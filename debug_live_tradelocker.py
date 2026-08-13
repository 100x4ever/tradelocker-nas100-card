import urllib.request
import urllib.error
import json
import ssl
import sys

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

print("--- 1. Authenticating with TradeLocker ---")
auth_payload = json.dumps({"email": email, "password": password, "server": server}).encode('utf-8')
req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=auth_payload, headers=headers, method="POST")

try:
    with urllib.request.urlopen(req, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        token = res["accessToken"]
        print("JWT Auth Success! Token:", token[:20] + "...")
except Exception as e:
    print("Auth Error:", e)
    sys.exit(1)

auth_headers = dict(headers)
auth_headers["Authorization"] = f"Bearer {token}"

print("\n--- 2. Fetching All Accounts ---")
req = urllib.request.Request(f"{base_url}/auth/jwt/all-accounts", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    acc_res = json.loads(resp.read().decode('utf-8'))
    accounts = acc_res.get("accounts", [])
    print(f"Found {len(accounts)} accounts:")
    for a in accounts:
        print(f" - ID: {a.get('id')}, accNum: {a.get('accNum')}, Name: {a.get('name')}, Balance: {a.get('accountBalance')}")

target_acc = None
for a in accounts:
    if str(a.get("id")) == "812189":
        target_acc = a
        break

if not target_acc:
    print("Target 812189 not found! Using first account...")
    target_acc = accounts[0]

acc_id = str(target_acc.get("id"))
acc_num = str(target_acc.get("accNum"))
print(f"\n--- Selected Account ID: {acc_id}, accNum: {acc_num} ---")

auth_headers["accNum"] = acc_num

print("\n--- 3. Fetching Config ---")
req = urllib.request.Request(f"{base_url}/trade/config", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    config = json.loads(resp.read().decode('utf-8')).get("d", {})

acc_cols = [c["id"] for c in config.get("accountDetailsConfig", {}).get("columns", [])]
print("Account State Columns:", acc_cols)

print("\n--- 4. Fetching Account State ---")
req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/state", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    state_raw = json.loads(resp.read().decode('utf-8')).get("d", {}).get("accountDetailsData", [])
    state_dict = dict(zip(acc_cols, state_raw))
    print("Account State:", json.dumps(state_dict, indent=2))

print("\n--- 5. Fetching Open Positions ---")
req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/positions", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    pos_raw = json.loads(resp.read().decode('utf-8')).get("d", {}).get("positions", [])
    print(f"Open Positions Count: {len(pos_raw)}")
    pos_cols = [c["id"] for c in config.get("positionsConfig", {}).get("columns", [])]
    for p in pos_raw:
        p_dict = dict(zip(pos_cols, p))
        print(" Position:", p_dict)
