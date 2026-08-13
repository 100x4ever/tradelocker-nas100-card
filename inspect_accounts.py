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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

def inspect_env(env):
    base_url = f"https://{env}.tradelocker.com/backend-api"
    data = json.dumps(credentials).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            token = json.loads(resp.read().decode('utf-8'))["accessToken"]
            
        auth_headers = dict(headers)
        auth_headers["Authorization"] = f"Bearer {token}"
        
        req = urllib.request.Request(f"{base_url}/auth/jwt/all-accounts", headers=auth_headers)
        with urllib.request.urlopen(req, context=ctx) as resp:
            accounts_res = json.loads(resp.read().decode('utf-8'))
            print(f"=== {env.upper()} ACCOUNTS ===")
            print(json.dumps(accounts_res, indent=2))
            
            accounts = accounts_res.get("accounts", [])
            for acc in accounts:
                acc_id = acc.get("id") or acc.get("accountId")
                acc_num = acc.get("accNum")
                acc_name = acc.get("name") or acc.get("accountName")
                
                # Fetch state for this specific account
                h = dict(auth_headers)
                if acc_num is not None:
                    h["accNum"] = str(acc_num)
                st_req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/state", headers=h)
                try:
                    with urllib.request.urlopen(st_req, context=ctx) as st_resp:
                        st_data = json.loads(st_resp.read().decode('utf-8'))
                        print(f"\nAccount ID: {acc_id}, accNum: {acc_num}, Name: {acc_name}")
                        print("State summary:", st_data.get("d", {}).get("accountDetailsData", [])[:5])
                except Exception as e:
                    print(f"Error fetching state for acc {acc_id}: {e}")
    except Exception as e:
        print(f"Error inspecting {env}: {e}")

print("Inspecting DEMO...")
inspect_env("demo")

print("\nInspecting LIVE...")
inspect_env("live")
