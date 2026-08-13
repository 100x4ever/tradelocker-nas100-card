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
from_ms = now_ms - (300 * 5 * 60 * 1000)  # 300 5m bars back

test_urls = [
    f"{base_url}/trade/history?tradableInstrumentId=3884&routeId=509043&resolution=5m&from={from_ms}&to={now_ms}",
    f"{base_url}/trade/history?tradableInstrumentId=3884&routeId=509994&resolution=5m&from={from_ms}&to={now_ms}",
    f"{base_url}/trade/history?instrumentId=4537&routeId=509043&resolution=5m&from={from_ms}&to={now_ms}"
]

for url in test_urls:
    print("\nTesting History URL:", url)
    try:
        req = urllib.request.Request(url, headers=auth_headers)
        with urllib.request.urlopen(req, context=ctx) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print("Response status:", res.get("s"))
            bars = res.get("d", {}).get("barDetails", []) or res.get("d", {}).get("bars", []) or res.get("d", {}).get("b", [])
            print(f"Total bars returned: {len(bars)}")
            if bars:
                print("Latest bar:", bars[-1])
                print("Oldest bar:", bars[0])
            else:
                print("Response data:", res)
    except Exception as e:
        print("Error:", e)
