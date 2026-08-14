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

pos_id = "72057594045587511"
patch_body = json.dumps({"trailingOffset": 10.0}).encode('utf-8')
url = f"{base_url}/trade/positions/{pos_id}"

print(f"PATCHing position {pos_id} with trailingOffset=10.0...")
try:
    req = urllib.request.Request(url, data=patch_body, headers=auth_headers, method="PATCH")
    with urllib.request.urlopen(req, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        print("Success response:", res)
except Exception as e:
    print("Error setting trailing stop:", e)
