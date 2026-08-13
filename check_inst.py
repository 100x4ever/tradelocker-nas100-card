import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

credentials = {
    "email": "jcollins92989@gmail.com",
    "password": "Pook&Buh9",
    "server": "HEROFX"
}

headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

def make_request(url, method="GET", token=None, acc_num=None):
    req_headers = dict(headers)
    if token:
        req_headers['Authorization'] = f"Bearer {token}"
    if acc_num is not None:
        req_headers['accNum'] = str(acc_num)
    
    req = urllib.request.Request(url, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"error": str(e)}

base_url = "https://demo.tradelocker.com/backend-api"
auth_res = make_request(f"{base_url}/auth/jwt/token", method="POST")
# wait, token with body
data = json.dumps(credentials).encode('utf-8')
req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=data, headers=headers, method="POST")
with urllib.request.urlopen(req, context=ctx) as resp:
    token = json.loads(resp.read().decode('utf-8'))["accessToken"]

accounts = make_request(f"{base_url}/auth/jwt/all-accounts", token=token).get("accounts", [])
acc = accounts[0]
acc_id = acc.get("id") or acc.get("accountId")
acc_num = acc.get("accNum", 1)

# try get instrument details for 4613
inst_detail = make_request(f"{base_url}/trade/instruments/4613", token=token, acc_num=acc_num)
print("Instrument 4613 detail:", json.dumps(inst_detail, indent=2))
