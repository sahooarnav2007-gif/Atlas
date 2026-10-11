import os
import random
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def generate_sample_sales_data(num_records: int = 1000, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    random.seed(seed)

    regions = ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East"]
    segments = ["Enterprise", "Mid-Market", "SMB", "Consumer"]
    statuses = ["active", "active", "active", "active", "cancelled", "pending"]  # cancelled represents ~16%
    
    start_date = datetime(2025, 1, 1)
    
    records = []
    for i in range(1, num_records + 1):
        txn_id = f"TXN-{100000 + i}"
        days_offset = random.randint(0, 365)
        dt = start_date + timedelta(days=days_offset)
        region = random.choice(regions)
        segment = random.choice(segments)
        status = random.choice(statuses)

        # Baseline order value varies by segment
        base_val = {"Enterprise": 1200, "Mid-Market": 600, "SMB": 250, "Consumer": 80}[segment]
        order_val = max(10, round(float(np.random.normal(base_val, base_val * 0.25)), 2))
        
        # Injected deliberate anomalies
        if i in [105, 230, 480, 712]:
            order_val = order_val * 12.0  # huge spike

        # Revenue
        discount = random.choice([0.0, 0.05, 0.1, 0.15])
        revenue = round(order_val * (1.0 - discount), 2)
        
        # Churn probability higher if cancelled or low order value
        churn = 1 if status == "cancelled" or random.random() < 0.12 else 0

        records.append({
            "transaction_id": txn_id,
            "date": dt.strftime("%Y-%m-%d"),
            "region": region,
            "customer_segment": segment,
            "customer_status": status,
            "order_value": order_val,
            "revenue": revenue,
            "churn": churn
        })

    return pd.DataFrame(records)

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "samples")
    os.makedirs(out_dir, exist_ok=True)
    
    df1 = generate_sample_sales_data(1000, seed=42)
    p1 = os.path.join(out_dir, "customer_sales_v1.csv")
    df1.to_csv(p1, index=False)
    print(f"Generated sample dataset: {p1} ({len(df1)} rows)")

    # Generate version 2 with newer records
    df2 = generate_sample_sales_data(1200, seed=99)
    p2 = os.path.join(out_dir, "customer_sales_v2.csv")
    df2.to_csv(p2, index=False)
    print(f"Generated sample dataset v2: {p2} ({len(df2)} rows)")
