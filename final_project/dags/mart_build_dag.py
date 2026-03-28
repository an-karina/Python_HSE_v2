"""
DAG для построения витрин с использованием PySpark.
Витрина заказов и витрина товаров.
"""

from datetime import datetime
import os
from airflow import DAG
from airflow.operators.python import PythonOperator

DB_HOST = os.getenv("TARGET_DB_HOST", "postgres")
DB_PORT = os.getenv("TARGET_DB_PORT", "5432")
DB_NAME = os.getenv("TARGET_DB_NAME", "delivery")
DB_USER = os.getenv("TARGET_DB_USER", "delivery_user")
DB_PASS = os.getenv("TARGET_DB_PASSWORD", "delivery_pass")

JDBC_URL = f"jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"
JDBC_PROPS = {
    "user": DB_USER,
    "password": DB_PASS,
    "driver": "org.postgresql.Driver",
}
JDBC_JAR = "/opt/spark/jars/postgresql-42.7.1.jar"


def _get_spark(app_name):
    from pyspark.sql import SparkSession
    spark = (
        SparkSession.builder
        .appName(app_name)
        .master("local[*]")
        .config("spark.jars", JDBC_JAR)
        .config("spark.driver.memory", "2g")
        .config("spark.executor.memory", "2g")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )
    return spark


def _read_table(spark, table_name, partition_column=None, num_partitions=4):
    reader = spark.read
    if partition_column:
        return (
            reader.jdbc(
                JDBC_URL, f"delivery.{table_name}",
                column=partition_column,
                lowerBound=0, upperBound=10000000,
                numPartitions=num_partitions,
                properties=JDBC_PROPS
            )
        )
    return reader.jdbc(JDBC_URL, f"delivery.{table_name}", properties=JDBC_PROPS)


def _write_table(df, table_name):
    (
        df.write
        .mode("overwrite")
        .jdbc(JDBC_URL, f"delivery.{table_name}", properties=JDBC_PROPS)
    )


def build_orders_mart(**kwargs):
    """Построение витрины заказов с помощью PySpark."""
    from pyspark.sql import functions as F

    spark = _get_spark("orders_mart")

    try:
        orders = _read_table(spark, "orders", "order_id", 8)
        order_items = _read_table(spark, "order_items", "order_id", 8)
        order_drivers = _read_table(spark, "order_drivers", "order_id", 8)
        stores = _read_table(spark, "stores")

        # Извлекаем город из address_text (первое слово до запятой)
        orders = orders.withColumn(
            "city",
            F.trim(F.split(F.col("address_text"), ",")[0])
        )

        # Добавляем временные разрезы
        orders = (
            orders
            .withColumn("year", F.year("created_at"))
            .withColumn("month", F.month("created_at"))
            .withColumn("day", F.dayofmonth("created_at"))
        )

        # Рассчитываем суммы по позициям заказа
        items_agg = (
            order_items
            .withColumn(
                "item_total",
                F.col("item_quantity") * F.col("item_price")
                * (1 - F.col("item_discount") / 100)
            )
            # Выручка = (кол-во - отмененное кол-во) * цена * (1 - item_discount/100)
            # Учитываем только неотмененные единицы
            .withColumn(
                "item_revenue",
                (F.col("item_quantity") - F.col("item_canceled_quantity"))
                * F.col("item_price")
                * (1 - F.col("item_discount") / 100)
            )
            .groupBy("order_id")
            .agg(
                F.sum("item_total").alias("order_turnover_raw"),
                F.sum("item_revenue").alias("order_revenue_raw"),
            )
        )

        # Джойним суммы к заказам и применяем скидку заказа
        orders_with_items = orders.join(items_agg, "order_id", "left")
        orders_with_items = (
            orders_with_items
            .withColumn(
                "turnover",
                F.col("order_turnover_raw") * (1 - F.col("order_discount") / 100)
            )
            .withColumn(
                "revenue",
                F.col("order_revenue_raw") * (1 - F.col("order_discount") / 100)
            )
            .withColumn(
                "profit",
                F.col("revenue") - F.col("delivery_cost")
            )
            # Флаги статусов
            .withColumn("is_delivered", F.when(F.col("delivered_at").isNotNull(), 1).otherwise(0))
            .withColumn("is_canceled", F.when(F.col("canceled_at").isNotNull(), 1).otherwise(0))
            .withColumn(
                "is_canceled_after_delivery",
                F.when(
                    (F.col("canceled_at").isNotNull()) & (F.col("delivered_at").isNotNull()),
                    1
                ).otherwise(0)
            )
            .withColumn(
                "is_service_error",
                F.when(
                    F.col("order_cancellation_reason").isin(
                        "Ошибка приложения", "Проблемы с оплатой"
                    ),
                    1
                ).otherwise(0)
            )
        )

        # Считаем смены курьеров: заказы, у которых > 1 курьера
        driver_counts = (
            order_drivers
            .groupBy("order_id")
            .agg(F.countDistinct("driver_id").alias("num_drivers"))
        )
        driver_changes = (
            driver_counts
            .withColumn(
                "has_driver_change",
                F.when(F.col("num_drivers") > 1, 1).otherwise(0)
            )
        )

        orders_full = orders_with_items.join(driver_changes, "order_id", "left")
        orders_full = orders_full.fillna({"has_driver_change": 0, "num_drivers": 0})

        # Активные курьеры — присоединяем driver_id
        orders_drivers = orders.select("order_id", "year", "month", "day", "city", "store_id") \
            .join(order_drivers.select("order_id", "driver_id"), "order_id", "inner")

        active_drivers = (
            orders_drivers
            .groupBy("year", "month", "day", "city", "store_id")
            .agg(F.countDistinct("driver_id").alias("active_drivers"))
        )

        # Добавляем store_address
        orders_full = orders_full.join(
            stores.select("store_id", "store_address"), "store_id", "left"
        )

        # Основная агрегация витрины
        mart = (
            orders_full
            .groupBy("year", "month", "day", "city", "store_id", "store_address")
            .agg(
                F.round(F.sum("turnover"), 2).alias("turnover"),
                F.round(F.sum("revenue"), 2).alias("revenue"),
                F.round(F.sum("profit"), 2).alias("profit"),
                F.countDistinct("order_id").alias("total_orders"),
                F.sum("is_delivered").alias("delivered_orders"),
                F.sum("is_canceled").alias("canceled_orders"),
                F.sum("is_canceled_after_delivery").alias("canceled_after_delivery"),
                F.sum("is_service_error").alias("canceled_service_errors"),
                F.countDistinct("user_id").alias("unique_buyers"),
                F.sum("has_driver_change").alias("driver_changes"),
            )
        )

        # Средний чек, заказов/покупателя, выручка/покупателя
        mart = (
            mart
            .withColumn(
                "avg_check",
                F.round(F.col("revenue") / F.col("total_orders"), 2)
            )
            .withColumn(
                "orders_per_buyer",
                F.round(F.col("total_orders").cast("double") / F.col("unique_buyers"), 4)
            )
            .withColumn(
                "revenue_per_buyer",
                F.round(F.col("revenue") / F.col("unique_buyers"), 2)
            )
        )

        # Присоединяем активных курьеров
        mart = mart.join(
            active_drivers,
            on=["year", "month", "day", "city", "store_id"],
            how="left"
        ).fillna({"active_drivers": 0})

        # Приводим типы
        mart = (
            mart
            .withColumn("total_orders", F.col("total_orders").cast("long"))
            .withColumn("delivered_orders", F.col("delivered_orders").cast("long"))
            .withColumn("canceled_orders", F.col("canceled_orders").cast("long"))
            .withColumn("canceled_after_delivery", F.col("canceled_after_delivery").cast("long"))
            .withColumn("canceled_service_errors", F.col("canceled_service_errors").cast("long"))
            .withColumn("unique_buyers", F.col("unique_buyers").cast("long"))
            .withColumn("driver_changes", F.col("driver_changes").cast("long"))
            .withColumn("active_drivers", F.col("active_drivers").cast("long"))
        )

        _write_table(mart, "mart_orders")
        print(f"Витрина заказов: {mart.count()} строк")

    finally:
        spark.stop()


def build_items_mart(**kwargs):
    """Построение витрины товаров с помощью PySpark."""
    from pyspark.sql import functions as F
    from pyspark.sql.window import Window

    spark = _get_spark("items_mart")

    try:
        orders = _read_table(spark, "orders", "order_id", 8)
        order_items = _read_table(spark, "order_items", "order_id", 8)
        items = _read_table(spark, "items")
        stores = _read_table(spark, "stores")

        # Город из адреса
        orders = orders.withColumn(
            "city", F.trim(F.split(F.col("address_text"), ",")[0])
        )
        orders = (
            orders
            .withColumn("year", F.year("created_at"))
            .withColumn("month", F.month("created_at"))
            .withColumn("day", F.dayofmonth("created_at"))
            .withColumn("week", F.weekofyear("created_at"))
        )

        # Соединяем заказы с позициями и товарами
        base = (
            order_items
            .join(orders.select(
                "order_id", "year", "month", "day", "week",
                "city", "store_id", "order_discount"
            ), "order_id", "inner")
            .join(items, "item_id", "inner")
            .join(stores.select("store_id", "store_address"), "store_id", "left")
        )

        # Оборот товара = кол-во * цена * (1 - item_discount/100) * (1 - order_discount/100)
        base = base.withColumn(
            "item_turnover",
            F.col("item_quantity") * F.col("item_price")
            * (1 - F.col("item_discount") / 100)
            * (1 - F.col("order_discount") / 100)
        )

        base = base.withColumn(
            "has_cancel",
            F.when(F.col("item_canceled_quantity") > 0, 1).otherwise(0)
        )

        # Агрегация по разрезам
        mart = (
            base
            .groupBy("year", "month", "day", "city", "store_id", "store_address",
                      "category", "item_id", "title")
            .agg(
                F.round(F.sum("item_turnover"), 2).alias("item_turnover"),
                F.sum("item_quantity").alias("ordered_quantity"),
                F.sum("item_canceled_quantity").alias("canceled_quantity"),
                F.countDistinct("order_id").alias("orders_with_item"),
                F.sum("has_cancel").alias("orders_with_item_cancel"),
            )
        )

        mart = mart.withColumnRenamed("title", "item_title")

        # Популярность: по дню
        day_window = Window.partitionBy("year", "month", "day", "city", "store_id")
        mart = (
            mart
            .withColumn("day_rank_asc",
                         F.rank().over(day_window.orderBy(F.col("ordered_quantity").asc())))
            .withColumn("day_rank_desc",
                         F.rank().over(day_window.orderBy(F.col("ordered_quantity").desc())))
            .withColumn("is_most_popular_day", F.col("day_rank_desc") == 1)
            .withColumn("is_least_popular_day", F.col("day_rank_asc") == 1)
        )

        # Популярность: по неделе
        # Агрегируем по неделе для определения ранга, затем джойним обратно
        week_base = (
            base
            .groupBy("year", "week", "city", "store_id", "item_id")
            .agg(F.sum("item_quantity").alias("week_qty"))
        )
        week_window = Window.partitionBy("year", "week", "city", "store_id")
        week_ranks = (
            week_base
            .withColumn("week_rank_desc",
                         F.rank().over(week_window.orderBy(F.col("week_qty").desc())))
            .withColumn("week_rank_asc",
                         F.rank().over(week_window.orderBy(F.col("week_qty").asc())))
            .withColumn("is_most_popular_week", F.col("week_rank_desc") == 1)
            .withColumn("is_least_popular_week", F.col("week_rank_asc") == 1)
            .select("year", "week", "city", "store_id", "item_id",
                    "is_most_popular_week", "is_least_popular_week")
        )

        # Нужно добавить week в mart для джойна
        mart = mart.join(
            base.select("order_id", "item_id", "year", "month", "day", "city", "store_id")
                .withColumn("week", F.weekofyear(
                    F.to_date(F.concat_ws("-",
                        F.col("year"), F.lpad(F.col("month"), 2, "0"),
                        F.lpad(F.col("day"), 2, "0")
                    ))
                ))
                .select("year", "month", "day", "city", "store_id", "item_id", "week")
                .dropDuplicates(["year", "month", "day", "city", "store_id", "item_id"]),
            on=["year", "month", "day", "city", "store_id", "item_id"],
            how="left"
        )

        mart = mart.join(
            week_ranks,
            on=["year", "week", "city", "store_id", "item_id"],
            how="left"
        ).fillna({"is_most_popular_week": False, "is_least_popular_week": False})

        # Популярность: по месяцу
        month_base = (
            base
            .groupBy("year", "month", "city", "store_id", "item_id")
            .agg(F.sum("item_quantity").alias("month_qty"))
        )
        month_window = Window.partitionBy("year", "month", "city", "store_id")
        month_ranks = (
            month_base
            .withColumn("month_rank_desc",
                         F.rank().over(month_window.orderBy(F.col("month_qty").desc())))
            .withColumn("month_rank_asc",
                         F.rank().over(month_window.orderBy(F.col("month_qty").asc())))
            .withColumn("is_most_popular_month", F.col("month_rank_desc") == 1)
            .withColumn("is_least_popular_month", F.col("month_rank_asc") == 1)
            .select("year", "month", "city", "store_id", "item_id",
                    "is_most_popular_month", "is_least_popular_month")
        )

        mart = mart.join(
            month_ranks,
            on=["year", "month", "city", "store_id", "item_id"],
            how="left"
        ).fillna({"is_most_popular_month": False, "is_least_popular_month": False})

        # Финальный select (убираем служебные колонки)
        mart_final = mart.select(
            "year", "month", "day", "city", "store_id", "store_address",
            "category", "item_id", "item_title",
            "item_turnover", "ordered_quantity", "canceled_quantity",
            "orders_with_item", "orders_with_item_cancel",
            "is_most_popular_day", "is_least_popular_day",
            "is_most_popular_week", "is_least_popular_week",
            "is_most_popular_month", "is_least_popular_month",
        )

        # Приводим типы
        mart_final = (
            mart_final
            .withColumn("ordered_quantity", F.col("ordered_quantity").cast("long"))
            .withColumn("canceled_quantity", F.col("canceled_quantity").cast("long"))
            .withColumn("orders_with_item", F.col("orders_with_item").cast("long"))
            .withColumn("orders_with_item_cancel", F.col("orders_with_item_cancel").cast("long"))
        )

        _write_table(mart_final, "mart_items")
        print(f"Витрина товаров: {mart_final.count()} строк")

    finally:
        spark.stop()



# Определение DAG
default_args = {
    "owner": "student",
    "retries": 1,
}

with DAG(
    dag_id="build_data_marts",
    default_args=default_args,
    description="Построение витрин заказов и товаров с PySpark",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["mart", "pyspark"],
) as dag:

    build_orders = PythonOperator(
        task_id="build_orders_mart",
        python_callable=build_orders_mart,
    )

    build_items = PythonOperator(
        task_id="build_items_mart",
        python_callable=build_items_mart,
    )

    # Витрины можно строить параллельно
    [build_orders, build_items]
