import urllib.request
import json
import ssl
from datetime import datetime

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def fetch_tradelocker_data(email, password, server, environment="demo"):
    base_url = f"https://{environment}.tradelocker.com/backend-api"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    # 1. Auth
    auth_data = json.dumps({"email": email, "password": password, "server": server}).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=auth_data, headers=headers, method="POST")
    with urllib.request.urlopen(req, context=ctx) as resp:
        auth_res = json.loads(resp.read().decode('utf-8'))
        token = auth_res["accessToken"]
        
    auth_headers = dict(headers)
    auth_headers["Authorization"] = f"Bearer {token}"
    
    # 2. Accounts
    req = urllib.request.Request(f"{base_url}/auth/jwt/all-accounts", headers=auth_headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        accounts = json.loads(resp.read().decode('utf-8')).get("accounts", [])
        
    if not accounts:
        return {"error": "No accounts found for user"}
        
    acc = accounts[0]
    acc_id = acc.get("id") or acc.get("accountId")
    acc_num = acc.get("accNum", 1)
    auth_headers["accNum"] = str(acc_num)
    
    # 3. Config
    req = urllib.request.Request(f"{base_url}/trade/config", headers=auth_headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        config = json.loads(resp.read().decode('utf-8')).get("d", {})
        
    # 4. Account State
    req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/state", headers=auth_headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        state_data = json.loads(resp.read().decode('utf-8')).get("d", {}).get("accountDetailsData", [])
        
    # 5. Instruments
    req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/instruments", headers=auth_headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        instruments = json.loads(resp.read().decode('utf-8')).get("d", {}).get("instruments", [])
        
    # 6. Positions
    req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/positions", headers=auth_headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        positions = json.loads(resp.read().decode('utf-8')).get("d", {}).get("positions", [])
        
    # 7. Orders History
    req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/ordersHistory", headers=auth_headers)
    with urllib.request.urlopen(req, context=ctx) as resp:
        history = json.loads(resp.read().decode('utf-8')).get("d", {}).get("ordersHistory", [])
        
    # Build column maps
    acc_cols = [c["id"] for c in config.get("accountDetailsConfig", {}).get("columns", [])]
    account_state = dict(zip(acc_cols, state_data))
    
    inst_map = {}
    for inst in instruments:
        inst_map[str(inst.get("id"))] = inst.get("name") or inst.get("symbol")
        
    # Parse Positions
    pos_cols = [c["id"] for c in config.get("positionsConfig", {}).get("columns", [])]
    open_positions = []
    open_pnl_by_inst = {"NAS100": 0.0, "EURUSD": 0.0, "OTHER": 0.0}
    
    for pos in positions:
        p_dict = dict(zip(pos_cols, pos))
        inst_id = str(p_dict.get("tradableInstrumentId"))
        inst_name = inst_map.get(inst_id, f"Inst-{inst_id}")
        unrealized = float(p_dict.get("unrealizedPl") or 0.0)
        
        p_dict["instrumentName"] = inst_name
        open_positions.append(p_dict)
        
        if "NAS" in inst_name.upper() or "US100" in inst_name.upper():
            open_pnl_by_inst["NAS100"] += unrealized
        elif "EURUSD" in inst_name.upper():
            open_pnl_by_inst["EURUSD"] += unrealized
        else:
            open_pnl_by_inst["OTHER"] += unrealized
            
    # Parse Orders History -> Position Trades
    hist_cols = [c["id"] for c in config.get("ordersHistoryConfig", {}).get("columns", [])]
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
        
    closed_trades = []
    instrument_metrics = {
        "OVERALL": {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0, "win_val": 0.0, "loss_val": 0.0},
        "NAS100": {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0, "win_val": 0.0, "loss_val": 0.0},
        "EURUSD": {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0, "win_val": 0.0, "loss_val": 0.0}
    }
    
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
        close_time = int(exit.get("lastModified") or exit.get("createdDate") or 0)
        
        pnl = (exit_p - entry_p) * qty if side == "buy" else (entry_p - exit_p) * qty
        
        trade_obj = {
            "positionId": p_id,
            "instrument": inst_name,
            "side": side,
            "qty": qty,
            "entryPrice": entry_p,
            "exitPrice": exit_p,
            "pnl": round(pnl, 2),
            "closeTime": close_time
        }
        closed_trades.append(trade_obj)
        
        # Categorize
        target_keys = ["OVERALL"]
        if "NAS" in inst_name.upper() or "US100" in inst_name.upper():
            target_keys.append("NAS100")
        elif "EURUSD" in inst_name.upper():
            target_keys.append("EURUSD")
            
        for k in target_keys:
            m = instrument_metrics[k]
            m["total"] += 1
            m["pnl"] += pnl
            if pnl >= 0:
                m["wins"] += 1
                m["win_val"] += pnl
            else:
                m["losses"] += 1
                m["loss_val"] += abs(pnl)
                
    # Calculate derived stats
    for k, m in instrument_metrics.items():
        total = m["total"]
        m["winRate"] = round((m["wins"] / total * 100), 1) if total > 0 else 0.0
        m["avgWin"] = round((m["win_val"] / m["wins"]), 2) if m["wins"] > 0 else 0.0
        m["avgLoss"] = round((m["loss_val"] / m["losses"]), 2) if m["losses"] > 0 else 0.0
        m["profitFactor"] = round((m["win_val"] / m["loss_val"]), 2) if m["loss_val"] > 0 else (round(m["win_val"], 2) if m["win_val"] > 0 else 0.0)
        m["pnl"] = round(m["pnl"], 2)
        
    balance = float(account_state.get("balance") or account_state.get("cashBalance") or 0.0)
    open_net_pnl = float(account_state.get("openNetPnL") or 0.0)
    equity = balance + open_net_pnl
    
    summary = {
        "account": {
            "accId": acc_id,
            "accNum": acc_num,
            "server": server,
            "balance": round(balance, 2),
            "equity": round(equity, 2),
            "openPnL": round(open_net_pnl, 2),
            "overallRealizedPnL": instrument_metrics["OVERALL"]["pnl"],
            "positionsCount": len(open_positions)
        },
        "openPnLByInstrument": open_pnl_by_inst,
        "metrics": instrument_metrics,
        "openPositions": open_positions,
        "closedTrades": closed_trades[:50] # Top 50 recent trades
    }
    return summary

print("Executing test fetch...")
res = fetch_tradelocker_data("jcollins92989@gmail.com", "Pook&Buh9", "HEROFX", "demo")
print(json.dumps(res, indent=2))
