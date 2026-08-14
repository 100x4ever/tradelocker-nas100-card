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

# Fetch all accounts
req_acc = urllib.request.Request(f"{base_url}/auth/jwt/all-accounts", headers=auth_headers)
with urllib.request.urlopen(req_acc, context=ctx) as resp:
    accounts = json.loads(resp.read().decode('utf-8')).get("accounts", [])
    print("All Accounts found:")
    target_acc = None
    for a in accounts:
        print(f" - Acc ID: {a.get('id')}, Acc Num: {a.get('accNum')}, Name: {a.get('name')}, Status: {a.get('status')}")
        if str(a.get("id")) == "814241" or str(a.get("accNum")) == "814241":
            target_acc = a

    if target_acc:
        print("\nTarget Account 814241 matched!")
        print("Details:", target_acc)
