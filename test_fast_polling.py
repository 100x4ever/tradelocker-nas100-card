import urllib.request
import urllib.error
import json
import ssl
import time

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

print("--- 1. Initial Login ---")
auth_payload = json.dumps({"email": email, "password": password, "server": server}).encode('utf-8')
req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=auth_payload, headers=headers, method="POST")
with urllib.request.urlopen(req, context=ctx) as resp:
    token = json.loads(resp.read().decode('utf-8'))["accessToken"]

auth_headers = dict(headers)
auth_headers["Authorization"] = f"Bearer {token}"
auth_headers["accNum"] = "17"
acc_id = "812189"

print("--- 2. Simulating 3 rapid real-time state & positions polls ---")
for i in range(3):
    t0 = time.time()
    
    # State
    req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/state", headers=auth_headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        state = json.loads(resp.read().decode('utf-8')).get("d", {}).get("accountDetailsData", [])

    # Positions
    req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/positions", headers=auth_headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        positions = json.loads(resp.read().decode('utf-8')).get("d", {}).get("positions", [])

    elapsed = time.time() - t0
    
    # Extract state metrics (balance = idx 0, openNetPnL = idx 23)
    # Column mapping: balance, projectedBalance, availableFunds, ..., openNetPnL (idx 23)
    balance = state[0] if len(state) > 0 else 0
    open_net_pnl = state[23] if len(state) > 23 else 0
    equity = balance + open_net_pnl

    print(f"Poll #{i+1} ({elapsed:.3f}s): Equity = ${equity:.2f}, Open PnL = ${open_net_pnl:.2f}, Positions Count = {len(positions)}")
    time.sleep(1.0)
