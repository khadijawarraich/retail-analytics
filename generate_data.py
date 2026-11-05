

import os
import sqlite3
import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)
os.makedirs("data", exist_ok=True)
DB_PATH = "data/retail.db"

# stores 
stores = pd.DataFrame({
    "store_id": range(1, 7),
    "store_name": ["Aurora - Havana St", "Denver - Colfax", "Lakewood - Belmar",
                   "Thornton - Grant St", "Littleton - Southwest Plaza", "Englewood - River Point"],
    "city": ["Aurora", "Denver", "Lakewood", "Thornton", "Littleton", "Englewood"],
    "opened_year": [2012, 2009, 2015, 2018, 2011, 2020],
    "sq_ft": [28000, 24000, 30000, 26000, 32000, 22000],
})
store_weight = np.array([1.15, 1.25, 1.0, 0.85, 1.05, 0.7])
store_weight = store_weight / store_weight.sum()

# products 
categories = {
    #  category: (n_products, price_low, price_high, return_rate)
    "Women's Apparel": (60, 8, 45, 0.11),
    "Men's Apparel":   (40, 8, 40, 0.08),
    "Kids":            (35, 5, 25, 0.06),
    "Shoes":           (30, 15, 60, 0.14),
    "Home":            (45, 6, 80, 0.05),
    "Accessories":     (25, 4, 30, 0.04),
    "Beauty":          (20, 3, 20, 0.02),
}
rows, pid = [], 1
for cat, (n, lo, hi, _) in categories.items():
    for i in range(n):
        price = float(np.floor(rng.uniform(lo, hi))) + 0.99  # retail-style .99 pricing
        cost = round(price * rng.uniform(0.45, 0.65), 2)
        rows.append((pid, f"{cat.split()[0].replace(chr(39) + 's', '')}-{i + 1:03d}", cat, round(price, 2), cost))
        pid += 1
products = pd.DataFrame(rows, columns=["product_id", "sku", "category", "list_price", "unit_cost"])

# customers
N_CUST = 6000
signup = pd.to_datetime("2022-01-01") + pd.to_timedelta(rng.integers(0, 365 * 4, N_CUST), unit="D")
customers = pd.DataFrame({
    "customer_id": range(1, N_CUST + 1),
    "home_store_id": rng.choice(stores.store_id, N_CUST, p=store_weight),
    "loyalty_member": (rng.random(N_CUST) < 0.38).astype(int),
    "age_group": rng.choice(["18-24", "25-34", "35-44", "45-54", "55+"], N_CUST, p=[0.16, 0.27, 0.24, 0.18, 0.15]),
    "signup_date": signup.date,
})
# shopping propensity: loyalty members shop 2x as often, long tail of heavy shoppers
propensity = rng.gamma(1.2, 1.0, N_CUST) * np.where(customers.loyalty_member == 1, 2.0, 1.0)
propensity = propensity / propensity.sum()

# orders
dates = pd.date_range("2024-01-01", "2025-12-31", freq="D")
month_factor = {1: 0.75, 2: 0.7, 3: 0.85, 4: 0.9, 5: 0.95, 6: 0.9, 7: 0.95,
                8: 1.15, 9: 0.9, 10: 1.0, 11: 1.35, 12: 1.7}
dow_factor = {0: 0.85, 1: 0.8, 2: 0.85, 3: 0.9, 4: 1.1, 5: 1.4, 6: 1.25}
daily = np.array([month_factor[d.month] * dow_factor[d.dayofweek] * (1.06 if d.year == 2025 else 1.0)
                  for d in dates])
orders_per_day = rng.poisson(daily / daily.mean() * 85)

order_dates = np.repeat(dates.values, orders_per_day)
N_ORD = len(order_dates)
cust_ids = rng.choice(customers.customer_id, N_ORD, p=propensity)
home = customers.set_index("customer_id").home_store_id
# 80% of the time a customer shops at their home store
store_ids = np.where(rng.random(N_ORD) < 0.8, home.loc[cust_ids].values,
                     rng.choice(stores.store_id, N_ORD, p=store_weight))
# promo days: black friday week, back-to-school, random weekend sales
od = pd.to_datetime(order_dates)
promo = (((od.month == 11) & (od.day >= 22)) | ((od.month == 8) & (od.day <= 15)) |
         ((od.dayofweek >= 5) & (rng.random(N_ORD) < 0.15)))
pay = rng.choice(["Card", "Cash", "Mobile"], N_ORD, p=[0.68, 0.14, 0.18])

orders = pd.DataFrame({
    "order_id": range(1, N_ORD + 1),
    "customer_id": cust_ids,
    "store_id": store_ids,
    "order_date": od.strftime("%Y-%m-%d"),
    "payment_type": pay,
    "promo_flag": promo.astype(int),
})

#  order items 
cat_names = list(categories.keys())
cat_p = np.array([0.27, 0.15, 0.13, 0.10, 0.17, 0.10, 0.08])
# holiday shifts mix toward home and accessories, back-to-school toward kids
n_items = rng.poisson(np.where(promo, 3.2, 2.3)) + 1
item_order = np.repeat(orders.order_id.values, n_items)
item_month = np.repeat(od.month.values, n_items)
item_promo = np.repeat(promo, n_items)

cat_choice = np.empty(len(item_order), dtype=object)
for m in range(1, 13):
    mask = item_month == m
    p = cat_p.copy()
    if m in (11, 12):
        p[4] *= 1.5; p[5] *= 1.4
    if m == 8:
        p[2] *= 1.8
    p /= p.sum()
    cat_choice[mask] = rng.choice(cat_names, mask.sum(), p=p)

prod_by_cat = {c: products[products.category == c].product_id.values for c in cat_names}
prod_ids = np.empty(len(item_order), dtype=int)
for c in cat_names:
    mask = cat_choice == c
    prod_ids[mask] = rng.choice(prod_by_cat[c], mask.sum())

price = products.set_index("product_id").list_price.loc[prod_ids].values
discount = np.where(item_promo, rng.choice([0.2, 0.3, 0.4], len(prod_ids), p=[0.5, 0.35, 0.15]),
                    np.where(rng.random(len(prod_ids)) < 0.08, 0.1, 0.0))
qty = np.where(rng.random(len(prod_ids)) < 0.88, 1, rng.integers(2, 4, len(prod_ids)))

items = pd.DataFrame({
    "item_id": range(1, len(item_order) + 1),
    "order_id": item_order,
    "product_id": prod_ids,
    "quantity": qty,
    "unit_price": price,
    "discount_pct": discount,
})

# returns 
ret_rate = np.array([categories[c][3] for c in cat_choice])
ret_rate = ret_rate * np.where(discount >= 0.3, 1.3, 1.0)  # deep-discount buys get returned more
returned = rng.random(len(items)) < ret_rate
order_date_lookup = orders.set_index("order_id").order_date
ret_items = items[returned]
ret_dates = pd.to_datetime(order_date_lookup.loc[ret_items.order_id].values) + \
    pd.to_timedelta(rng.integers(1, 30, len(ret_items)), unit="D")
reasons = ["Wrong size", "Changed mind", "Defective", "Not as pictured", "Gift return"]
reason_p = {  # sizing drives apparel/shoe returns, quality and looks drive home returns
    "Women's Apparel": [0.48, 0.22, 0.07, 0.13, 0.10],
    "Men's Apparel":   [0.45, 0.24, 0.08, 0.11, 0.12],
    "Kids":            [0.50, 0.18, 0.08, 0.08, 0.16],
    "Shoes":           [0.58, 0.15, 0.12, 0.07, 0.08],
    "Home":            [0.00, 0.28, 0.32, 0.28, 0.12],
    "Accessories":     [0.00, 0.40, 0.20, 0.20, 0.20],
    "Beauty":          [0.00, 0.35, 0.30, 0.15, 0.20],
}
ret_cats = cat_choice[returned]
ret_reason = np.empty(len(ret_items), dtype=object)
for c, p in reason_p.items():
    mask = ret_cats == c
    ret_reason[mask] = rng.choice(reasons, mask.sum(), p=p)
returns = pd.DataFrame({
    "return_id": range(1, len(ret_items) + 1),
    "item_id": ret_items.item_id.values,
    "return_date": ret_dates.strftime("%Y-%m-%d"),
    "reason": ret_reason,
})

# load into SQLite 
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
con = sqlite3.connect(DB_PATH)
with open("sql/schema.sql") as f:
    con.executescript(f.read())
for name, df in [("stores", stores), ("products", products), ("customers", customers),
                 ("orders", orders), ("order_items", items), ("returns", returns)]:
    df.to_sql(name, con, if_exists="append", index=False)
con.commit()

# also export the tables as CSVs
os.makedirs("data/csv", exist_ok=True)
for name, df in [("stores", stores), ("products", products), ("customers", customers),
                 ("orders", orders), ("order_items", items), ("returns", returns)]:
    df.to_csv(f"data/csv/{name}.csv", index=False)

for t in ["stores", "products", "customers", "orders", "order_items", "returns"]:
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"{t:12s} {n:>8,} rows")
con.close()
print(f"Saved {DB_PATH}")
