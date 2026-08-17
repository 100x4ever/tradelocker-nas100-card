import urllib.request
import urllib.error
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base_url = "https://live.tradelocker.com/backend-api"
headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

email = "jcollins92989@gmail.com"
password = "Pook&Buh9"
server = "HEROFX"

auth_payload = json.dumps({"email": email, "password": password, "server": server}).encode('utf-8')
req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=auth_payload, headers=headers, method="POST")
with urllib.request.urlopen(req, context=ctx) as resp:
    token = json.loads(resp.read().decode('utf-8'))["accessToken"]

auth_headers = dict(headers)
auth_headers["Authorization"] = f"Bearer {token}"
auth_headers["accNum"] = "18"

# 1. Config to check order columns
req = urllib.request.Request(f"{base_url}/trade/config", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    config = json.loads(resp.read().decode('utf-8')).get("d", {})
    pos_cols = [c["id"] for c in config.get("positionsConfig", {}).get("columns", [])]
    orders_cols = [c["id"] for c in config.get("ordersConfig", {}).get("columns", [])]
    print("Positions Columns:", pos_cols)
    print("Orders Columns:", orders_cols)

# 2. Positions
req = urllib.request.Request(f"{base_url}/trade/accounts/814241/positions", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    positions_data = json.loads(resp.read().decode('utf-8')).get("d", {}).get("positions", [])
    print(f"\nPositions Data:")
    for pos in positions_data:
        print(dict(zip(pos_cols, pos)))

# 3. Active Orders (Pending SL/TP orders)
req = urllib.request.Request(f"{base_url}/trade/accounts/814241/orders", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    orders_data = json.loads(resp.read().decode('utf-8')).get("d", {}).get("orders", [])
    print(f"\nActive Orders ({len(orders_data)}):")
    for o in orders_data:
        print(dict(zip(orders_cols, o)))
