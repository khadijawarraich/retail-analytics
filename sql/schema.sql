-- schema.sql
CREATE TABLE stores (
    store_id      INTEGER PRIMARY KEY,
    store_name    TEXT    NOT NULL,
    city          TEXT    NOT NULL,
    opened_year   INTEGER,
    sq_ft         INTEGER
);

CREATE TABLE products (
    product_id    INTEGER PRIMARY KEY,
    sku           TEXT    NOT NULL UNIQUE,
    category      TEXT    NOT NULL,
    list_price    REAL    NOT NULL CHECK (list_price > 0),
    unit_cost     REAL    NOT NULL CHECK (unit_cost > 0)
);

CREATE TABLE customers (
    customer_id     INTEGER PRIMARY KEY,
    home_store_id   INTEGER REFERENCES stores(store_id),
    loyalty_member  INTEGER NOT NULL CHECK (loyalty_member IN (0, 1)),
    age_group       TEXT,
    signup_date     TEXT
);

CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
    store_id      INTEGER NOT NULL REFERENCES stores(store_id),
    order_date    TEXT    NOT NULL,
    payment_type  TEXT,
    promo_flag    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE order_items (
    item_id       INTEGER PRIMARY KEY,
    order_id      INTEGER NOT NULL REFERENCES orders(order_id),
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    REAL    NOT NULL,
    discount_pct  REAL    NOT NULL DEFAULT 0
);

CREATE TABLE returns (
    return_id     INTEGER PRIMARY KEY,
    item_id       INTEGER NOT NULL REFERENCES order_items(item_id),
    return_date   TEXT    NOT NULL,
    reason        TEXT
);

CREATE INDEX idx_orders_date     ON orders(order_date);
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_items_order     ON order_items(order_id);
CREATE INDEX idx_items_product   ON order_items(product_id);


CREATE VIEW v_sales AS
SELECT
    oi.item_id,
    o.order_id,
    o.order_date,
    strftime('%Y', o.order_date)          AS yr,
    strftime('%Y-%m', o.order_date)       AS yr_month,
    o.customer_id,
    o.store_id,
    o.promo_flag,
    p.category,
    oi.quantity,
    oi.discount_pct,
    ROUND(oi.quantity * oi.unit_price * (1 - oi.discount_pct), 2) AS revenue,
    ROUND(oi.quantity * p.unit_cost, 2)                            AS cost,
    CASE WHEN r.return_id IS NULL THEN 0 ELSE 1 END                AS is_returned
FROM order_items oi
JOIN orders   o ON o.order_id   = oi.order_id
JOIN products p ON p.product_id = oi.product_id
LEFT JOIN returns r ON r.item_id = oi.item_id;
