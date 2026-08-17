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

# 1. Inspect current position & active orders
req = urllib.request.Request(f"{base_url}/trade/accounts/814241/positions", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    positions = json.loads(resp.read().decode('utf-8')).get("d", {}).get("positions", [])
    print("Open Positions:", positions)

if positions:
    pos = positions[0]
    pos_id = str(pos[0])
    side = str(pos[3]).lower()
    qty = float(pos[4])
    entry_p = float(pos[5])
    unrealized = float(pos[9])

    print(f"\nPosition #{pos_id}: {side.upper()} {qty}L @ {entry_p}, Current PnL: +${unrealized:.2f}")

    # Calculate SL price for +$40.00 profit lock
    val_amt = 40.0
    if side == "buy":
        sl_price = round(entry_p + (val_amt / qty), 2)
    else:
        sl_price = round(entry_p - (val_amt / qty), 2)

    print(f"Targeting +${val_amt} SL Price: {sl_price}")

    patch_body = json.dumps({"stopLoss": sl_price}).encode('utf-8')
    url = f"{base_url}/trade/positions/{pos_id}"

    try:
        req = urllib.request.Request(url, data=patch_body, headers=auth_headers, method="PATCH")
        with urllib.request.urlopen(req, context=ctx) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print("PATCH Response:", res)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print("Error:", e)
