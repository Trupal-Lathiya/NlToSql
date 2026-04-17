import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.llm_service import generate_sql

schema_context = """
Table: Customers
Columns: CustomerID (int), CustomerName (varchar), City (varchar), Country (varchar)

Table: Orders  
Columns: OrderID (int), CustomerID (int), OrderDate (date), TotalAmount (decimal)
"""

result = generate_sql("Show me all customers from India", schema_context)

if result["status"] == "success":
    print("✅ SQL Generated:")
    print(result["sql"])
else:
    print("❌ Failed:", result["message"])