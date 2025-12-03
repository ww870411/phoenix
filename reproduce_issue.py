import sys
import os
from datetime import date
import logging

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Configure logging to stdout
logging.basicConfig(level=logging.INFO)

from backend.services.data_analysis import _query_plan_month_rows

def test_query():
    print("Testing _query_plan_month_rows with ZhuChengQu...")
    
    # Test ZhuChengQu
    unit_key = "ZhuChengQu" 
    unit_label = "主城区"
    metric_keys = ["amount_power_generation"]
    metric_dict = {"amount_power_generation": "发电量"}
    period_start = date(2025, 11, 1)
    
    print(f"Parameters:")
    print(f"  unit_key: {unit_key}")
    print(f"  period_start: {period_start}")
    
    try:
        result = _query_plan_month_rows(
            unit_key=unit_key,
            unit_label=unit_label,
            metric_keys=metric_keys,
            metric_dict=metric_dict,
            period_start=period_start
        )
        
        print(f"\nResult for {unit_key}: {len(result)} items")
        if result:
            for key, val in result.items():
                print(f"{key}: {val}")
        else:
            print("No data found.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*30 + "\n")
    
    print("Testing _query_plan_month_rows with BeiHai (direct)...")
    
    # Test BeiHai
    unit_key_bh = "BeiHai"
    unit_label_bh = "北海热电厂"
    
    try:
        result_bh = _query_plan_month_rows(
            unit_key=unit_key_bh,
            unit_label=unit_label_bh,
            metric_keys=metric_keys,
            metric_dict=metric_dict,
            period_start=period_start
        )
        
        print(f"\nResult for {unit_key_bh}: {len(result_bh)} items")
        if result_bh:
             for key, val in result_bh.items():
                print(f"{key}: {val}")
        else:
            print("No data found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_query()
