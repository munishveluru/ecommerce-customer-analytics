-- E-Commerce Customer Analytics and Segmentation Star Schema
-- Targets SQL engines like PostgreSQL, MySQL, SQLite, or SQL Server.

-- 1. Dimension Table: Customers (Processed with RFM & Clustering Outputs)
CREATE TABLE dim_customers_processed (
    customer_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    signup_date TIMESTAMP NOT NULL,
    country VARCHAR(50) NOT NULL,
    recency_days INT NOT NULL,
    frequency_orders INT NOT NULL,
    monetary_spend DECIMAL(12, 2) NOT NULL,
    r_score INT NOT NULL,
    f_score INT NOT NULL,
    m_score INT NOT NULL,
    rfm_cell VARCHAR(3) NOT NULL,
    rfm_score INT NOT NULL,
    kmeans_cluster INT NOT NULL,
    customer_segment VARCHAR(50) NOT NULL
);

-- Indexing for fast retrieval of customer segmentation details
CREATE INDEX idx_customer_segment ON dim_customers_processed(customer_segment);
CREATE INDEX idx_customer_cluster ON dim_customers_processed(kmeans_cluster);

-- 2. Fact Table: Transactions
CREATE TABLE fact_transactions (
    transaction_id VARCHAR(10) PRIMARY KEY,
    customer_id VARCHAR(10) NOT NULL,
    transaction_date TIMESTAMP NOT NULL,
    order_value DECIMAL(10, 2) NOT NULL,
    items_count INT NOT NULL,
    category VARCHAR(50) NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES dim_customers_processed(customer_id)
);

-- Indexing on foreign keys and dates for dashboard query optimization
CREATE INDEX idx_tx_customer ON fact_transactions(customer_id);
CREATE INDEX idx_tx_date ON fact_transactions(transaction_date);
CREATE INDEX idx_tx_category ON fact_transactions(category);
