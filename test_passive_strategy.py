import urllib.request
import urllib.error
import json
import ssl
import time
import math

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
auth_headers["accNum"] = "18"

# Fetch 5m bars
now_ms = int(time.time() * 1000)
from_ms = now_ms - (300 * 5 * 60 * 1000)
history_url = f"{base_url}/trade/history?tradableInstrumentId=3884&routeId=509043&resolution=5m&from={from_ms}&to={now_ms}"
req_h = urllib.request.Request(history_url, headers=auth_headers)
with urllib.request.urlopen(req_h, context=ctx) as r_h:
    bars = json.loads(r_h.read().decode('utf-8')).get("d", {}).get("barDetails", [])

def calc_wma(data, period):
    if len(data) < period:
        return data[-1] if data else 0.0
    sub = data[-period:]
    weights = list(range(1, period + 1))
    return sum(s * w for s, w in zip(sub, weights)) / sum(weights)

def calc_hma(bars, period=49):
    closes = [b["c"] for b in bars]
    if len(closes) < period:
        return closes[-1] if closes else 0.0
    half_p = int(period / 2)
    sqrt_p = int(math.sqrt(period))

    diff_series = []
    for i in range(len(closes)):
        if i < period - 1:
            diff_series.append(0.0)
            continue
        sub_closes = closes[:i+1]
        wma_half = calc_wma(sub_closes, half_p)
        wma_full = calc_wma(sub_closes, period)
        diff_series.append(2.0 * wma_half - wma_full)

    return calc_wma(diff_series, sqrt_p)

def calc_supertrend(bars, period=6, multiplier=1.0):
    if len(bars) < period + 1:
        return bars[-1]["c"], bars[-1]["c"]
    
    # Calculate ATR
    trs = []
    for i in range(1, len(bars)):
        h, l, prev_c = bars[i]["h"], bars[i]["l"], bars[i-1]["c"]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)
    
    atr = sum(trs[-period:]) / period
    curr_b = bars[-1]
    hl2 = (curr_b["h"] + curr_b["l"]) / 2.0
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr
    return lower, upper

hma49 = calc_hma(bars, 49)
st1_lower, st1_upper = calc_supertrend(bars, 6, 1.0)
st2_lower, st2_upper = calc_supertrend(bars, 12, 2.0)

print(f"HMA 49: {hma49:.2f}")
print(f"Supertrend (6,1.0): Lower={st1_lower:.2f}, Upper={st1_upper:.2f}")
print(f"Supertrend (12,2.0): Lower={st2_lower:.2f}, Upper={st2_upper:.2f}")

# Check candlestick pattern triggers on latest bars
b0 = bars[-1]
b1 = bars[-2]
b2 = bars[-3]

is_bull_engulf = (b1["c"] < b1["o"]) and (b0["c"] > b0["o"]) and (b0["c"] >= b1["o"]) and (b0["o"] <= b1["c"])
is_bear_engulf = (b1["c"] > b1["o"]) and (b0["c"] < b0["o"]) and (b0["c"] <= b1["o"]) and (b0["o"] >= b1["c"])

is_tweezer_bottom = (b1["c"] < b1["o"]) and (b0["c"] > b0["o"]) and (abs(b0["l"] - b1["l"]) <= 3.0)
is_tweezer_top = (b1["c"] > b1["o"]) and (b0["c"] < b0["o"]) and (abs(b0["h"] - b1["h"]) <= 3.0)

print(f"Bullish Engulfing: {is_bull_engulf}, Bearish Engulfing: {is_bear_engulf}")
print(f"Tweezer Bottom: {is_tweezer_bottom}, Tweezer Top: {is_tweezer_top}")
