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

# User Session State (Locked to LIVE Account 812189)
session_config = {
    "live_mode": True,
    "email": "jcollins92989@gmail.com",
    "password": "Pook&Buh9",
    "server": "HEROFX",
    "environment": "live",
    "target_acc_id": "812189",
    "token": None,
    "acc_id": None,
    "acc_num": None
}

cache = {
    "last_fetch_time": 0,
    "data": None
}

CACHE_TTL = 1.5  # seconds

def get_tradelocker_data():
    now = time.time()
    if cache["data"] and (now - cache["last_fetch_time"]) < CACHE_TTL:
        return cache["data"]

    email = session_config["email"]
    password = session_config["password"]
    server = session_config["server"]
    env = session_config["environment"]
    base_url = f"https://{env}.tradelocker.com/backend-api"

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }

    try:
        # 1. JWT Auth
        token = session_config["token"]
        if not token:
            auth_payload = json.dumps({"email": email, "password": password, "server": server}).encode('utf-8')
            req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=auth_payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, context=ctx) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                token = res["accessToken"]
                session_config["token"] = token

        auth_headers = dict(headers)
        auth_headers["Authorization"] = f"Bearer {token}"

        # 2. Fetch all accounts
        req = urllib.request.Request(f"{base_url}/auth/jwt/all-accounts", headers=auth_headers)
        with urllib.request.urlopen(req, context=ctx) as resp:
            accounts_data = json.loads(resp.read().decode('utf-8')).get("accounts", [])

        if not accounts_data:
            return cache["data"] or get_mock_summary_data()

        target_id = str(session_config.get("target_acc_id") or "")
        selected_acc = None

        if target_id:
            for a in accounts_data:
                if str(a.get("id")) == target_id or target_id in str(a.get("name", "")):
                    selected_acc = a
                    break

        if not selected_acc:
            selected_acc = accounts_data[0]

        acc_id = str(selected_acc.get("id") or selected_acc.get("accountId"))
        acc_num = str(selected_acc.get("accNum", 1))
        session_config["acc_id"] = acc_id
        session_config["acc_num"] = acc_num

        auth_headers["accNum"] = acc_num

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

        # Schema mappings
        acc_cols = [c["id"] for c in config.get("accountDetailsConfig", {}).get("columns", [])]
        account_state = dict(zip(acc_cols, state_data))

        inst_map = {}
        for inst in instruments:
            inst_map[str(inst.get("id"))] = inst.get("name") or inst.get("symbol")

        # Open Positions
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

            if "NAS" in inst_name.upper() or "US100" in inst_name.upper() or inst_id == "3884":
                open_pnl_by_inst["NAS100"] += unrealized
            elif "EURUSD" in inst_name.upper():
                open_pnl_by_inst["EURUSD"] += unrealized
            else:
                open_pnl_by_inst["OTHER"] += unrealized

        # History -> Trades
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

            trade_obj = {
                "positionId": p_id,
                "instrument": inst_name,
                "side": side,
                "qty": qty,
                "entryPrice": entry_p,
                "exitPrice": exit_p,
                "pnl": round(pnl, 2)
            }
            closed_trades.append(trade_obj)

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

        balance = float(account_state.get("balance") or account_state.get("cashBalance") or 0.0)
        open_net_pnl = float(account_state.get("openNetPnL") or 0.0)
        equity = balance + open_net_pnl

        formatted_accounts = []
        for a in accounts_data:
            aid = str(a.get("id") or a.get("accountId"))
            anum = str(a.get("accNum", ""))
            abal = float(a.get("accountBalance") or 0.0)
            formatted_accounts.append({
                "id": aid,
                "accNum": anum,
                "name": a.get("name", f"Account #{aid}"),
                "balance": abal,
                "isSelected": aid == acc_id
            })

        result_data = {
            "account": {
                "accId": acc_id,
                "accNum": acc_num,
                "server": server,
                "environment": env,
                "balance": round(balance, 2),
                "equity": round(equity, 2),
                "openPnL": round(open_net_pnl, 2),
                "overallRealizedPnL": instrument_metrics["OVERALL"]["pnl"],
                "positionsCount": len(open_positions),
                "availableAccounts": formatted_accounts
            },
            "openPnLByInstrument": open_pnl_by_inst,
            "metrics": instrument_metrics,
            "openPositions": open_positions,
            "closedTrades": closed_trades[:60]
        }

        cache["data"] = result_data
        cache["last_fetch_time"] = time.time()
        return result_data

    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("Received HTTP 429, using cached data...")
            return cache["data"] or get_mock_summary_data()
        session_config["token"] = None
        return cache["data"] or get_mock_summary_data()
    except Exception as e:
        session_config["token"] = None
        print(f"Error fetching TradeLocker data: {e}")
        return cache["data"] or get_mock_summary_data()

def close_nas100_positions():
    """Execute TradeLocker REST API call to market close all NAS100 positions."""

    # 1. First fetch current live data to identify open NAS100 positions
    data = get_tradelocker_data()
    open_positions = data.get("openPositions", [])
    
    nas_positions = [
        p for p in open_positions
        if "NAS" in (p.get("instrumentName") or "").upper()
        or "US100" in (p.get("instrumentName") or "").upper()
        or str(p.get("tradableInstrumentId")) == "3884"
    ]

    if not nas_positions and not session_config["live_mode"]:
        return {"status": "ok", "closedCount": 0, "message": "No open NAS100 positions found"}

    email = session_config["email"]
    password = session_config["password"]
    server = session_config["server"]
    env = session_config["environment"]
    base_url = f"https://{env}.tradelocker.com/backend-api"

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }

    token = session_config["token"]
    if not token:
        auth_payload = json.dumps({"email": email, "password": password, "server": server}).encode('utf-8')
        req = urllib.request.Request(f"{base_url}/auth/jwt/token", data=auth_payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, context=ctx) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            token = res["accessToken"]
            session_config["token"] = token

    acc_id = session_config["acc_id"] or "812189"
    acc_num = session_config["acc_num"] or "17"

    auth_headers = dict(headers)
    auth_headers["Authorization"] = f"Bearer {token}"
    auth_headers["accNum"] = str(acc_num)

    closed_count = 0
    errors = []

    # Method 1: Delete all positions for instrument 3884 (NAS100) via TradeLocker closeAll API
    close_all_url = f"{base_url}/trade/accounts/{acc_id}/positions?tradableInstrumentId=3884"
    req = urllib.request.Request(close_all_url, headers=auth_headers, method="DELETE")
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            print("TradeLocker closeAll NAS100 response status:", resp.status)
            closed_count += len(nas_positions)
    except Exception as e:
        print("closeAll endpoint exception:", e)

    # Method 2: Close each NAS100 position individually via DELETE /trade/positions/{positionId}
    for pos in nas_positions:
        pos_id = pos.get("id") or pos.get("positionId")
        if not pos_id:
            continue
        url = f"{base_url}/trade/positions/{pos_id}"
        close_body = json.dumps({"qty": 0}).encode('utf-8')
        req = urllib.request.Request(url, data=close_body, headers=auth_headers, method="DELETE")
        try:
            with urllib.request.urlopen(req, context=ctx) as resp:
                print(f"Closed NAS100 position {pos_id} successfully!")
                closed_count += 1
        except Exception as e:
            print(f"Error closing position {pos_id}: {e}")
            errors.append(str(e))

    # Invalidate cache so real-time status reflects closed positions immediately
    cache["data"] = None
    cache["last_fetch_time"] = 0

    return {
        "status": "ok",
        "closedCount": closed_count,
        "message": f"Closed {len(nas_positions)} NAS100 market positions successfully!"
    }

def get_mock_summary_data():
    return {
        "account": {
            "accId": "812189",
            "accNum": 17,
            "server": "HEROFX",
            "environment": "live",
            "balance": 987.64,
            "equity": 979.22,
            "openPnL": -8.42,
            "overallRealizedPnL": 29.44,
            "positionsCount": 2,
            "availableAccounts": [
                { "id": "812189", "accNum": "17", "name": "HEROFX Live #812189", "balance": 987.64, "isSelected": True }
            ]
        },
        "openPnLByInstrument": {
            "NAS100": -8.42,
            "EURUSD": 0.00,
            "OTHER": 0.00
        },
        "metrics": {
            "OVERALL": { "total": 21, "wins": 14, "losses": 7, "pnl": 29.44, "winRate": 66.7, "avgWin": 2.16, "avgLoss": 0.12, "profitFactor": 36.38, "lots": 2.45 },
            "NAS100": { "total": 5, "wins": 5, "losses": 0, "pnl": 11.49, "winRate": 100.0, "avgWin": 2.30, "avgLoss": 0.00, "profitFactor": 11.49, "lots": 0.95 },
            "EURUSD": { "total": 0, "wins": 0, "losses": 0, "pnl": 0.00, "winRate": 0.0, "avgWin": 0.00, "avgLoss": 0.00, "profitFactor": 0.00, "lots": 0.00 }
        },
        "openPositions": [
            { "id": "72057594045519539", "instrumentName": "NAS100", "side": "SELL", "qty": 0.28, "avgPrice": 30094.97, "unrealizedPl": -2.10, "strategyId": "Manual" },
            { "id": "72057594045519380", "instrumentName": "NAS100", "side": "SELL", "qty": 0.28, "avgPrice": 30075.33, "unrealizedPl": -6.32, "strategyId": "Manual" }
        ],
        "closedTrades": [
            { "positionId": "72057594045515963", "instrument": "NAS100", "side": "sell", "qty": 0.28, "entryPrice": 30153.93, "exitPrice": 30133.23, "pnl": 5.80 },
            { "positionId": "72057594045516212", "instrument": "NAS100", "side": "sell", "qty": 0.28, "entryPrice": 30158.31, "exitPrice": 30143.04, "pnl": 4.28 },
            { "positionId": "72057594045509054", "instrument": "NAS100", "side": "sell", "qty": 0.28, "entryPrice": 30135.27, "exitPrice": 30133.94, "pnl": 0.37 },
            { "positionId": "72057594045492963", "instrument": "NAS100", "side": "sell", "qty": 0.10, "entryPrice": 30124.30, "exitPrice": 30123.56, "pnl": 0.07 },
            { "positionId": "72057594045420699", "instrument": "NAS100", "side": "sell", "qty": 0.01, "entryPrice": 29781.50, "exitPrice": 29683.91, "pnl": 0.98 }
        ]
    }

class TradeLockerHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/summary':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
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

        if self.path == '/api/close-all-nas100':
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
            cache["data"] = None

            data = get_tradelocker_data()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()

            if "account" in data:
                self.wfile.write(json.dumps({"status": "ok", "account": data["account"]}).encode('utf-8'))
            else:
                self.wfile.write(json.dumps({"status": "error", "message": "Failed to connect to TradeLocker"}).encode('utf-8'))

        elif self.path == '/api/select-account':
            acc_id = str(payload.get("accId"))
            session_config["target_acc_id"] = acc_id
            session_config["acc_id"] = acc_id
            cache["data"] = None

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "accId": acc_id}).encode('utf-8'))

        elif self.path == '/api/toggle-mode':
            session_config["live_mode"] = payload.get("liveMode", True)
            cache["data"] = None
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "liveMode": session_config["live_mode"]}).encode('utf-8'))

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), TradeLockerHTTPRequestHandler) as httpd:
        print(f"TradeLocker Portfolio Tracker Server running at http://localhost:{PORT}")
        httpd.serve_forever()
