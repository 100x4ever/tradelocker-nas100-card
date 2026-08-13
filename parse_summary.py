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
    except Exception as e:
        return {"error": str(e)}

base_url = "https://demo.tradelocker.com/backend-api"
auth_res = make_request(f"{base_url}/auth/jwt/token", method="POST", body=credentials)
token = auth_res.get("accessToken")

accounts_res = make_request(f"{base_url}/auth/jwt/all-accounts", token=token)
accounts = accounts_res.get("accounts", [])
acc = accounts[0]
acc_id = acc.get("id") or acc.get("accountId")
acc_num = acc.get("accNum", 1)

config = make_request(f"{base_url}/trade/config", token=token, acc_num=acc_num).get("d", {})
state_data = make_request(f"{base_url}/trade/accounts/{acc_id}/state", token=token, acc_num=acc_num).get("d", {}).get("accountDetailsData", [])
instruments = make_request(f"{base_url}/trade/accounts/{acc_id}/instruments", token=token, acc_num=acc_num).get("d", {}).get("instruments", [])
positions = make_request(f"{base_url}/trade/accounts/{acc_id}/positions", token=token, acc_num=acc_num).get("d", {}).get("positions", [])
history = make_request(f"{base_url}/trade/accounts/{acc_id}/ordersHistory", token=token, acc_num=acc_num).get("d", {}).get("ordersHistory", [])

# Map account details
acc_cols = [c["id"] for c in config.get("accountDetailsConfig", {}).get("columns", [])]
account_state = dict(zip(acc_cols, state_data))

print("=== ACCOUNT STATE MAP ===")
for k, v in account_state.items():
    print(f"  {k}: {v}")

# Map instruments by ID
inst_map = {}
for inst in instruments:
    inst_id = str(inst.get("id"))
    name = inst.get("name") or inst.get("symbol")
    inst_map[inst_id] = name

print("\n=== RELEVANT INSTRUMENTS ===")
for i_id, name in inst_map.items():
    if any(k in name.upper() for k in ["NAS", "100", "EUR", "USD", "BTC", "XAU"]):
        print(f"  ID {i_id}: {name}")

# Map open positions
pos_cols = [c["id"] for c in config.get("positionsConfig", {}).get("columns", [])]
parsed_positions = []
for pos in positions:
    p_dict = dict(zip(pos_cols, pos))
    inst_name = inst_map.get(str(p_dict.get("tradableInstrumentId")), p_dict.get("tradableInstrumentId"))
    p_dict["instrumentName"] = inst_name
    parsed_positions.append(p_dict)

print("\n=== OPEN POSITIONS ===")
print(json.dumps(parsed_positions, indent=2))
