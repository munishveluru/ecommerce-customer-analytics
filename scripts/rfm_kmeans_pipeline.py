import os
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# 1. Load data
transactions_file = os.path.join("data", "raw_transactions.csv")
customers_file = os.path.join("data", "dim_customers.csv")

if not os.path.exists(transactions_file) or not os.path.exists(customers_file):
    print("Error: Raw data files not found. Please run scripts/data_generator.py first.")
    exit(1)

df_tx = pd.read_csv(transactions_file)
df_cust = pd.read_csv(customers_file)

# Parse dates
df_tx["TransactionDate"] = pd.to_datetime(df_tx["TransactionDate"])
df_cust["SignupDate"] = pd.to_datetime(df_cust["SignupDate"])

# Set reference date (one day after the latest transaction)
ref_date = df_tx["TransactionDate"].max() + pd.Timedelta(days=1)
print(f"Reference Date for Recency calculation: {ref_date.strftime('%Y-%m-%d')}")

# 2. Calculate RFM Metrics
print("Calculating Recency, Frequency, and Monetary metrics...")
rfm = df_tx.groupby("CustomerID").agg({
    "TransactionDate": lambda x: (ref_date - x.max()).days, # Recency
    "TransactionID": "count",                             # Frequency
    "OrderValue": "sum"                                   # Monetary
}).reset_index()

rfm.rename(columns={
    "TransactionDate": "Recency",
    "TransactionID": "Frequency",
    "OrderValue": "Monetary"
}, inplace=True)

# Add any customers who haven't made any purchases (if any, though generator makes sure everyone has at least 1)
all_customers = pd.DataFrame({"CustomerID": df_cust["CustomerID"]})
rfm = pd.merge(all_customers, rfm, on="CustomerID", how="left")
rfm["Recency"] = rfm["Recency"].fillna((ref_date - df_cust["SignupDate"]).dt.days)
rfm["Frequency"] = rfm["Frequency"].fillna(0)
rfm["Monetary"] = rfm["Monetary"].fillna(0.0)

# 3. Traditional RFM Scoring (1 to 5)
print("Computing traditional RFM scores (1-5)...")
# Note: For Recency, smaller is better (score 5). For Frequency & Monetary, larger is better (score 5).
# Using qcut with duplicate handling (using rank method if bin edges are not unique)
rfm["R_Score"] = pd.qcut(rfm["Recency"], 5, labels=[5, 4, 3, 2, 1], duplicates="drop")
rfm["F_Score"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])
rfm["M_Score"] = pd.qcut(rfm["Monetary"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5])

# Convert scores to integers
rfm["R_Score"] = rfm["R_Score"].astype(int)
rfm["F_Score"] = rfm["F_Score"].astype(int)
rfm["M_Score"] = rfm["M_Score"].astype(int)

# RFM Cell (e.g. 555, 111)
rfm["RFM_Cell"] = rfm["R_Score"].astype(str) + rfm["F_Score"].astype(str) + rfm["M_Score"].astype(str)
# RFM Score (Sum of R, F, M)
rfm["RFM_Score"] = rfm["R_Score"] + rfm["F_Score"] + rfm["M_Score"]

# 4. K-Means Clustering on RFM
print("Preparing data for K-Means Clustering...")
# Add small constant to avoid log(0)
rfm_log = pd.DataFrame()
rfm_log["Recency"] = np.log1p(rfm["Recency"])
rfm_log["Frequency"] = np.log1p(rfm["Frequency"])
rfm_log["Monetary"] = np.log1p(rfm["Monetary"])

# Standardize features
scaler = StandardScaler()
rfm_scaled = scaler.fit_transform(rfm_log)

# Run K-Means with K=4
print("Running K-Means (K=4)...")
kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
rfm["Cluster"] = kmeans.fit_predict(rfm_scaled)

# 5. Dynamically Label Clusters Based on Centroids
# Champions: Low Recency (high score), High Frequency, High Monetary
# Lost: High Recency, Low Frequency, Low Monetary
# Loyalists: Low/Moderate Recency, High Frequency, Moderate/High Monetary
# At Risk: High Recency, Moderate/Low Frequency, Moderate Monetary

# Calculate mean log values for each cluster to rank them
centroids = rfm.groupby("Cluster").agg({
    "Recency": "mean",
    "Frequency": "mean",
    "Monetary": "mean"
}).reset_index()

# Define a scoring metric for clusters: higher frequency + higher monetary - recency
# To do this in log space or standardized space is cleaner. Let's compute a standardized score for each cluster centroid.
centroids_scaled = scaler.transform(np.log1p(centroids[["Recency", "Frequency", "Monetary"]]))
# Score = F + M - R
cluster_scores = centroids_scaled[:, 1] + centroids_scaled[:, 2] - centroids_scaled[:, 0]

# Rank clusters
ranked_clusters = np.argsort(cluster_scores) # array of indices sorting clusters from lowest score to highest score
# Lowest score -> Lost
# Second -> At Risk
# Third -> Loyalists
# Highest -> Champions
cluster_mapping = {
    ranked_clusters[0]: "Lost Customers",
    ranked_clusters[1]: "At Risk Customers",
    ranked_clusters[2]: "Loyalists",
    ranked_clusters[3]: "Champions"
}

rfm["Customer_Segment"] = rfm["Cluster"].map(cluster_mapping)
print("Cluster mapping determined:")
for c_id, label in cluster_mapping.items():
    cnt = len(rfm[rfm["Cluster"] == c_id])
    print(f"  Cluster {c_id}: {label} ({cnt} customers)")

# 6. Merge with customer metadata
print("Merging segments with customer demographic data...")
df_final = pd.merge(df_cust, rfm, on="CustomerID", how="inner")

# Save to CSV
output_path = os.path.join("data", "customer_rfm_segments.csv")
df_final.to_csv(output_path, index=False)
print(f"Successfully saved segmented customer data to {output_path}!")
