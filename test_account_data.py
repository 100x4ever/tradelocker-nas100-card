import server
import json

server.session_config["live_mode"] = True
data = server.get_tradelocker_data()
print("Account Info:", json.dumps(data.get("account"), indent=2))
print("Open PnL by Instrument:", json.dumps(data.get("openPnLByInstrument"), indent=2))
print("Metrics:", json.dumps(data.get("metrics"), indent=2))
print("Open Positions:", json.dumps(data.get("openPositions"), indent=2))
