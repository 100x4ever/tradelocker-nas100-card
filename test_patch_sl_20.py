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

# Position details: SELL 0.39 lots @ 30175.82
# For SELL: +$15.00 profit lock means SL price is BELOW entry price:
# sl_price = entry_p - (15.0 / qty) = 30175.82 - (15.0 / 0.39) = 30175.82 - 38.46 = 30137.36
pos_id = "72057594045687931"
entry_p = 30175.82
qty = 0.39
val_amt = 15.0

sl_price = round(entry_p - (val_amt / qty), 2)
print(f"Targeting SELL Position #{pos_id}: Entry={entry_p}, Qty={qty}, Target SL Price (+${val_amt}) = {sl_price}")

patch_body = json.dumps({"stopLoss": sl_price}).encode('utf-8')
url = f"{base_url}/trade/positions/{pos_id}"

try:
    req = urllib.request.Request(url, data=patch_body, headers=auth_headers, method="PATCH")
    with urllib.request.urlopen(req, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("PATCH SUCCESS Response:", res)
except urllib.error.HTTPError as e:
    print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print("Error:", e)
