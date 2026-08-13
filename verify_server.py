import urllib.request
import json

try:
    with urllib.request.urlopen("http://localhost:8000/api/summary") as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print("Server API Response Success!")
        print("Account:", data.get("account"))
        print("Metrics NAS100:", data.get("metrics", {}).get("NAS100"))
        print("Metrics EURUSD:", data.get("metrics", {}).get("EURUSD"))
        print("Metrics OVERALL:", data.get("metrics", {}).get("OVERALL"))
except Exception as e:
    print("Error querying server API:", e)
