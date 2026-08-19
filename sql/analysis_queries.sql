-- Recruiter-grade analytical SQL queries for E-Commerce Customer Analytics
-- Built for PostgreSQL, MySQL, and generic modern SQL engines.

-- =====================================================================
-- QUERY 1: Calculate RFM Metrics & Scores Entirely in SQL
-- (Used to replicate/verify python results inside the database layer)
-- =====================================================================
WITH reference_date AS (
    -- Reference date is set to 1 day after the maximum transaction date
    SELECT MAX(transaction_date) + INTERVAL '1 day' AS ref_date
    FROM fact_transactions
),
customer_rfm_raw AS (
    SELECT 
        t.customer_id,
        EXTRACT(DAY FROM (ref.ref_date - MAX(t.transaction_date))) AS recency,
        COUNT(t.transaction_id) AS frequency,
        SUM(t.order_value) AS monetary
    FROM fact_transactions t
    CROSS JOIN reference_date ref
    GROUP BY t.customer_id, ref.ref_date
),
rfm_tiles AS (
    SELECT 
        customer_id,
        recency,
        frequency,
        monetary,
        -- Recency: 5 is most recent (lowest recency value)
        NTILE(5) OVER (ORDER BY recency DESC) AS r_score,
        -- Frequency & Monetary: 5 is highest
        NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC) AS m_score
    FROM customer_rfm_raw
)
SELECT 
    customer_id,
    recency,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    (r_score || f_score || m_score) AS rfm_cell,
    (r_score + f_score + m_score) AS rfm_score
FROM rfm_tiles
ORDER BY rfm_score DESC, monetary DESC
LIMIT 10;


-- =====================================================================
-- QUERY 2: Customer Segment Profiles (K-Means Output Analysis)
-- Summarizes headcount, average metrics, and revenue contribution by segment.
-- =====================================================================
SELECT 
    customer_segment,
    COUNT(customer_id) AS total_customers,
    ROUND(100.0 * COUNT(customer_id) / SUM(COUNT(customer_id)) OVER (), 2) AS customer_percentage,
    ROUND(AVG(recency_days), 1) AS avg_recency_days,
    ROUND(AVG(frequency_orders), 1) AS avg_frequency_orders,
    ROUND(AVG(monetary_spend), 2) AS avg_spend_per_customer,
    ROUND(SUM(monetary_spend), 2) AS total_segment_revenue,
    ROUND(100.0 * SUM(monetary_spend) / SUM(SUM(monetary_spend)) OVER (), 2) AS revenue_contribution_pct
FROM dim_customers_processed
GROUP BY customer_segment
ORDER BY avg_spend_per_customer DESC;


-- =====================================================================
-- QUERY 3: Monthly Cohort Retention Analysis
-- Tracks repeat purchase behavior based on customer's signup cohort.
-- =====================================================================
WITH cohort_signups AS (
    -- Group customers into monthly cohorts based on signup date
    SELECT 
        customer_id,
        DATE_TRUNC('month', signup_date) AS cohort_month
    FROM dim_customers_processed
),
purchase_months AS (
    -- Find all distinct months in which each customer made a purchase
    SELECT DISTINCT
        customer_id,
        DATE_TRUNC('month', transaction_date) AS purchase_month
    FROM fact_transactions
),
cohort_size AS (
    -- Total count of customers who signed up in each cohort
    SELECT 
        cohort_month,
        COUNT(customer_id) AS total_signup_size
    FROM cohort_signups
    GROUP BY cohort_month
),
retention_matrix AS (
    -- Calculate active customers in subsequent months
    SELECT 
        s.cohort_month,
        p.purchase_month,
        -- Number of months between cohort signup and purchase month
        (EXTRACT(YEAR FROM p.purchase_month) - EXTRACT(YEAR FROM s.cohort_month)) * 12 +
        (EXTRACT(MONTH FROM p.purchase_month) - EXTRACT(MONTH FROM s.cohort_month)) AS period_offset,
        COUNT(DISTINCT s.customer_id) AS active_customers
    FROM cohort_signups s
    INNER JOIN purchase_months p ON s.customer_id = p.customer_id
    WHERE p.purchase_month >= s.cohort_month
    GROUP BY s.cohort_month, p.purchase_month
)
SELECT 
    TO_CHAR(r.cohort_month, 'YYYY-MM') AS cohort,
    cs.total_signup_size,
    r.period_offset AS month_index,
    r.active_customers,
    ROUND(100.0 * r.active_customers / cs.total_signup_size, 2) AS retention_rate_pct
FROM retention_matrix r
INNER JOIN cohort_size cs ON r.cohort_month = cs.cohort_month
ORDER BY r.cohort_month, r.period_offset;


-- =====================================================================
-- QUERY 4: Product Category Affinities by Customer Segment
-- Identifies top-performing product categories for each segment to personalize marketing campaigns.
-- =====================================================================
WITH segment_category_spend AS (
    SELECT 
        c.customer_segment,
        t.category,
        SUM(t.order_value) AS category_revenue,
        COUNT(t.transaction_id) AS purchase_count
    FROM fact_transactions t
    INNER JOIN dim_customers_processed c ON t.customer_id = c.customer_id
    GROUP BY c.customer_segment, t.category
),
ranked_categories AS (
    SELECT 
        customer_segment,
        category,
        category_revenue,
        purchase_count,
        RANK() OVER (PARTITION BY customer_segment ORDER BY category_revenue DESC) AS rev_rank
    FROM segment_category_spend
)
SELECT 
    customer_segment,
    category,
    ROUND(category_revenue, 2) AS total_spend,
    purchase_count,
    rev_rank
FROM ranked_categories
WHERE rev_rank <= 3
ORDER BY customer_segment, rev_rank;


-- =====================================================================
-- QUERY 5: Target "At Risk" Champions
-- Generates a targeted outreach list of historically high-spending customers
-- who are slipping (high recency) to prevent permanent churn.
-- =====================================================================
SELECT 
    customer_id,
    name,
    email,
    country,
    recency_days,
    frequency_orders,
    monetary_spend AS historical_lifetime_spend,
    rfm_cell
FROM dim_customers_processed
WHERE customer_segment = 'At Risk Customers'
  AND monetary_spend >= 150.0
ORDER BY monetary_spend DESC, recency_days ASC
LIMIT 50;
