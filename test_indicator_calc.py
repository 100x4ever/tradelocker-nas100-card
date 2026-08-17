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

auth_payload = json.dumps({"email": email, "password": password, "server": server}).encode('utf-8')
req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=auth_payload, headers=headers, method="POST")
with urllib.request.urlopen(req, context=ctx) as resp:
    token = json.loads(resp.read().decode('utf-8'))["accessToken"]

auth_headers = dict(headers)
auth_headers["Authorization"] = f"Bearer {token}"
auth_headers["accNum"] = "18"

now_ms = int(time.time() * 1000)
from_ms = now_ms - (300 * 5 * 60 * 1000) # 300 5m bars back
history_url = f"{base_url}/trade/history?tradableInstrumentId=3884&routeId=509043&resolution=5m&from={from_ms}&to={now_ms}"

req_h = urllib.request.Request(history_url, headers=auth_headers)
with urllib.request.urlopen(req_h, context=ctx) as r_h:
    bars = json.loads(r_h.read().decode('utf-8')).get("d", {}).get("barDetails", [])
    print(f"Fetched {len(bars)} 5m NAS100 bars.")

if len(bars) > 10:
    print("Latest Bar:", bars[-1])
    print("Previous Bar:", bars[-2])
