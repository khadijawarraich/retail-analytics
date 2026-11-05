import os
import re
import sqlite3
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

os.makedirs("outputs", exist_ok=True)
os.makedirs("charts", exist_ok=True)

BLUE, ORANGE, GRAY, TEAL = "#2F6BB3", "#E07B39", "#9AA0A6", "#2A9D8F"
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25, "font.size": 10})

#run the SQL
con = sqlite3.connect("data/retail.db")
sql_text = open("sql/analysis.sql").read()
results = {}
for name, query in re.findall(r"-- name: (\w+)\n(.*?)(?=-- name:|\Z)", sql_text, re.S):
    results[name] = pd.read_sql(query, con)
    results[name].to_csv(f"outputs/{name}.csv", index=False)
    print(f"ran {name:28s} -> {len(results[name]):>5} rows")

#charts
# monthly revenue, 2024 vs 2025
m = results["q1_monthly_revenue"].copy()
m["year"] = m.yr_month.str[:4]
m["month"] = m.yr_month.str[5:].astype(int)
fig, ax = plt.subplots(figsize=(8, 4))
for yr, color in [("2024", GRAY), ("2025", BLUE)]:
    d = m[m.year == yr]
    ax.plot(d.month, d.revenue / 1000, marker="o", color=color, label=yr, linewidth=2)
ax.set_xticks(range(1, 13), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
ax.set_ylabel("Net revenue ($K)")
ax.set_title("Monthly net revenue: holiday season drives the year")
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig("charts/monthly_revenue.png"); plt.close(fig)

# category revenue vs return rate
c = results["q2_category_performance"]
fig, ax1 = plt.subplots(figsize=(8, 4))
ax1.bar(c.category, c.gross_revenue / 1000, color=BLUE)
ax1.set_ylabel("Gross revenue ($K)")
ax2 = ax1.twinx()
ax2.plot(c.category, c.return_rate_pct, color=ORANGE, marker="o", linewidth=2)
ax2.set_ylabel("Return rate (%)", color=ORANGE)
ax2.grid(False)
ax1.set_title("Revenue (bars) vs return rate (line) by category")
plt.setp(ax1.get_xticklabels(), rotation=20, ha="right")
fig.tight_layout(); fig.savefig("charts/category_returns.png"); plt.close(fig)

# discount depth vs margin and returns
dsc = results["q5_discount_impact"]
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(dsc.discount, dsc.margin_pct, color=TEAL)
for i, (mg, rr) in enumerate(zip(dsc.margin_pct, dsc.return_rate_pct)):
    ax.text(i, mg + 1, f"{mg:.0f}% margin\n{rr:.1f}% returned", ha="center", fontsize=8)
ax.set_ylabel("Margin (%)")
ax.set_ylim(0, 58)
ax.set_title("Deeper discounts cut margin sharply and raise returns")
fig.tight_layout(); fig.savefig("charts/discount_margin.png"); plt.close(fig)

# revenue concentration
dec = results["q8_customer_value_tiers"]
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot([0] + list(dec.decile * 10), [0] + list(dec.cumulative_revenue_pct), marker="o", color=BLUE, linewidth=2)
ax.plot([0, 100], [0, 100], linestyle="--", color=GRAY, label="If every customer spent equally")
ax.set_xlabel("Top X% of customers by spend")
ax.set_ylabel("Share of total revenue (%)")
ax.set_title("Revenue concentration across customers")
ax.legend(frameon=False)
fig.tight_layout(); fig.savefig("charts/revenue_concentration.png"); plt.close(fig)

#customer segmentation (RFM + K-Means)
rfm = results["q9_rfm_base"].copy()
X = np.column_stack([np.log1p(rfm.recency_days), np.log1p(rfm.frequency), np.log1p(rfm.monetary)])
X = StandardScaler().fit_transform(X)

print("\nChoosing number of clusters (silhouette score, higher is better):")
scores = {}
for k in range(3, 7):
    labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)
    scores[k] = silhouette_score(X, labels, sample_size=3000, random_state=42)
    print(f"  k={k}: {scores[k]:.3f}")
# 4 clusters map to segments the business can act on
best_k = max(scores, key=scores.get)
k = 4 if scores[4] >= scores[best_k] - 0.03 else best_k
rfm["cluster"] = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)

profile = rfm.groupby("cluster").agg(customers=("customer_id", "count"),
                                     avg_recency_days=("recency_days", "mean"),
                                     avg_orders=("frequency", "mean"),
                                     avg_spend=("monetary", "mean"),
                                     total_spend=("monetary", "sum")).round(1)
# name clusters by spend and recency, highest-value first
profile = profile.sort_values("avg_spend", ascending=False)
names = ["Champions", "Loyal regulars", "Occasional shoppers", "At risk / lapsed", "Low engagement", "One-timers"]
order = list(profile.index)
# the least-recent cluster gets the "at risk" label regardless of spend rank
lapsed = profile.avg_recency_days.idxmax()
labels_map, pool = {}, [n for n in names if n != "At risk / lapsed"]
for cl in order:
    labels_map[cl] = "At risk / lapsed" if cl == lapsed else pool.pop(0)
profile.insert(0, "segment", profile.index.map(labels_map))
profile["share_of_revenue_pct"] = (100 * profile.total_spend / profile.total_spend.sum()).round(1)
profile = profile.drop(columns="total_spend")
rfm["segment"] = rfm.cluster.map(labels_map)
profile.to_csv("outputs/customer_segments.csv", index=False)
rfm.to_csv("outputs/customer_rfm_labeled.csv", index=False)
print("\nCustomer segments:")
print(profile.to_string(index=False))

fig, ax = plt.subplots(figsize=(7, 4.5))
palette = [BLUE, TEAL, ORANGE, "#B5179E", GRAY, "#6A994E"]
for i, seg in enumerate(profile.segment):
    d = rfm[rfm.segment == seg]
    ax.scatter(d.frequency, d.monetary, s=8, alpha=0.5, color=palette[i], label=seg)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("Orders (2 years, log scale)")
ax.set_ylabel("Net spend $ (log scale)")
ax.set_title("Customer segments from RFM + K-Means")
ax.legend(frameon=False, markerscale=2)
fig.tight_layout(); fig.savefig("charts/customer_segments.png"); plt.close(fig)

con.close()
print("\nSaved CSVs to outputs/ and charts to charts/")
