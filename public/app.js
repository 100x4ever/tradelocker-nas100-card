let liveSummaryData = null;
let lastRefreshTimestamp = Date.now();
const autoSlNotified = new Set();
let isStalkingActive = false;

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    fetchPortfolioSummary();

    // Auto refresh every 4 seconds for reliable PnL, Equity & Stochastics updates
    setInterval(fetchPortfolioSummary, 4000);
});

function initEventListeners() {
    // NOW Button: Instant Market Close ALL open positions
    const btnCloseNow = document.getElementById('btnCloseNow');
    if (btnCloseNow) {
        btnCloseNow.addEventListener('click', async () => {
            const confirmed = confirm("Unrealized Strike NOW: Market Close ALL active open positions immediately?");
            if (!confirmed) return;

            btnCloseNow.disabled = true;
            btnCloseNow.innerText = "CLOSING...";

            try {
                const res = await fetch('/api/close-all-nas100', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();

                alert(data.message || "All positions market closed NOW!");
                fetchPortfolioSummary();
            } catch (err) {
                alert("Market close error: " + err.message);
            } finally {
                btnCloseNow.disabled = false;
                btnCloseNow.innerText = "⚡ NOW";
            }
        });
    }

    // Defensive Move: Set Break Even (BE), Positive Lock (+$5), -$5 and -$10 Stop Loss
    const btnSlBe = document.getElementById('btnSlBe');
    const btnSlP5 = document.getElementById('btnSlP5');
    const btnSl5 = document.getElementById('btnSl5');
    const btnSl10 = document.getElementById('btnSl10');
    const btnStalk = document.getElementById('btnStalk');

    // Max Power Move: Set +$10, +$15, +$20 Take Profit
    const btnTp10 = document.getElementById('btnTp10');
    const btnTp15 = document.getElementById('btnTp15');
    const btnTp20 = document.getElementById('btnTp20');

    // STALK Button: Toggle & Activate Trailing Stop Loss on active positions
    if (btnStalk) {
        btnStalk.addEventListener('click', async () => {
            const nextState = !isStalkingActive;
            const confirmed = confirm(`Defensive Shield: ${nextState ? 'Activate STALK Mode (Convert Stop Loss to Trailing Stop)' : 'Deactivate STALK Mode'} on ALL open positions?`);
            if (!confirmed) return;

            btnStalk.disabled = true;
            try {
                const res = await fetch('/api/set-trailing-stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ positionId: "all", trailingOffset: 10.0 })
                });
                const data = await res.json();

                if (data.status === 'ok') {
                    isStalkingActive = nextState;
                    btnStalk.classList.toggle('active-sl-glow', isStalkingActive);
                    btnStalk.innerText = isStalkingActive ? "🐾 STALKING" : "🐾 STALK";
                    alert(data.message || "STALK Trailing Stop mode activated!");
                    fetchPortfolioSummary();
                } else {
                    alert("Failed to activate STALK: " + (data.message || "Could not set trailing stop"));
                }
            } catch (err) {
                alert("Error setting trailing stop: " + err.message);
            } finally {
                btnStalk.disabled = false;
            }
        });
    }

    const executeStopLoss = async (amount) => {
        let label = "";
        if (amount === 0) label = "Break Even (Exact Entry Price)";
        else if (amount > 0) label = `+$${amount}.00 Profit Lock`;
        else label = `-$${Math.abs(amount)}.00 Loss Cap`;

        const confirmed = confirm(`Apply Defensive Shield: Set ${label} Stop Loss on ALL active open positions?`);
        if (!confirmed) return;

        if (btnSlBe) btnSlBe.disabled = true;
        if (btnSlP5) btnSlP5.disabled = true;
        if (btnSl5) btnSl5.disabled = true;
        if (btnSl10) btnSl10.disabled = true;

        try {
            const res = await fetch('/api/set-stoploss', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ positionId: "all", amount: amount })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                alert(data.message);
                fetchPortfolioSummary();
            } else {
                alert("Failed: " + (data.message || "Could not set Stop Loss"));
            }
        } catch (err) {
            alert("Error setting Stop Loss: " + err.message);
        } finally {
            if (btnSlBe) btnSlBe.disabled = false;
            if (btnSlP5) btnSlP5.disabled = false;
            if (btnSl5) btnSl5.disabled = false;
            if (btnSl10) btnSl10.disabled = false;
        }
    };

    const executeTakeProfit = async (amount) => {
        const confirmed = confirm(`Unrealized Strike: Set +$${amount}.00 Take Profit on ALL active open positions?`);
        if (!confirmed) return;

        if (btnTp10) btnTp10.disabled = true;
        if (btnTp15) btnTp15.disabled = true;
        if (btnTp20) btnTp20.disabled = true;

        try {
            const res = await fetch('/api/set-takeprofit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ positionId: "all", amount: amount })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                alert(data.message);
                fetchPortfolioSummary();
            } else {
                alert("Failed: " + (data.message || "Could not set Take Profit"));
            }
        } catch (err) {
            alert("Error setting Take Profit: " + err.message);
        } finally {
            if (btnTp10) btnTp10.disabled = false;
            if (btnTp15) btnTp15.disabled = false;
            if (btnTp20) btnTp20.disabled = false;
        }
    };

    if (btnSlBe) btnSlBe.addEventListener('click', () => executeStopLoss(0.0));
    if (btnSlP5) btnSlP5.addEventListener('click', () => executeStopLoss(5.0)); // Positive +$5 Profit Lock!
    if (btnSl5) btnSl5.addEventListener('click', () => executeStopLoss(-5.0));  // Negative -$5 Loss Cap
    if (btnSl10) btnSl10.addEventListener('click', () => executeStopLoss(-10.0)); // Negative -$10 Loss Cap

    if (btnTp10) btnTp10.addEventListener('click', () => executeTakeProfit(10.0));
    if (btnTp15) btnTp15.addEventListener('click', () => executeTakeProfit(15.0));
    if (btnTp20) btnTp20.addEventListener('click', () => executeTakeProfit(20.0));
}

async function fetchPortfolioSummary() {
    try {
        const res = await fetch(`/api/summary?t=${Date.now()}`, {
            headers: { 'Cache-Control': 'no-cache' }
        });
        const data = await res.json();
        liveSummaryData = data;
        lastRefreshTimestamp = Date.now();
        renderData();
    } catch (err) {
        console.error('Failed to fetch summary:', err);
    }
}

function renderData() {
    if (!liveSummaryData) return;

    const { account, openPnLByInstrument, metrics, stochastics, openPositions } = liveSummaryData;

    const nasMetric = metrics['NAS100'] || { pnl: 0, total: 0, wins: 0, losses: 0, winRate: 0, profitFactor: 0, lots: 0 };
    const overallMetric = metrics['OVERALL'] || { pnl: 0, total: 0, wins: 0, losses: 0, winRate: 0, profitFactor: 0 };

    // 1. HP / Account Equity
    document.getElementById('cardEquityHp').innerText = `$${account.equity.toFixed(2)}`;

    // 2. Move 1: NAS100 Open PnL
    const nasOpenPnLVal = openPnLByInstrument['NAS100'] !== undefined ? openPnLByInstrument['NAS100'] : account.openPnL;
    const nasOpenEl = document.getElementById('cardNasOpenPnL');
    nasOpenEl.innerText = `${nasOpenPnLVal >= 0 ? '+' : ''}$${nasOpenPnLVal.toFixed(2)}`;
    nasOpenEl.className = `move-pnl ${nasOpenPnLVal > 0 ? 'positive' : nasOpenPnLVal < 0 ? 'negative' : 'neutral'}`;

    const nasPositions = openPositions.filter(p => {
        const name = (p.instrumentName || '').toUpperCase();
        return name.includes('NAS') || name.includes('100') || p.tradableInstrumentId === '3884';
    });

    // --- ENABLE / DISABLE BUTTONS BASED ON OPEN POSITIONS ---
    const btnCloseNow = document.getElementById('btnCloseNow');
    const btnSlBe = document.getElementById('btnSlBe');
    const btnSlP5 = document.getElementById('btnSlP5');
    const btnSl5 = document.getElementById('btnSl5');
    const btnSl10 = document.getElementById('btnSl10');
    const btnStalk = document.getElementById('btnStalk');

    const btnTp10 = document.getElementById('btnTp10');
    const btnTp15 = document.getElementById('btnTp15');
    const btnTp20 = document.getElementById('btnTp20');

    const hasOpenPositions = nasPositions.length > 0;

    if (btnCloseNow) btnCloseNow.disabled = !hasOpenPositions;
    if (btnSlBe) btnSlBe.disabled = !hasOpenPositions;
    if (btnSlP5) btnSlP5.disabled = !hasOpenPositions;
    if (btnSl5) btnSl5.disabled = !hasOpenPositions;
    if (btnSl10) btnSl10.disabled = !hasOpenPositions;

    if (btnTp10) btnTp10.disabled = !hasOpenPositions;
    if (btnTp15) btnTp15.disabled = !hasOpenPositions;
    if (btnTp20) btnTp20.disabled = !hasOpenPositions;

    // --- SHINY GLOWING BORDER HIGHLIGHTING FOR ACTIVE TP AND SL BUTTONS ---
    // Reset all glow classes
    [btnTp10, btnTp15, btnTp20].forEach(b => b && b.classList.remove('active-tp-glow'));
    [btnSlBe, btnSlP5, btnSl5, btnSl10, btnStalk].forEach(b => b && b.classList.remove('active-sl-glow'));

    if (hasOpenPositions) {
        nasPositions.forEach(p => {
            const side = (p.side || 'buy').toLowerCase();
            const qty = parseFloat(p.qty || 0.01);
            const entry = parseFloat(p.avgPrice || 0);
            const sl = p.stopLoss ? parseFloat(p.stopLoss) : null;
            const tp = p.takeProfit ? parseFloat(p.takeProfit) : null;

            // Check Take Profits
            if (tp && entry > 0 && qty > 0) {
                const diff = side === 'buy' ? (tp - entry) * qty : (entry - tp) * qty;
                if (Math.abs(diff - 10.0) < 1.5 && btnTp10) btnTp10.classList.add('active-tp-glow');
                if (Math.abs(diff - 15.0) < 1.5 && btnTp15) btnTp15.classList.add('active-tp-glow');
                if (Math.abs(diff - 20.0) < 1.5 && btnTp20) btnTp20.classList.add('active-tp-glow');
            }

            // Check Stop Losses
            if (sl && entry > 0 && qty > 0) {
                const diff = side === 'buy' ? (sl - entry) * qty : (entry - sl) * qty;
                if (Math.abs(diff - 0.0) < 0.5 && btnSlBe) btnSlBe.classList.add('active-sl-glow');
                if (Math.abs(diff - 5.0) < 1.2 && btnSlP5) btnSlP5.classList.add('active-sl-glow');
                if (Math.abs(diff - (-5.0)) < 1.2 && btnSl5) btnSl5.classList.add('active-sl-glow');
                if (Math.abs(diff - (-10.0)) < 1.2 && btnSl10) btnSl10.classList.add('active-sl-glow');
            }

            // Check Trailing Stop (STALK)
            if (p.trailingOffset && btnStalk) {
                btnStalk.classList.add('active-sl-glow');
                btnStalk.innerText = "🐾 STALKING";
            }
        });
    }

    // --- 3. DYNAMIC POKEMON MOOD ARTWORK SWITCHING (+15 & +20 TIERS INCLUDED) ---
    const artImg = document.getElementById('cardArtImg');
    if (artImg) {
        let isShort = false;
        if (nasPositions.length > 0) {
            let buyLots = 0;
            let sellLots = 0;
            nasPositions.forEach(p => {
                const side = (p.side || 'buy').toLowerCase();
                const qty = parseFloat(p.qty || 0.01);
                if (side === 'sell') sellLots += qty;
                else buyLots += qty;
            });
            if (sellLots > buyLots) {
                isShort = true;
            } else if (sellLots === buyLots && sellLots > 0) {
                isShort = (nasPositions[0].side || '').toLowerCase() === 'sell';
            }
        }

        const prefix = isShort ? 'bear_' : 'art_';

        let selectedArt = `${prefix}neutral.jpg`;
        if (nasOpenPnLVal >= 20.0) {
            selectedArt = `${prefix}green_20.jpg`;
        } else if (nasOpenPnLVal >= 15.0) {
            selectedArt = `${prefix}green_15.jpg`;
        } else if (nasOpenPnLVal >= 10.0) {
            selectedArt = `${prefix}green_double.jpg`;
        } else if (nasOpenPnLVal > 2.0) {
            selectedArt = `${prefix}green_single.jpg`;
        } else if (nasOpenPnLVal >= -2.0) {
            selectedArt = `${prefix}neutral.jpg`;
        } else if (nasOpenPnLVal > -10.0) {
            selectedArt = `${prefix}red_single.jpg`;
        } else {
            selectedArt = `${prefix}red_double.jpg`;
        }

        if (!artImg.src.includes(selectedArt)) {
            artImg.src = selectedArt;
        }
    }

    // --- 4. Move 3: 5m REAL-TIME STOCHASTICS DISPLAY (Fast & Heavy) ---
    if (stochastics) {
        const sFast = stochastics.stoch_fast || stochastics.stoch_7_3_3 || { d: 35.0, status: 'NEUTRAL', class: 'neutral' };
        const sHeavy = stochastics.stoch_heavy || stochastics.stoch_40_1_4 || { d: 44.6, status: 'NEUTRAL', class: 'neutral' };

        const el7Val = document.getElementById('stoch7Val');
        const el7Badge = document.getElementById('stoch7Badge');
        if (el7Val) el7Val.innerText = sFast.d.toFixed(1);
        if (el7Badge) {
            el7Badge.innerText = sFast.status;
            el7Badge.className = `stoch-badge ${sFast.class}`;
        }

        const el40Val = document.getElementById('stoch40Val');
        const el40Badge = document.getElementById('stoch40Badge');
        if (el40Val) el40Val.innerText = sHeavy.d.toFixed(1);
        if (el40Badge) {
            el40Badge.innerText = sHeavy.status;
            el40Badge.className = `stoch-badge ${sHeavy.class}`;
        }
    }

    // 5. Move 4: NAS100 Cumulative Realized PnL
    const nasTotalPnLEl = document.getElementById('cardTotalPnL');
    nasTotalPnLEl.innerText = `${nasMetric.pnl >= 0 ? '+' : ''}$${nasMetric.pnl.toFixed(2)}`;
    nasTotalPnLEl.className = `move-pnl ${nasMetric.pnl > 0 ? 'positive' : nasMetric.pnl < 0 ? 'negative' : 'neutral'}`;

    // 6. Move 5: NAS100 Win Rate & Record
    document.getElementById('cardWinRate').innerText = `${nasMetric.winRate.toFixed(1)}%`;

    // 7. Stat Pills: Balance, Profit Factor, Retreat Fee (-$1 / LOT)
    document.getElementById('cardBalance').innerText = `$${account.balance.toFixed(2)}`;
    document.getElementById('cardProfitFactor').innerText = nasMetric.profitFactor ? nasMetric.profitFactor.toFixed(2) : (overallMetric.profitFactor ? overallMetric.profitFactor.toFixed(2) : '11.49');

    // Retreat Cost: Clean -$1.00 / LOT
    document.getElementById('cardFee').innerText = `-$1.00 / LOT`;
}
