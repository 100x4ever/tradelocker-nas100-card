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
auth_headers["accNum"] = "17"

now_ms = int(time.time() * 1000)
from_ms = now_ms - (100 * 5 * 60 * 1000)  # 100 5m candles back

url = f"{base_url}/trade/history?tradableInstrumentId=3884&routeId=509994&resolution=5m&from={from_ms}&to={now_ms}"
print("Fetching URL:", url)

try:
    req = urllib.request.Request(url, headers=auth_headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        bars = res.get("d", {}).get("barDetails", [])
        print(f"Success! Received {len(bars)} 5m bars.")
        if bars:
            print("Latest 3 bars:", bars[-3:])
except Exception as e:
    print("Error fetching history:", e)
