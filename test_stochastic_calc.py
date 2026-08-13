import urllib.request
import json
import ssl
import time

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
auth_headers["accNum"] = "17"

now_ms = int(time.time() * 1000)
from_ms = now_ms - (300 * 5 * 60 * 1000)

url = f"{base_url}/trade/history?tradableInstrumentId=3884&routeId=509043&resolution=5m&from={from_ms}&to={now_ms}"
req = urllib.request.Request(url, headers=auth_headers)
with urllib.request.urlopen(req, context=ctx) as resp:
    bars = json.loads(resp.read().decode('utf-8')).get("d", {}).get("barDetails", [])

print(f"Loaded {len(bars)} 5m bars.")

def calculate_stochastic(bars, k_period, k_slowing, d_smoothing):
    if len(bars) < k_period:
        return {"k": 50.0, "d": 50.0}

    # 1. Raw %K series
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

    # 2. Smooth %K series (Slowing)
    smoothed_k_list = []
    for i in range(len(raw_k_list)):
        if i < k_slowing - 1:
            smoothed_k_list.append(raw_k_list[i])
            continue
        sub = raw_k_list[i - k_slowing + 1 : i + 1]
        smoothed_k_list.append(sum(sub) / k_slowing)

    # 3. %D series (Smoothing of smoothed %K)
    d_list = []
    for i in range(len(smoothed_k_list)):
        if i < d_smoothing - 1:
            d_list.append(smoothed_k_list[i])
            continue
        sub = smoothed_k_list[i - d_smoothing + 1 : i + 1]
        d_list.append(sum(sub) / d_smoothing)

    return {
        "k": round(smoothed_k_list[-1], 1),
        "d": round(d_list[-1], 1)
    }

stoch_7_3_3 = calculate_stochastic(bars, 7, 3, 3)
stoch_40_1_4 = calculate_stochastic(bars, 40, 1, 4)

print("\n--- Live 5m NAS100 Stochastic Indicators ---")
print(f"Stoch (7,3,3)  -> %K: {stoch_7_3_3['k']}, %D: {stoch_7_3_3['d']}")
print(f"Stoch (40,1,4) -> %K: {stoch_40_1_4['k']}, %D: {stoch_40_1_4['d']}")

def get_stoch_state(val):
    if val >= 90.0:
        return "EXTREME OB", "extreme-ob"
    elif val >= 80.0:
        return "OB", "ob"
    elif val <= 10.0:
        return "EXTREME OS", "extreme-os"
    elif val <= 20.0:
        return "OS", "os"
    else:
        return "NEUTRAL", "neutral"

state_7 = get_stoch_state(stoch_7_3_3['d'])
state_40 = get_stoch_state(stoch_40_1_4['d'])

print(f"Stoch (7,3,3)  %D = {stoch_7_3_3['d']}  [{state_7[0]}]")
print(f"Stoch (40,1,4) %D = {stoch_40_1_4['d']} [{state_40[0]}]")
