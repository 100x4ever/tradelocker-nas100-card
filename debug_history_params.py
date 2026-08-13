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

# First check routeId from instrument details for instrument 3884
req = urllib.request.Request(f"{base_url}/trade/accounts/812189/instruments", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    insts = json.loads(resp.read().decode('utf-8')).get("d", {}).get("instruments", [])
    for inst in insts:
        if str(inst.get("id")) == "3884":
            print("Instrument 3884 details:", inst)
            routes = inst.get("routes", [])
            print("Routes:", routes)
            if routes:
                route_id = routes[0].get("id")
                print("Selected route_id:", route_id)

now_ms = int(time.time() * 1000)
from_ms = now_ms - (24 * 3600 * 1000) # 1 day ago

url = f"{base_url}/trade/history?tradableInstrumentId=3884&routeId=509994&resolution=5m&from={from_ms}&to={now_ms}"
print("\nFetching history URL:", url)
try:
    req = urllib.request.Request(url, headers=auth_headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("Raw history response keys:", list(res.get("d", {}).keys()))
        bars = res.get("d", {}).get("barDetails", []) or res.get("d", {}).get("bars", []) or res.get("d", {}).get("b", [])
        print(f"Total bars returned: {len(bars)}")
        if bars:
            print("Sample latest bar:", bars[-1])
        else:
            print("Full response data:", res)
except Exception as e:
    print("Error:", e)
