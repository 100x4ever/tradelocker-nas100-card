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

# 1. Config
req = urllib.request.Request(f"{base_url}/trade/config", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    config = json.loads(resp.read().decode('utf-8')).get("d", {})
    pos_cols = [c["id"] for c in config.get("positionsConfig", {}).get("columns", [])]
    orders_cols = [c["id"] for c in config.get("ordersConfig", {}).get("columns", [])]

# 2. Active Orders Map
req = urllib.request.Request(f"{base_url}/trade/accounts/814241/orders", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    orders_data = json.loads(resp.read().decode('utf-8')).get("d", {}).get("orders", [])

sl_tp_map = {}
for o in orders_data:
    o_dict = dict(zip(orders_cols, o))
    o_id = str(o_dict.get("id"))
    stop_p = o_dict.get("stopPrice")
    limit_p = o_dict.get("price")
    price_val = float(stop_p) if (stop_p and stop_p != 'None') else (float(limit_p) if (limit_p and limit_p != 'None') else None)
    sl_tp_map[o_id] = price_val

print("SL/TP Map from Active Orders:", sl_tp_map)

# 3. Positions mapping
req = urllib.request.Request(f"{base_url}/trade/accounts/814241/positions", headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    positions_data = json.loads(resp.read().decode('utf-8')).get("d", {}).get("positions", [])
    for pos in positions_data:
        p_dict = dict(zip(pos_cols, pos))
        p_id = str(p_dict.get("id"))
        sl_id = str(p_dict.get("stopLossId") or "")
        tp_id = str(p_dict.get("takeProfitId") or "")

        sl_price = sl_tp_map.get(sl_id)
        tp_price = sl_tp_map.get(tp_id)

        entry_p = float(p_dict.get("avgPrice"))
        qty = float(p_dict.get("qty"))
        side = p_dict.get("side")

        if sl_price:
            diff = (sl_price - entry_p) * qty if side == 'buy' else (entry_p - sl_price) * qty
            print(f"Position #{p_id} ({side.upper()} {qty}L @ {entry_p}): SL Price={sl_price} -> Shield Power: {'+' if diff>=0 else ''}${diff:.2f}")
