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

accounts = make_request(f"{base_url}/auth/jwt/all-accounts", token=token).get("accounts", [])
acc = accounts[0]
acc_id = acc.get("id") or acc.get("accountId")
acc_num = acc.get("accNum", 1)

config = make_request(f"{base_url}/trade/config", token=token, acc_num=acc_num).get("d", {})
instruments = make_request(f"{base_url}/trade/accounts/{acc_id}/instruments", token=token, acc_num=acc_num).get("d", {}).get("instruments", [])
history = make_request(f"{base_url}/trade/accounts/{acc_id}/ordersHistory", token=token, acc_num=acc_num).get("d", {}).get("ordersHistory", [])

inst_map = {}
for inst in instruments:
    inst_map[str(inst.get("id"))] = inst.get("name") or inst.get("symbol")

cols = [c["id"] for c in config.get("ordersHistoryConfig", {}).get("columns", [])]

# Group orders by positionId
positions_map = {}
for row in history:
    o = dict(zip(cols, row))
    if o.get("status") != "Filled":
        continue
    p_id = o.get("positionId")
    if not p_id:
        continue
    if p_id not in positions_map:
        positions_map[p_id] = []
    positions_map[p_id].append(o)

print(f"Total Unique Closed Positions in History: {len(positions_map)}")

instrument_stats = {}

for p_id, orders in positions_map.items():
    # Sort orders by createdDate
    orders.sort(key=lambda x: int(x.get("createdDate", 0)))
    open_orders = [o for o in orders if o.get("isOpen") == "false" or o.get("isOpen") == False]
    close_orders = [o for o in orders if o.get("isOpen") == "true" or o.get("isOpen") == True]
    
    first_order = orders[0]
    inst_id = str(first_order.get("tradableInstrumentId"))
    inst_name = inst_map.get(inst_id, f"Inst-{inst_id}")
    
    # Simple PnL estimation from entry/exit prices if closed
    if len(orders) >= 2:
        entry = orders[0]
        exit = orders[-1]
        side = entry.get("side")
        qty = float(entry.get("filledQty") or entry.get("qty") or 0)
        entry_p = float(entry.get("avgPrice") or entry.get("price") or 0)
        exit_p = float(exit.get("avgPrice") or exit.get("price") or 0)
        
        pnl = 0
        if side == "buy":
            pnl = (exit_p - entry_p) * qty
        else:
            pnl = (entry_p - exit_p) * qty
            
        if inst_name not in instrument_stats:
            instrument_stats[inst_name] = {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "pnl": 0.0,
                "trades": []
            }
        
        s = instrument_stats[inst_name]
        s["total_trades"] += 1
        s["pnl"] += pnl
        if pnl >= 0:
            s["wins"] += 1
        else:
            s["losses"] += 1
        s["trades"].append({
            "positionId": p_id,
            "side": side,
            "qty": qty,
            "entry_p": entry_p,
            "exit_p": exit_p,
            "pnl": round(pnl, 2)
        })

print("\n=== STATS PER INSTRUMENT ===")
for name, s in instrument_stats.items():
    win_rate = (s["wins"] / s["total_trades"] * 100) if s["total_trades"] > 0 else 0
    print(f"\nInstrument: {name}")
    print(f"  Total Trades: {s['total_trades']}")
    print(f"  Wins: {s['wins']} | Losses: {s['losses']}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Est. PnL: ${s['pnl']:.2f}")
