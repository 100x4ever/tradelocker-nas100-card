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

req = urllib.request.Request(f"{base_url}/trade/accounts/812189/instruments", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    insts = json.loads(resp.read().decode('utf-8')).get("d", {}).get("instruments", [])
    print(f"Total Instruments Found: {len(insts)}")
    for inst in insts:
        name = inst.get("name") or inst.get("symbol") or ""
        if "NAS" in name.upper() or "100" in name.upper() or "US" in name.upper():
            print("Target Match:", inst)
