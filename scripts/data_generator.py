import os
import csv
import random
from datetime import datetime, timedelta

# Create data directory if it doesn't exist
os.makedirs("data", exist_ok=True)

# Configuration
NUM_CUSTOMERS = 1000
NUM_TRANSACTIONS = 6500
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 8, 19)

# Seed for reproducibility
random.seed(42)

# Sample lists for generation
first_names = [
    "muneesh", "Aditya", "Amit", "Ananya", "Arjun", "Diya", "Isha", "Kabir", "Meera", "Neha",
    "Pranav", "Rohan", "Siddharth", "Tanvi", "Vikram", "James", "Emily", "Michael", "Sarah", "David",
    "John", "Jessica", "Robert", "Karen", "William", "Lisa", "Thomas", "Sandra", "Richard", "Ashley",
    "Rajesh", "Priya", "Sunita", "Vijay", "Anil", "Suresh", "Gita", "Deepak", "Sanjay", "Kiran"
]
last_names = [
    "Sharma", "Verma", "Gupta", "Mehta", "Patel", "Singh", "Joshi", "Rao", "Nair", "Reddy",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
    "Kumar", "Sen", "Roy", "Bose", "Das", "Choudhury", "Mukherjee", "Banerjee", "Chatterjee", "Mishra",
    "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin", "Thompson", "Young", "King"
]
countries = ["India", "United States", "United Kingdom", "Germany", "France", "Canada", "Australia", "Singapore"]
categories = ["Electronics", "Apparel", "Home & Kitchen", "Books", "Beauty & Personal Care", "Sports & Outdoors"]

# 1. Generate Customers
customers = []
customer_ids = [f"C{i:04d}" for i in range(1, NUM_CUSTOMERS + 1)]

print("Generating customer data...")
for cid in customer_ids:
    first = random.choice(first_names)
    last = random.choice(last_names)
    name = f"{first} {last}"
    email = f"{first.lower()}.{last.lower()}{random.randint(10, 99)}@example.com"
    
    # Random signup date between START_DATE and 6 months before END_DATE
    signup_days_limit = (END_DATE - START_DATE).days - 180
    signup_offset = random.randint(0, signup_days_limit)
    signup_date = START_DATE + timedelta(days=signup_offset)
    
    # Country distribution (weighted towards India and US)
    country = random.choices(countries, weights=[40, 25, 10, 8, 5, 5, 4, 3], k=1)[0]
    
    customers.append({
        "CustomerID": cid,
        "Name": name,
        "Email": email,
        "SignupDate": signup_date.strftime("%Y-%m-%d %H:%M:%S"),
        "Country": country
    })

# Write Customers CSV
customers_file = os.path.join("data", "dim_customers.csv")
with open(customers_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["CustomerID", "Name", "Email", "SignupDate", "Country"])
    writer.writeheader()
    writer.writerows(customers)
print(f"Saved {NUM_CUSTOMERS} customers to {customers_file}")

# 2. Generate Transactions
transactions = []
transaction_id = 100001

# Distribute transactions: Some customers are heavy buyers, some buy once and churn
# Assign a "purchase profile" weight to each customer
customer_weights = {}
for cid in customer_ids:
    profile = random.choices(["Champion", "Loyal", "Normal", "One-Time"], weights=[10, 20, 50, 20], k=1)[0]
    if profile == "Champion":
        customer_weights[cid] = (8, 20, 150.0, 500.0) # (min_purchases, max_purchases, min_spend, max_spend)
    elif profile == "Loyal":
        customer_weights[cid] = (4, 10, 60.0, 250.0)
    elif profile == "Normal":
        customer_weights[cid] = (2, 5, 20.0, 120.0)
    else: # One-Time
        customer_weights[cid] = (1, 1, 10.0, 80.0)

print("Generating transaction data...")
for cid, (min_p, max_p, min_s, max_s) in customer_weights.items():
    # Find signup date of this customer
    c_signup_str = next(c["SignupDate"] for c in customers if c["CustomerID"] == cid)
    c_signup = datetime.strptime(c_signup_str, "%Y-%m-%d %H:%M:%S")
    
    # Determine actual number of purchases
    num_purchases = random.randint(min_p, max_p)
    
    # Generate dates and values
    for _ in range(num_purchases):
        # Transaction date must be after signup date
        max_days = (END_DATE - c_signup).days
        if max_days <= 0:
            tx_date = c_signup
        else:
            tx_offset = random.randint(0, max_days)
            tx_date = c_signup + timedelta(days=tx_offset)
            
        # Spend value: right-skewed normal distribution
        spend = round(random.uniform(min_s, max_s), 2)
        items = random.randint(1, 5) if spend < 100 else random.randint(3, 10)
        category = random.choices(categories, weights=[25, 30, 15, 10, 12, 8], k=1)[0]
        
        transactions.append({
            "TransactionID": f"TX{transaction_id}",
            "CustomerID": cid,
            "TransactionDate": tx_date.strftime("%Y-%m-%d %H:%M:%S"),
            "OrderValue": spend,
            "ItemsCount": items,
            "Category": category
        })
        transaction_id += 1

# Sort transactions by date
transactions.sort(key=lambda x: x["TransactionDate"])

# Write Transactions CSV
transactions_file = os.path.join("data", "raw_transactions.csv")
with open(transactions_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["TransactionID", "CustomerID", "TransactionDate", "OrderValue", "ItemsCount", "Category"])
    writer.writeheader()
    writer.writerows(transactions)
print(f"Saved {len(transactions)} transactions to {transactions_file}")
print("Data generation complete!")
