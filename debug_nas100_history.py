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

base_url = "https://live.tradelocker.com/backend-api"
auth_payload = json.dumps(credentials).encode('utf-8')
req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=auth_payload, headers=headers, method="POST")
with urllib.request.urlopen(req, context=ctx) as resp:
    token = json.loads(resp.read().decode('utf-8'))["accessToken"]

auth_headers = dict(headers)
auth_headers["Authorization"] = f"Bearer {token}"
acc_id = "812189"
acc_num = "17"
auth_headers["accNum"] = acc_num

config = json.loads(urllib.request.urlopen(urllib.request.Request(f"{base_url}/trade/config", headers=auth_headers), context=ctx).read().decode('utf-8'))["d"]
instruments = json.loads(urllib.request.urlopen(urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/instruments", headers=auth_headers), context=ctx).read().decode('utf-8'))["d"]["instruments"]
history = json.loads(urllib.request.urlopen(urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/ordersHistory", headers=auth_headers), context=ctx).read().decode('utf-8'))["d"]["ordersHistory"]

inst_map = {str(i["id"]): (i.get("name") or i.get("symbol")) for i in instruments}
hist_cols = [c["id"] for c in config["ordersHistoryConfig"]["columns"]]

pos_groups = {}
for row in history:
    o = dict(zip(hist_cols, row))
    if o.get("status") != "Filled":
        continue
    p_id = o.get("positionId")
    if not p_id:
        continue
    if p_id not in pos_groups:
        pos_groups[p_id] = []
    pos_groups[p_id].append(o)

print(f"Total Unique Closed Positions: {len(pos_groups)}")

nas100_trades = []
nas100_pnl = 0.0
nas100_wins = 0
nas100_losses = 0
nas100_lots = 0.0

all_trades = []

for p_id, orders in pos_groups.items():
    orders.sort(key=lambda x: int(x.get("createdDate", 0)))
    if len(orders) < 2:
        continue
    entry = orders[0]
    exit = orders[-1]
    inst_id = str(entry.get("tradableInstrumentId"))
    inst_name = inst_map.get(inst_id, f"Inst-{inst_id}")
    
    side = entry.get("side")
    qty = float(entry.get("filledQty") or entry.get("qty") or 0)
    entry_p = float(entry.get("avgPrice") or entry.get("price") or 0)
    exit_p = float(exit.get("avgPrice") or exit.get("price") or 0)
    
    pnl = (exit_p - entry_p) * qty if side == "buy" else (entry_p - exit_p) * qty
    
    trade_info = {
        "p_id": p_id,
        "inst_id": inst_id,
        "inst_name": inst_name,
        "side": side,
        "qty": qty,
        "entry_p": entry_p,
        "exit_p": exit_p,
        "pnl": round(pnl, 2)
    }
    all_trades.append(trade_info)
    
    is_nas = "NAS" in inst_name.upper() or "US100" in inst_name.upper() or inst_id == "3884"
    if is_nas:
        nas100_trades.append(trade_info)
        nas100_pnl += pnl
        nas100_lots += qty
        if pnl >= 0:
            nas100_wins += 1
        else:
            nas100_losses += 1

print("\n=== NAS100 SPECIFIC STATS ===")
print(f"NAS100 Total Trades: {len(nas100_trades)}")
print(f"NAS100 Wins: {nas100_wins} | Losses: {nas100_losses}")
win_rate = (nas100_wins / len(nas100_trades) * 100) if nas100_trades else 0
print(f"NAS100 Win Rate: {win_rate:.1f}%")
print(f"NAS100 Cum PnL: ${nas100_pnl:.2f}")
print(f"NAS100 Total Traded Lots: {nas100_lots:.2f}")
print("\nNAS100 Trade List:")
for t in nas100_trades:
    print(t)

print("\n=== ALL TRADES BY INSTRUMENT ===")
inst_summary = {}
for t in all_trades:
    name = t["inst_name"]
    if name not in inst_summary:
        inst_summary[name] = {"count": 0, "pnl": 0.0}
    inst_summary[name]["count"] += 1
    inst_summary[name]["pnl"] += t["pnl"]

for k, v in inst_summary.items():
    print(f"Instrument: {k} -> Count: {v['count']}, PnL: ${v['pnl']:.2f}")
