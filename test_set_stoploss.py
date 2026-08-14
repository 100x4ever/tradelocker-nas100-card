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
auth_headers["accNum"] = "17"

# 1. Get current open positions
req = urllib.request.Request(f"{base_url}/trade/accounts/812189/positions", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    positions = json.loads(resp.read().decode('utf-8')).get("d", {}).get("positions", [])

print(f"Found {len(positions)} open positions:")
for p in positions:
    pos_id = p[0]
    side = p[3]
    qty = float(p[4])
    entry_p = float(p[5])
    
    loss_5 = 5.0
    sl_5_price = round(entry_p - (loss_5 / qty) if side == 'buy' else entry_p + (loss_5 / qty), 2)
    
    loss_10 = 10.0
    sl_10_price = round(entry_p - (loss_10 / qty) if side == 'buy' else entry_p + (loss_10 / qty), 2)

    print(f" - Pos #{pos_id} | Side: {side} | Qty: {qty} | Entry: {entry_p}")
    print(f"   -$5 SL Price: {sl_5_price} | -$10 SL Price: {sl_10_price}")
