import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from services.query_pipeline import run_pipeline

nl_query = "give me all the username"

result = run_pipeline(nl_query)

if result["status"] == "success":
    print("\n✅ Pipeline successful!")
    print(f"\n📝 SQL:\n{result['sql']}")
    print(f"\n🗂️ Tables used: {result['retrieved_tables']}")
    print(f"\n📊 Total rows: {result['total_row_count']}")
    print(f"\n🤖 Summary:\n{result['summary']}")
    if result["csv_path"]:
        print(f"\n📁 CSV saved at: {result['csv_path']}")
else:
    print(f"\n❌ Pipeline failed: {result['message']}")