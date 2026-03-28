-- DDL-скрипты для нормализованной схемы данных по доставкам
-- Нормальная форма: 3НФ (третья нормальная форма)

CREATE SCHEMA IF NOT EXISTS delivery;

-- Справочник пользователей
CREATE TABLE IF NOT EXISTS delivery.users (
    user_id     BIGINT PRIMARY KEY,
    phone       VARCHAR(50) NOT NULL
);

-- Справочник магазинов
CREATE TABLE IF NOT EXISTS delivery.stores (
    store_id      BIGINT PRIMARY KEY,
    store_address VARCHAR(500) NOT NULL
);

-- Справочник курьеров
CREATE TABLE IF NOT EXISTS delivery.drivers (
    driver_id   BIGINT PRIMARY KEY,
    phone       VARCHAR(50) NOT NULL
);

-- Справочник товаров
CREATE TABLE IF NOT EXISTS delivery.items (
    item_id     BIGINT PRIMARY KEY,
    title       VARCHAR(500) NOT NULL,
    category    VARCHAR(200) NOT NULL
);

-- Заказы
CREATE TABLE IF NOT EXISTS delivery.orders (
    order_id                BIGINT PRIMARY KEY,
    user_id                 BIGINT NOT NULL REFERENCES delivery.users(user_id),
    store_id                BIGINT NOT NULL REFERENCES delivery.stores(store_id),
    address_text            VARCHAR(500) NOT NULL,
    created_at              TIMESTAMP NOT NULL,
    paid_at                 TIMESTAMP,
    delivery_started_at     TIMESTAMP,
    delivered_at            TIMESTAMP,
    canceled_at             TIMESTAMP,
    payment_type            VARCHAR(50) NOT NULL,
    order_discount          INTEGER NOT NULL DEFAULT 0,
    order_cancellation_reason VARCHAR(200),
    delivery_cost           INTEGER NOT NULL DEFAULT 0
);

-- Позиции заказа (товары в заказе)
CREATE TABLE IF NOT EXISTS delivery.order_items (
    order_id              BIGINT NOT NULL REFERENCES delivery.orders(order_id),
    item_id               BIGINT NOT NULL REFERENCES delivery.items(item_id),
    item_quantity          INTEGER NOT NULL,
    item_price             INTEGER NOT NULL,
    item_canceled_quantity INTEGER NOT NULL DEFAULT 0,
    item_replaced_id       BIGINT REFERENCES delivery.items(item_id),
    item_discount          INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (order_id, item_id)
);

-- Назначения курьеров на заказы (для отслеживания смен курьеров)
CREATE TABLE IF NOT EXISTS delivery.order_drivers (
    id          SERIAL PRIMARY KEY,
    order_id    BIGINT NOT NULL REFERENCES delivery.orders(order_id),
    driver_id   BIGINT NOT NULL REFERENCES delivery.drivers(driver_id),
    delivered_at TIMESTAMP,
    UNIQUE (order_id, driver_id)
);


-- Витрина заказов
CREATE TABLE IF NOT EXISTS delivery.mart_orders (
    year                        INTEGER NOT NULL,
    month                       INTEGER NOT NULL,
    day                         INTEGER NOT NULL,
    city                        VARCHAR(200) NOT NULL,
    store_id                    BIGINT NOT NULL,
    store_address               VARCHAR(500) NOT NULL,
    turnover                    NUMERIC(18,2),
    revenue                     NUMERIC(18,2),
    profit                      NUMERIC(18,2),
    total_orders                BIGINT,
    delivered_orders            BIGINT,
    canceled_orders             BIGINT,
    canceled_after_delivery     BIGINT,
    canceled_service_errors     BIGINT,
    unique_buyers               BIGINT,
    avg_check                   NUMERIC(18,2),
    orders_per_buyer            NUMERIC(18,4),
    revenue_per_buyer           NUMERIC(18,2),
    driver_changes              BIGINT,
    active_drivers              BIGINT,
    PRIMARY KEY (year, month, day, city, store_id)
);

-- Витрина товаров
CREATE TABLE IF NOT EXISTS delivery.mart_items (
    year                        INTEGER NOT NULL,
    month                       INTEGER NOT NULL,
    day                         INTEGER NOT NULL,
    city                        VARCHAR(200) NOT NULL,
    store_id                    BIGINT NOT NULL,
    store_address               VARCHAR(500) NOT NULL,
    category                    VARCHAR(200) NOT NULL,
    item_id                     BIGINT NOT NULL,
    item_title                  VARCHAR(500) NOT NULL,
    item_turnover               NUMERIC(18,2),
    ordered_quantity            BIGINT,
    canceled_quantity           BIGINT,
    orders_with_item            BIGINT,
    orders_with_item_cancel     BIGINT,
    is_most_popular_day         BOOLEAN DEFAULT FALSE,
    is_least_popular_day        BOOLEAN DEFAULT FALSE,
    is_most_popular_week        BOOLEAN DEFAULT FALSE,
    is_least_popular_week       BOOLEAN DEFAULT FALSE,
    is_most_popular_month       BOOLEAN DEFAULT FALSE,
    is_least_popular_month      BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (year, month, day, city, store_id, item_id)
);
