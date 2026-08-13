import server
import json

print("Calling server.get_tradelocker_data()...")
data = server.get_tradelocker_data()
print("Account Data:", json.dumps(data["account"], indent=2))
print("Open PnL by instrument:", data["openPnLByInstrument"])
print("Metrics NAS100:", data["metrics"]["NAS100"])
