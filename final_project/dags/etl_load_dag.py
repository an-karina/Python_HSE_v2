from datetime import datetime, timedelta
import os
import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import create_engine, text

DB_HOST = os.getenv("TARGET_DB_HOST", "postgres")
DB_PORT = os.getenv("TARGET_DB_PORT", "5432")
DB_NAME = os.getenv("TARGET_DB_NAME", "delivery")
DB_USER = os.getenv("TARGET_DB_USER", "delivery_user")
DB_PASS = os.getenv("TARGET_DB_PASSWORD", "delivery_pass")

DATA_DIR = "/opt/airflow/data"
CONN_STR = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_engine():
    return create_engine(CONN_STR)


def get_parquet_files():
    return sorted([
        os.path.join(DATA_DIR, f)
        for f in os.listdir(DATA_DIR)
        if f.endswith(".parquet")
    ])


def truncate_all_tables(**kwargs):
    """Очищаем все таблицы перед загрузкой"""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE delivery.order_drivers CASCADE"))
        conn.execute(text("TRUNCATE TABLE delivery.order_items CASCADE"))
        conn.execute(text("TRUNCATE TABLE delivery.orders CASCADE"))
        conn.execute(text("TRUNCATE TABLE delivery.items CASCADE"))
        conn.execute(text("TRUNCATE TABLE delivery.drivers CASCADE"))
        conn.execute(text("TRUNCATE TABLE delivery.stores CASCADE"))
        conn.execute(text("TRUNCATE TABLE delivery.users CASCADE"))
    print("Все таблицы очищены")


def load_dictionaries(**kwargs):
    """Загрузка справочников (users, stores, drivers, items) — по файлам."""
    files = get_parquet_files()
    if not files:
        raise FileNotFoundError(f"Нет parquet-файлов в {DATA_DIR}")

    users_set = {}
    stores_set = {}
    drivers_set = {}
    items_set = {}

    for i, fpath in enumerate(files):
        df = pd.read_parquet(fpath, columns=[
            "user_id", "user_phone", "store_id", "store_address",
            "driver_id", "driver_phone", "item_id", "item_title", "item_category"
        ])

        for _, row in df.drop_duplicates(subset=["user_id"]).iterrows():
            if row["user_id"] not in users_set:
                users_set[row["user_id"]] = row["user_phone"]

        for _, row in df.drop_duplicates(subset=["store_id"]).iterrows():
            if row["store_id"] not in stores_set:
                stores_set[row["store_id"]] = row["store_address"]

        for _, row in df.drop_duplicates(subset=["driver_id"]).iterrows():
            if row["driver_id"] not in drivers_set:
                drivers_set[row["driver_id"]] = row["driver_phone"]

        for _, row in df.drop_duplicates(subset=["item_id"]).iterrows():
            if row["item_id"] not in items_set:
                items_set[row["item_id"]] = (row["item_title"], row["item_category"])

        del df
        print(f"  Справочники: файл {i+1}/{len(files)}")

    engine = get_engine()

    users_df = pd.DataFrame([
        {"user_id": k, "phone": v} for k, v in users_set.items()
    ])
    users_df.to_sql("users", engine, schema="delivery", if_exists="append", index=False)
    print(f"Загружено {len(users_df)} пользователей")

    stores_df = pd.DataFrame([
        {"store_id": k, "store_address": v} for k, v in stores_set.items()
    ])
    stores_df.to_sql("stores", engine, schema="delivery", if_exists="append", index=False)
    print(f"Загружено {len(stores_df)} магазинов")

    drivers_df = pd.DataFrame([
        {"driver_id": k, "phone": v} for k, v in drivers_set.items()
    ])
    drivers_df.to_sql("drivers", engine, schema="delivery", if_exists="append", index=False)
    print(f"Загружено {len(drivers_df)} курьеров")

    items_df = pd.DataFrame([
        {"item_id": k, "title": v[0], "category": v[1]} for k, v in items_set.items()
    ])
    items_df.to_sql("items", engine, schema="delivery", if_exists="append", index=False)
    print(f"Загружено {len(items_df)} товаров")


def load_orders(**kwargs):
    """Загрузка таблицы заказов — по файлам."""
    files = get_parquet_files()
    engine = get_engine()

    order_cols = [
        "order_id", "user_id", "store_id", "address_text",
        "created_at", "paid_at", "delivery_started_at", "delivered_at",
        "canceled_at", "payment_type", "order_discount",
        "order_cancellation_reason", "delivery_cost"
    ]

    seen_orders = set()

    for i, fpath in enumerate(files):
        df = pd.read_parquet(fpath, columns=order_cols)

        # Берём строку с непустым delivered_at (финальный курьер)
        orders = df.sort_values("delivered_at", ascending=False, na_position="last")
        orders = orders.drop_duplicates(subset=["order_id"], keep="first")

        # Убираем уже загруженные order_id
        orders = orders[~orders["order_id"].isin(seen_orders)]
        seen_orders.update(orders["order_id"].tolist())

        if len(orders) == 0:
            del df, orders
            continue

        # Преобразуем NaT/NaN в None
        for col in ["paid_at", "delivery_started_at", "delivered_at", "canceled_at"]:
            orders[col] = orders[col].where(orders[col].notna(), None)
        orders["order_cancellation_reason"] = orders["order_cancellation_reason"].where(
            orders["order_cancellation_reason"].notna(), None
        )

        orders.to_sql("orders", engine, schema="delivery", if_exists="append",
                       index=False, method="multi", chunksize=5000)

        del df, orders
        print(f"  Заказы: файл {i+1}/{len(files)}, уникальных: {len(seen_orders)}")

    print(f"Загружено {len(seen_orders)} заказов")


def load_order_items(**kwargs):
    """Загрузка позиций заказов — по файлам."""
    files = get_parquet_files()
    engine = get_engine()

    seen_pairs = set()

    for i, fpath in enumerate(files):
        df = pd.read_parquet(fpath, columns=[
            "order_id", "item_id", "item_quantity", "item_price",
            "item_canceled_quantity", "item_replaced_id", "item_discount"
        ])
        oi = df.drop_duplicates(subset=["order_id", "item_id"])

        # Убираем уже загруженные пары
        oi["_key"] = oi["order_id"].astype(str) + "_" + oi["item_id"].astype(str)
        oi = oi[~oi["_key"].isin(seen_pairs)]
        seen_pairs.update(oi["_key"].tolist())
        oi = oi.drop(columns=["_key"])

        if len(oi) == 0:
            del df, oi
            continue


        oi["item_replaced_id"] = oi["item_replaced_id"].where(
            oi["item_replaced_id"].notna(), None
        )
        mask = oi["item_replaced_id"].notna()
        if mask.any():
            oi.loc[mask, "item_replaced_id"] = oi.loc[mask, "item_replaced_id"].astype(int)

        oi.to_sql("order_items", engine, schema="delivery", if_exists="append",
                   index=False, method="multi", chunksize=5000)

        del df, oi
        print(f"  Позиции: файл {i+1}/{len(files)}, уникальных: {len(seen_pairs)}")

    print(f"Загружено {len(seen_pairs)} позиций заказов")


def load_order_drivers(**kwargs):
    """Загрузка назначений курьеров — по файлам."""
    files = get_parquet_files()
    engine = get_engine()

    seen_pairs = set()

    for i, fpath in enumerate(files):
        df = pd.read_parquet(fpath, columns=["order_id", "driver_id", "delivered_at"])
        od = df.drop_duplicates(subset=["order_id", "driver_id"])

        od["_key"] = od["order_id"].astype(str) + "_" + od["driver_id"].astype(str)
        od = od[~od["_key"].isin(seen_pairs)]
        seen_pairs.update(od["_key"].tolist())
        od = od.drop(columns=["_key"])

        if len(od) == 0:
            del df, od
            continue

        od["delivered_at"] = od["delivered_at"].where(od["delivered_at"].notna(), None)

        od.to_sql("order_drivers", engine, schema="delivery", if_exists="append",
                   index=False, method="multi", chunksize=5000)

        del df, od
        print(f"  Курьеры: файл {i+1}/{len(files)}, уникальных: {len(seen_pairs)}")

    print(f"Загружено {len(seen_pairs)} назначений курьеров")


default_args = {
    "owner": "student",
    "retries": 2,
    "retry_delay": timedelta(seconds=30),
}

with DAG(
    dag_id="etl_load_normalized",
    default_args=default_args,
    description="Загрузка Parquet в нормализованные таблицы PostgreSQL",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["etl", "load"],
) as dag:

    truncate_task = PythonOperator(
        task_id="truncate_tables",
        python_callable=truncate_all_tables,
    )

    load_dicts_task = PythonOperator(
        task_id="load_dictionaries",
        python_callable=load_dictionaries,
    )

    load_orders_task = PythonOperator(
        task_id="load_orders",
        python_callable=load_orders,
    )

    load_order_items_task = PythonOperator(
        task_id="load_order_items",
        python_callable=load_order_items,
    )

    load_order_drivers_task = PythonOperator(
        task_id="load_order_drivers",
        python_callable=load_order_drivers,
    )

    truncate_task >> load_dicts_task >> load_orders_task
    load_orders_task >> [load_order_items_task, load_order_drivers_task]
