import server

print("Testing SL Ladder progression logic:")
SL_LADDER = [
    (55.0, 50.0),
    (50.0, 45.0),
    (45.0, 40.0),
    (40.0, 35.0),
    (35.0, 30.0),
    (30.0, 25.0),
    (25.0, 20.0),
    (20.0, 15.0),
    (10.0, 5.0)
]

test_pnls = [0.0, 10.5, 18.0, 22.0, 26.5, 31.0, 38.0, 42.0, 47.0, 52.0, 58.0]

for pnl in test_pnls:
    target = None
    for pnl_thresh, sl_amt in SL_LADDER:
        if pnl >= pnl_thresh:
            target = sl_amt
            break
    print(f"PnL: +${pnl:5.2f} -> Protective SL Level: {('+$' + str(target) + '.00') if target else 'Initial -$10.00'}")
