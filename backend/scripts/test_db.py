import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database_service import test_connection

result = test_connection()
if result["status"] == "success":
    print("✅ Connection successful!")
    print(result["version"])
else:
    print("❌ Connection failed!")
    print(result["message"])