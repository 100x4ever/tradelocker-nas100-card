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

# 1. Config to check columns
req = urllib.request.Request(f"{base_url}/trade/config", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    config = json.loads(resp.read().decode('utf-8')).get("d", {})
    pos_cols = [c["id"] for c in config.get("positionsConfig", {}).get("columns", [])]
    print("Positions Columns:", pos_cols)

# 2. Open positions
req = urllib.request.Request(f"{base_url}/trade/accounts/814241/positions", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    positions_data = json.loads(resp.read().decode('utf-8')).get("d", {}).get("positions", [])
    print(f"\nRaw Open Positions ({len(positions_data)}):")
    for pos in positions_data:
        p_dict = dict(zip(pos_cols, pos)) if pos_cols else {}
        print("POS DICT:", p_dict)

# 3. Account state
req = urllib.request.Request(f"{base_url}/trade/accounts/814241/state", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    state_data = json.loads(resp.read().decode('utf-8')).get("d", {}).get("accountDetailsData", [])
    acc_cols = [c["id"] for c in config.get("accountDetailsConfig", {}).get("columns", [])]
    acc_dict = dict(zip(acc_cols, state_data)) if acc_cols else {}
    print("\nAccount State DICT:", acc_dict)
