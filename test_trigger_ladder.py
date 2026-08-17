import server

print("Testing live check_and_apply_auto_stoploss execution on active position...")
server.session_config["live_mode"] = True
data = server.get_tradelocker_data()
print("Account Equity:", data["account"]["equity"])
print("NAS100 PnL:", data["openPnLByInstrument"]["NAS100"])
print("Open Positions:", data["openPositions"])
