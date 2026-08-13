import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

credentials = {
    "email": "jcollins92989@gmail.com",
    "password": "Pook&Buh9",
    "server": "HEROFX"
}

headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

base_url = "https://live.tradelocker.com/backend-api"
auth_payload = json.dumps(credentials).encode('utf-8')
req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=auth_payload, headers=headers, method="POST")
with urllib.request.urlopen(req, context=ctx) as resp:
    token = json.loads(resp.read().decode('utf-8'))["accessToken"]

auth_headers = dict(headers)
auth_headers["Authorization"] = f"Bearer {token}"

# Target user account 812189 (accNum 17)
acc_id = "812189"
acc_num = "17"
auth_headers["accNum"] = str(acc_num)

# Fetch Config
config = json.loads(urllib.request.urlopen(urllib.request.Request(f"{base_url}/trade/config", headers=auth_headers), context=ctx).read().decode('utf-8'))["d"]

# Fetch State
state_data = json.loads(urllib.request.urlopen(urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/state", headers=auth_headers), context=ctx).read().decode('utf-8'))["d"]["accountDetailsData"]

# Fetch Instruments
instruments = json.loads(urllib.request.urlopen(urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/instruments", headers=auth_headers), context=ctx).read().decode('utf-8'))["d"]["instruments"]

# Fetch Positions
positions = json.loads(urllib.request.urlopen(urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/positions", headers=auth_headers), context=ctx).read().decode('utf-8'))["d"]["positions"]

# Fetch History
history = json.loads(urllib.request.urlopen(urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/ordersHistory", headers=auth_headers), context=ctx).read().decode('utf-8'))["d"]["ordersHistory"]

acc_cols = [c["id"] for c in config["accountDetailsConfig"]["columns"]]
account_state = dict(zip(acc_cols, state_data))

print("=== ACCOUNT 812189 REAL STATE ===")
print("Balance:", account_state.get("balance"))
print("Equity:", float(account_state.get("balance", 0)) + float(account_state.get("openNetPnL", 0)))
print("Open Net PnL:", account_state.get("openNetPnL"))
print("Positions Count:", len(positions))
print("History Orders Count:", len(history))

inst_map = {str(i["id"]): (i.get("name") or i.get("symbol")) for i in instruments}

# Open positions detail
pos_cols = [c["id"] for c in config["positionsConfig"]["columns"]]
parsed_positions = []
for p in positions:
    pd = dict(zip(pos_cols, p))
    pd["instrumentName"] = inst_map.get(str(pd.get("tradableInstrumentId")), pd.get("tradableInstrumentId"))
    parsed_positions.append(pd)

print("\n=== OPEN POSITIONS IN ACCOUNT 812189 ===")
print(json.dumps(parsed_positions, indent=2))
