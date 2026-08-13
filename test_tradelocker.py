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

def make_request(url, method="GET", token=None, acc_num=None, body=None):
    req_headers = dict(headers)
    if token:
        req_headers['Authorization'] = f"Bearer {token}"
    if acc_num is not None:
        req_headers['accNum'] = str(acc_num)
    
    data = json.dumps(body).encode('utf-8') if body else None
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        err_content = e.read().decode('utf-8') if e.fp else ""
        return {"error": f"HTTP {e.code}: {e.reason}", "body": err_content}
    except Exception as e:
        return {"error": str(e)}

# Step 1: Auth
base_url = "https://live.tradelocker.com/backend-api"
auth_res = make_request(f"{base_url}/auth/jwt/token", method="POST", body=credentials)
token = auth_res.get("accessToken")
print("Access Token acquired!")

# Step 2: Get all accounts
accounts_res = make_request(f"{base_url}/auth/jwt/all-accounts", token=token)
print("\n--- ALL ACCOUNTS ---")
print(json.dumps(accounts_res, indent=2))

accounts = accounts_res.get("accounts", [])
if not accounts:
    # Try demo environment if live has 0 accounts
    base_url = "https://demo.tradelocker.com/backend-api"
    auth_res = make_request(f"{base_url}/auth/jwt/token", method="POST", body=credentials)
    token = auth_res.get("accessToken")
    accounts_res = make_request(f"{base_url}/auth/jwt/all-accounts", token=token)
    print("\n--- ALL ACCOUNTS (DEMO) ---")
    print(json.dumps(accounts_res, indent=2))
    accounts = accounts_res.get("accounts", [])

if accounts:
    selected_acc = accounts[0]
    acc_id = selected_acc.get("id") or selected_acc.get("accountId")
    acc_num = selected_acc.get("accNum", 1)
    
    print(f"\nUsing Selected Account ID: {acc_id}, accNum: {acc_num}")
    
    # Step 3: Fetch Config
    config_res = make_request(f"{base_url}/trade/config", token=token, acc_num=acc_num)
    print("\n--- CONFIG ---")
    print("Keys in Config:", list(config_res.get("d", {}).keys()))
    
    # Step 4: Fetch State
    state_res = make_request(f"{base_url}/trade/accounts/{acc_id}/state", token=token, acc_num=acc_num)
    print("\n--- ACCOUNT STATE ---")
    print(json.dumps(state_res, indent=2))
    
    # Step 5: Fetch Instruments
    instruments_res = make_request(f"{base_url}/trade/accounts/{acc_id}/instruments", token=token, acc_num=acc_num)
    print("\n--- INSTRUMENTS COUNT ---")
    instruments = instruments_res.get("d", {}).get("instruments", [])
    print(f"Total Instruments: {len(instruments)}")
    # Find NAS100 and EURUSD instrument IDs
    for inst in instruments:
        name = inst.get("name", "")
        if "NAS" in name.upper() or "US100" in name.upper() or "EURUSD" in name.upper():
            print(f"Matched Instrument: ID={inst.get('id')}, Name={inst.get('name')}, Symbol={inst.get('symbol')}")
            
    # Step 6: Fetch Positions
    positions_res = make_request(f"{base_url}/trade/accounts/{acc_id}/positions", token=token, acc_num=acc_num)
    print("\n--- POSITIONS ---")
    print(json.dumps(positions_res, indent=2))

    # Step 7: Fetch Orders History
    history_res = make_request(f"{base_url}/trade/accounts/{acc_id}/ordersHistory", token=token, acc_num=acc_num)
    print("\n--- ORDERS HISTORY ---")
    print(json.dumps(history_res, indent=2))
