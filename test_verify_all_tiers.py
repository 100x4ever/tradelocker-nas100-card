import math

def get_target_sl(effective_pnl):
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

    for pnl_thresh, sl_amt in SL_LADDER:
        if effective_pnl >= pnl_thresh:
            return sl_amt

    # Dynamic trailing above 55 PnL
    if effective_pnl > 55.0:
        return round(effective_pnl - 5.0, 1)

    return None

test_values = [0.0, 5.0, 10.0, 15.0, 20.0, 24.5, 25.0, 29.9, 30.0, 35.0, 40.0, 44.5, 46.0, 50.0, 55.0, 60.0, 75.0]

for pnl in test_values:
    sl = get_target_sl(pnl)
    print(f"PnL: +${pnl:5.1f} -> Target SL: {('+$' + str(sl)) if sl else 'Initial -$10'}")
