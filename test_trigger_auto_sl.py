import server

print("Triggering get_tradelocker_data() to verify auto SL execution on active position...")
server.session_config["live_mode"] = True
data = server.get_tradelocker_data()
print("Account Equity:", data["account"]["equity"])
print("NAS100 PnL:", data["openPnLByInstrument"]["NAS100"])
print("Open Positions:", data["openPositions"])
