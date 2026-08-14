import http.server
import socketserver
import json
import urllib.request
import urllib.error
import ssl
import os
import mimetypes
import time

PORT = int(os.environ.get("PORT", 8000))
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), 'public')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# User Session State (Locked to LIVE Account 814241)
session_config = {
    "live_mode": True,
    "email": "jcollins92989@gmail.com",
    "password": "Pook&Buh9",
    "server": "HEROFX",
    "environment": "live",
    "target_acc_id": "814241",
    "token": None,
    "token_time": 0,
    "acc_id": None,
    "acc_num": None
}

# Cache for static metadata (TTL = 60s)
meta_cache = {
    "last_fetch": 0,
    "config": None,
    "instruments": None,
    "history": None,
    "inst_map": {},
    "closed_trades": [],
    "metrics": None
}

# Real-time state cache (TTL = 2.0s)
live_cache = {
    "last_fetch": 0,
    "data": None
}

# 5m Bars cache for real-time stochastic calculation (TTL = 2.0s)
bars_cache = {
    "last_fetch": 0,
    "bars": []
}

# Track auto-triggered +$5 SL for position IDs to prevent duplicate calls
auto_sl_triggered = set()

def get_jwt_token():
    """Authenticate and fetch a fresh TradeLocker JWT token."""
    base_url = f"https://{session_config['environment']}.tradelocker.com/backend-api"
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    auth_payload = json.dumps({
        "email": session_config["email"],
        "password": session_config["password"],
        "server": session_config["server"]
    }).encode('utf-8')

    req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=auth_payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, context=ctx) as resp:
        res = json.loads(resp.read().decode('utf-8'))
        token = res["accessToken"]
        session_config["token"] = token
        session_config["token_time"] = time.time()

        auth_headers = dict(headers)
        auth_headers["Authorization"] = f"Bearer {token}"
        req_acc = urllib.request.Request(f"{base_url}/auth/jwt/all-accounts", headers=auth_headers)
        with urllib.request.urlopen(req_acc, context=ctx) as r_acc:
            accounts_data = json.loads(r_acc.read().decode('utf-8')).get("accounts", [])
            target_id = str(session_config["target_acc_id"])
            selected = None
            for a in accounts_data:
                if str(a.get("id")) == target_id or str(a.get("accNum")) == target_id:
                    selected = a
                    break
            if not selected and accounts_data:
                selected = accounts_data[0]
            if selected:
                session_config["acc_id"] = str(selected.get("id"))
                session_config["acc_num"] = str(selected.get("accNum", 18))

        print(f"[{time.strftime('%H:%M:%S')}] TradeLocker Auth Success! accId={session_config['acc_id']}, accNum={session_config['acc_num']}")
        return token

def calculate_stochastic(bars, k_period, k_slowing, d_smoothing):
    if not bars or len(bars) < k_period:
        return {"k": 50.0, "d": 50.0, "status": "NEUTRAL", "class": "neutral"}

    raw_k_list = []
    for i in range(len(bars)):
        if i < k_period - 1:
            raw_k_list.append(50.0)
            continue
        window = bars[i - k_period + 1 : i + 1]
        highest_h = max(b["h"] for b in window)
        lowest_l = min(b["l"] for b in window)
        current_c = window[-1]["c"]
        
        if highest_h == lowest_l:
            k_val = 50.0
        else:
            k_val = ((current_c - lowest_l) / (highest_h - lowest_l)) * 100.0
        raw_k_list.append(k_val)

    smoothed_k_list = []
    for i in range(len(raw_k_list)):
        if i < k_slowing - 1:
            smoothed_k_list.append(raw_k_list[i])
            continue
        sub = raw_k_list[i - k_slowing + 1 : i + 1]
        smoothed_k_list.append(sum(sub) / k_slowing)

    d_list = []
    for i in range(len(smoothed_k_list)):
        if i < d_smoothing - 1:
            d_list.append(smoothed_k_list[i])
            continue
        sub = smoothed_k_list[i - d_smoothing + 1 : i + 1]
        d_list.append(sum(sub) / d_smoothing)

    final_k = round(smoothed_k_list[-1], 1)
    final_d = round(d_list[-1], 1)

    if final_d >= 90.0:
        status, cls = "EXTREME OB", "extreme-ob"
    elif final_d >= 80.0:
        status, cls = "OB", "ob"
    elif final_d <= 10.0:
        status, cls = "EXTREME OS", "extreme-os"
    elif final_d <= 20.0:
        status, cls = "OS", "os"
    else:
        status, cls = "NEUTRAL", "neutral"

    return {
        "k": final_k,
        "d": final_d,
        "status": status,
        "class": cls
    }

def fetch_live_stochastics(auth_headers, base_url):
    """Fetch 5m NAS100 bars and calculate Fast (7,3,3) & Heavy (40,1,4) in real-time."""
    now = time.time()
    if bars_cache["bars"] and (now - bars_cache["last_fetch"]) < 2.0:
        bars = bars_cache["bars"]
    else:
        now_ms = int(now * 1000)
        from_ms = now_ms - (300 * 5 * 60 * 1000) # 300 5m bars back
        history_url = f"{base_url}/trade/history?tradableInstrumentId=3884&routeId=509043&resolution=5m&from={from_ms}&to={now_ms}"
        try:
            req_h = urllib.request.Request(history_url, headers=auth_headers)
            with urllib.request.urlopen(req_h, context=ctx) as r_h:
                bars = json.loads(r_h.read().decode('utf-8')).get("d", {}).get("barDetails", [])
                if bars:
                    bars_cache["bars"] = bars
                    bars_cache["last_fetch"] = now
                else:
                    bars = bars_cache["bars"]
        except Exception as e:
            print("Realtime stoch history exception:", e)
            bars = bars_cache["bars"]

    stoch_fast = calculate_stochastic(bars, 7, 3, 3)
    stoch_heavy = calculate_stochastic(bars, 40, 1, 4)

    return {
        "timeframe": "5m",
        "stoch_fast": stoch_fast,
        "stoch_heavy": stoch_heavy
    }

def refresh_metadata(auth_headers, base_url, acc_id):
    """Fetch heavy metadata (config, instruments, trade history) - cached for 60s."""
    now = time.time()
    if meta_cache["config"] and (now - meta_cache["last_fetch"]) < 60:
        return

    try:
        req = urllib.request.Request(f"{base_url}/trade/config", headers=auth_headers)
        with urllib.request.urlopen(req, context=ctx) as resp:
            meta_cache["config"] = json.loads(resp.read().decode('utf-8')).get("d", {})

        req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/instruments", headers=auth_headers)
        with urllib.request.urlopen(req, context=ctx) as resp:
            instruments = json.loads(resp.read().decode('utf-8')).get("d", {}).get("instruments", [])
            meta_cache["instruments"] = instruments
            inst_map = {}
            for inst in instruments:
                inst_map[str(inst.get("id"))] = inst.get("name") or inst.get("symbol")
            meta_cache["inst_map"] = inst_map

        req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/ordersHistory", headers=auth_headers)
        with urllib.request.urlopen(req, context=ctx) as resp:
            history = json.loads(resp.read().decode('utf-8')).get("d", {}).get("ordersHistory", [])
            meta_cache["history"] = history

        config = meta_cache["config"]
        hist_cols = [c["id"] for c in config.get("ordersHistoryConfig", {}).get("columns", [])]
        inst_map = meta_cache["inst_map"]
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
            "OVERALL": {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0, "win_val": 0.0, "loss_val": 0.0, "lots": 0.0},
            "NAS100": {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0, "win_val": 0.0, "loss_val": 0.0, "lots": 0.0},
            "EURUSD": {"total": 0, "wins": 0, "losses": 0, "pnl": 0.0, "win_val": 0.0, "loss_val": 0.0, "lots": 0.0}
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

            pnl = (exit_p - entry_p) * qty if side == "buy" else (entry_p - exit_p) * qty

            closed_trades.append({
                "positionId": p_id,
                "instrument": inst_name,
                "side": side,
                "qty": qty,
                "entryPrice": entry_p,
                "exitPrice": exit_p,
                "pnl": round(pnl, 2)
            })

            target_keys = ["OVERALL"]
            if "NAS" in inst_name.upper() or "US100" in inst_name.upper() or inst_id == "3884":
                target_keys.append("NAS100")
            elif "EURUSD" in inst_name.upper():
                target_keys.append("EURUSD")

            for k in target_keys:
                m = instrument_metrics[k]
                m["total"] += 1
                m["pnl"] += pnl
                m["lots"] += qty
                if pnl >= 0:
                    m["wins"] += 1
                    m["win_val"] += pnl
                else:
                    m["losses"] += 1
                    m["loss_val"] += abs(pnl)

        for k, m in instrument_metrics.items():
            total = m["total"]
            m["winRate"] = round((m["wins"] / total * 100), 1) if total > 0 else 0.0
            m["avgWin"] = round((m["win_val"] / m["wins"]), 2) if m["wins"] > 0 else 0.0
            m["avgLoss"] = round((m["loss_val"] / m["losses"]), 2) if m["losses"] > 0 else 0.0
            m["profitFactor"] = round((m["win_val"] / m["loss_val"]), 2) if m["loss_val"] > 0 else (round(m["win_val"], 2) if m["win_val"] > 0 else 0.0)
            m["pnl"] = round(m["pnl"], 2)
            m["lots"] = round(m["lots"], 2)

        meta_cache["closed_trades"] = closed_trades
        meta_cache["metrics"] = instrument_metrics
        meta_cache["last_fetch"] = time.time()
        print(f"[{time.strftime('%H:%M:%S')}] TradeLocker metadata refreshed.")
    except Exception as e:
        print("Metadata refresh exception:", e)

def get_default_stochastics():
    return {
        "timeframe": "5m",
        "stoch_fast": {"k": 35.0, "d": 35.0, "status": "NEUTRAL", "class": "neutral"},
        "stoch_heavy": {"k": 44.6, "d": 44.6, "status": "NEUTRAL", "class": "neutral"}
    }

def check_and_apply_auto_stoploss(open_positions, nas_open_pnl):
    """Automatically set Stop Loss to +$5.00 whenever PnL reaches +$10.00 (Victory Artwork)!"""
    if nas_open_pnl >= 10.0:
        for pos in open_positions:
            p_id = str(pos.get("id") or pos.get("positionId"))
            if p_id and p_id not in auto_sl_triggered:
                print(f"[{time.strftime('%H:%M:%S')}] [AUTO SL] PnL reached +${nas_open_pnl:.2f} (Victory Artwork)! Auto-triggering +$5.00 Stop Loss on position #{p_id}")
                auto_sl_triggered.add(p_id)
                set_position_stoploss(p_id, 5.0)

def get_tradelocker_data(retry_on_401=True):
    """Fetch live real-time account state, positions & Stochastics on EVERY request."""
    now = time.time()
    if live_cache["data"] and (now - live_cache["last_fetch"]) < 2.0:
        return live_cache["data"]

    env = session_config["environment"]
    base_url = f"https://{env}.tradelocker.com/backend-api"

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }

    try:
        token = session_config["token"]
        if not token or (now - session_config.get("token_time", 0)) > 300:
            token = get_jwt_token()

        acc_id = session_config["acc_id"] or "814241"
        acc_num = session_config["acc_num"] or "18"

        auth_headers = dict(headers)
        auth_headers["Authorization"] = f"Bearer {token}"
        auth_headers["accNum"] = str(acc_num)

        refresh_metadata(auth_headers, base_url, acc_id)

        config = meta_cache.get("config") or {}
        inst_map = meta_cache.get("inst_map") or {}

        # 1. Real-Time Account State
        req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/state", headers=auth_headers)
        with urllib.request.urlopen(req, context=ctx) as resp:
            state_data = json.loads(resp.read().decode('utf-8')).get("d", {}).get("accountDetailsData", [])

        # 2. Real-Time Positions
        req = urllib.request.Request(f"{base_url}/trade/accounts/{acc_id}/positions", headers=auth_headers)
        with urllib.request.urlopen(req, context=ctx) as resp:
            positions_data = json.loads(resp.read().decode('utf-8')).get("d", {}).get("positions", [])

        # 3. Real-Time Stochastics Calculation
        stochastics = fetch_live_stochastics(auth_headers, base_url)

        # Map Account State
        acc_cols = [c["id"] for c in config.get("accountDetailsConfig", {}).get("columns", [])]
        account_state = dict(zip(acc_cols, state_data)) if acc_cols and state_data else {}

        balance = float(account_state.get("balance") or (state_data[0] if len(state_data) > 0 else 500.00))
        open_net_pnl = float(account_state.get("openNetPnL") or (state_data[23] if len(state_data) > 23 else 0.0))
        equity = balance + open_net_pnl

        # Map Positions
        pos_cols = [c["id"] for c in config.get("positionsConfig", {}).get("columns", [])]
        open_positions = []
        open_pnl_by_inst = {"NAS100": 0.0, "EURUSD": 0.0, "OTHER": 0.0}

        for pos in positions_data:
            p_dict = dict(zip(pos_cols, pos)) if pos_cols else {"unrealizedPl": pos[9] if len(pos)>9 else 0.0}
            p_id = str(p_dict.get("id") or (pos[0] if len(pos)>0 else ""))
            inst_id = str(p_dict.get("tradableInstrumentId") or (pos[1] if len(pos)>1 else ""))
            inst_name = inst_map.get(inst_id, "NAS100" if inst_id=="3884" else f"Inst-{inst_id}")
            side = str(p_dict.get("side") or (pos[3] if len(pos)>3 else "buy"))
            qty = float(p_dict.get("qty") or (pos[4] if len(pos)>4 else 0.01))
            entry_price = float(p_dict.get("avgPrice") or (pos[5] if len(pos)>5 else 0.0))
            unrealized = float(p_dict.get("unrealizedPl") or (pos[9] if len(pos)>9 else 0.0))
            stop_loss = p_dict.get("stopLossId") or p_dict.get("stopLoss")
            take_profit = p_dict.get("takeProfitId") or p_dict.get("takeProfit")

            p_dict["id"] = p_id
            p_dict["instrumentName"] = inst_name
            p_dict["side"] = side
            p_dict["qty"] = qty
            p_dict["avgPrice"] = entry_price
            p_dict["unrealizedPl"] = unrealized
            p_dict["stopLoss"] = stop_loss
            p_dict["takeProfit"] = take_profit

            open_positions.append(p_dict)

            if "NAS" in inst_name.upper() or "US100" in inst_name.upper() or inst_id == "3884":
                open_pnl_by_inst["NAS100"] += unrealized
            elif "EURUSD" in inst_name.upper():
                open_pnl_by_inst["EURUSD"] += unrealized
            else:
                open_pnl_by_inst["OTHER"] += unrealized

        # AUTOMATIC +$5 STOP LOSS TRIGGER WHEN PNL REACHES +$10 (VICTORY ARTWORK)
        check_and_apply_auto_stoploss(open_positions, open_pnl_by_inst["NAS100"])

        metrics = meta_cache.get("metrics") or {
            "OVERALL": {"pnl": 0.0, "winRate": 0.0, "profitFactor": 0.0, "total": 0, "wins": 0, "losses": 0, "lots": 0.0},
            "NAS100": {"pnl": 0.0, "winRate": 0.0, "profitFactor": 0.0, "total": 0, "wins": 0, "losses": 0, "lots": 0.0}
        }

        result_data = {
            "account": {
                "accId": acc_id,
                "accNum": acc_num,
                "server": session_config["server"],
                "environment": env,
                "balance": round(balance, 2),
                "equity": round(equity, 2),
                "openPnL": round(open_net_pnl, 2),
                "positionsCount": len(open_positions),
                "serverTime": int(time.time())
            },
            "openPnLByInstrument": open_pnl_by_inst,
            "metrics": metrics,
            "stochastics": stochastics,
            "openPositions": open_positions,
            "closedTrades": meta_cache.get("closed_trades", [])[:60]
        }

        live_cache["data"] = result_data
        live_cache["last_fetch"] = time.time()
        return result_data

    except urllib.error.HTTPError as e:
        if e.code == 401 and retry_on_401:
            print("Token expired. Re-authenticating...")
            session_config["token"] = None
            return get_tradelocker_data(retry_on_401=False)
        print(f"HTTP Error {e.code} in get_tradelocker_data: {e}")
        return live_cache["data"] or get_mock_summary_data()
    except Exception as e:
        print(f"Exception in get_tradelocker_data: {e}")
        return live_cache["data"] or get_mock_summary_data()

def set_position_stoploss(position_id, loss_amount):
    """Calculate exact Stop Loss price level for Break Even, positive lock (+$5), or -$5 / -$10 loss."""
    data = get_tradelocker_data()
    positions = data.get("openPositions", [])

    if not positions:
        return {"status": "error", "message": "No open positions found"}

    target_positions = []
    if position_id and str(position_id).lower() != "all":
        for p in positions:
            if str(p.get("id")) == str(position_id) or str(p.get("positionId")) == str(position_id):
                target_positions.append(p)
                break
    
    if not target_positions:
        target_positions = positions

    try:
        val_amt = float(loss_amount)
    except (ValueError, TypeError):
        val_amt = 0.0

    env = session_config["environment"]
    base_url = f"https://{env}.tradelocker.com/backend-api"

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }

    token = session_config["token"]
    if not token:
        token = get_jwt_token()

    acc_num = session_config["acc_num"] or "18"

    auth_headers = dict(headers)
    auth_headers["Authorization"] = f"Bearer {token}"
    auth_headers["accNum"] = str(acc_num)

    updated_count = 0
    sl_price_last = 0.0

    for target_pos in target_positions:
        p_id = target_pos.get("id") or target_pos.get("positionId")
        side = str(target_pos.get("side", "buy")).lower()
        qty = float(target_pos.get("qty") or 0.01)
        entry_p = float(target_pos.get("avgPrice") or 0.0)

        if entry_p <= 0 or qty <= 0:
            continue

        if val_amt == 0.0 or str(loss_amount).lower() == "be":
            sl_price = round(entry_p, 2)
            label = "Break Even"
        elif val_amt > 0:
            # Positive +$5 Stop Loss / Profit Lock
            if side == "buy":
                sl_price = round(entry_p + (val_amt / qty), 2)
            else:
                sl_price = round(entry_p - (val_amt / qty), 2)
            label = f"+${val_amt:.2f}"
        else:
            # Negative -$5 / -$10 Stop Loss
            abs_val = abs(val_amt)
            if side == "buy":
                sl_price = round(entry_p - (abs_val / qty), 2)
            else:
                sl_price = round(entry_p + (abs_val / qty), 2)
            label = f"-${abs_val:.2f}"

        sl_price_last = sl_price
        patch_body = json.dumps({"stopLoss": sl_price}).encode('utf-8')
        url = f"{base_url}/trade/positions/{p_id}"

        try:
            req = urllib.request.Request(url, data=patch_body, headers=auth_headers, method="PATCH")
            with urllib.request.urlopen(req, context=ctx) as resp:
                updated_count += 1
                print(f"Set StopLoss=${sl_price} ({label}) on Position #{p_id} successfully!")
        except Exception as e:
            print(f"Error setting stop loss on position {p_id}: {e}")

    live_cache["data"] = None
    live_cache["last_fetch"] = 0

    if updated_count > 0:
        return {
            "status": "ok",
            "updatedCount": updated_count,
            "stopLoss": sl_price_last,
            "message": f"Set {label} Stop Loss on {updated_count} position(s)!"
        }
    else:
        return {"status": "error", "message": "Failed to set Stop Loss on positions"}

def set_position_takeprofit(position_id, profit_amount):
    """Calculate exact price level for Max Power TP (+$10, +$15, +$20) and execute PATCH /trade/positions/{positionId}."""
    data = get_tradelocker_data()
    positions = data.get("openPositions", [])

    if not positions:
        return {"status": "error", "message": "No open positions found"}

    target_positions = []
    if position_id and str(position_id).lower() != "all":
        for p in positions:
            if str(p.get("id")) == str(position_id) or str(p.get("positionId")) == str(position_id):
                target_positions.append(p)
                break

    if not target_positions:
        target_positions = positions

    profit_amt = float(profit_amount)

    env = session_config["environment"]
    base_url = f"https://{env}.tradelocker.com/backend-api"

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }

    token = session_config["token"]
    if not token:
        token = get_jwt_token()

    acc_num = session_config["acc_num"] or "18"

    auth_headers = dict(headers)
    auth_headers["Authorization"] = f"Bearer {token}"
    auth_headers["accNum"] = str(acc_num)

    updated_count = 0
    tp_price_last = 0.0

    for target_pos in target_positions:
        p_id = target_pos.get("id") or target_pos.get("positionId")
        side = str(target_pos.get("side", "buy")).lower()
        qty = float(target_pos.get("qty") or 0.01)
        entry_p = float(target_pos.get("avgPrice") or 0.0)

        if entry_p <= 0 or qty <= 0:
            continue

        if side == "buy":
            tp_price = round(entry_p + (profit_amt / qty), 2)
        else:
            tp_price = round(entry_p - (profit_amt / qty), 2)

        tp_price_last = tp_price
        patch_body = json.dumps({"takeProfit": tp_price}).encode('utf-8')
        url = f"{base_url}/trade/positions/{p_id}"

        try:
            req = urllib.request.Request(url, data=patch_body, headers=auth_headers, method="PATCH")
            with urllib.request.urlopen(req, context=ctx) as resp:
                updated_count += 1
                print(f"Set TakeProfit=${tp_price} (+${profit_amt:.2f}) on Position #{p_id} successfully!")
        except Exception as e:
            print(f"Error setting take profit on position {p_id}: {e}")

    live_cache["data"] = None
    live_cache["last_fetch"] = 0

    if updated_count > 0:
        return {
            "status": "ok",
            "updatedCount": updated_count,
            "takeProfit": tp_price_last,
            "message": f"Set Max Power +${profit_amt:.2f} Take Profit on {updated_count} position(s)!"
        }
    else:
        return {"status": "error", "message": "Failed to set Take Profit on positions"}

def close_nas100_positions():
    """Execute TradeLocker REST API call to market close all NAS100 positions."""
    data = get_tradelocker_data()
    open_positions = data.get("openPositions", [])

    nas_positions = [
        p for p in open_positions
        if "NAS" in (p.get("instrumentName") or "").upper()
        or "US100" in (p.get("instrumentName") or "").upper()
        or str(p.get("tradableInstrumentId")) == "3884"
    ]

    env = session_config["environment"]
    base_url = f"https://{env}.tradelocker.com/backend-api"

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }

    token = session_config["token"]
    if not token:
        token = get_jwt_token()

    acc_id = session_config["acc_id"] or "814241"
    acc_num = session_config["acc_num"] or "18"

    auth_headers = dict(headers)
    auth_headers["Authorization"] = f"Bearer {token}"
    auth_headers["accNum"] = str(acc_num)

    closed_count = 0
    close_all_url = f"{base_url}/trade/accounts/{acc_id}/positions?tradableInstrumentId=3884"
    req = urllib.request.Request(close_all_url, headers=auth_headers, method="DELETE")
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            closed_count += len(nas_positions)
    except Exception as e:
        print("closeAll endpoint exception:", e)

    for pos in nas_positions:
        pos_id = pos.get("id") or pos.get("positionId")
        if not pos_id:
            continue
        url = f"{base_url}/trade/positions/{pos_id}"
        close_body = json.dumps({"qty": 0}).encode('utf-8')
        req = urllib.request.Request(url, data=close_body, headers=auth_headers, method="DELETE")
        try:
            with urllib.request.urlopen(req, context=ctx) as resp:
                closed_count += 1
        except Exception as e:
            print(f"Error closing position {pos_id}: {e}")

    live_cache["data"] = None
    live_cache["last_fetch"] = 0

    return {
        "status": "ok",
        "closedCount": closed_count,
        "message": f"Closed {len(nas_positions)} NAS100 market positions successfully!"
    }

def get_mock_summary_data():
    return {
        "account": {
            "accId": "814241",
            "accNum": 18,
            "server": "HEROFX",
            "environment": "live",
            "balance": 500.00,
            "equity": 500.00,
            "openPnL": 0.00,
            "positionsCount": 0,
            "serverTime": int(time.time())
        },
        "openPnLByInstrument": {
            "NAS100": 0.00,
            "EURUSD": 0.00,
            "OTHER": 0.00
        },
        "metrics": {
            "OVERALL": { "total": 0, "wins": 0, "losses": 0, "pnl": 0.0, "winRate": 0.0, "avgWin": 0.0, "avgLoss": 0.0, "profitFactor": 0.0, "lots": 0.0 },
            "NAS100": { "total": 0, "wins": 0, "losses": 0, "pnl": 0.0, "winRate": 0.0, "avgWin": 0.0, "avgLoss": 0.0, "profitFactor": 0.0, "lots": 0.0 }
        },
        "stochastics": get_default_stochastics(),
        "openPositions": [],
        "closedTrades": []
    }

class TradeLockerHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/summary'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()

            if session_config["live_mode"]:
                data = get_tradelocker_data()
            else:
                data = get_mock_summary_data()

            self.wfile.write(json.dumps(data).encode('utf-8'))
            return

        clean_path = self.path.split('?')[0]
        if clean_path == '/':
            clean_path = '/index.html'

        file_path = os.path.join(PUBLIC_DIR, clean_path.lstrip('/'))
        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.send_response(200)
            mime_type, _ = mimetypes.guess_type(file_path)
            self.send_header('Content-Type', mime_type or 'text/html')
            self.end_headers()
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(content_len) if content_len > 0 else b'{}'
        payload = json.loads(body_bytes.decode('utf-8')) if body_bytes else {}

        if self.path == '/api/set-takeprofit':
            pos_id = payload.get("positionId")
            amount = payload.get("amount", 10.0)
            res = set_position_takeprofit(pos_id, amount)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif self.path == '/api/set-stoploss':
            pos_id = payload.get("positionId")
            amount = payload.get("amount", 0.0)
            res = set_position_stoploss(pos_id, amount)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif self.path == '/api/close-all-nas100':
            res = close_nas100_positions()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))

        elif self.path == '/api/login':
            session_config["environment"] = payload.get("environment", "live")
            session_config["server"] = payload.get("server", "HEROFX")
            session_config["email"] = payload.get("email")
            session_config["password"] = payload.get("password")
            if payload.get("targetAccId"):
                session_config["target_acc_id"] = str(payload.get("targetAccId"))
            session_config["token"] = None
            meta_cache["last_fetch"] = 0
            live_cache["data"] = None

            data = get_tradelocker_data()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            if "account" in data:
                self.wfile.write(json.dumps({"status": "ok", "account": data["account"]}).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"status": "error", "message": "Failed to connect to TradeLocker"}).encode('utf-8'))

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), TradeLockerHTTPRequestHandler) as httpd:
        print(f"TradeLocker Portfolio Tracker Server running at http://localhost:{PORT}")
        httpd.serve_forever()
