let liveSummaryData = null;
let lastRefreshTimestamp = Date.now();

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    fetchPortfolioSummary();

    // Auto refresh every 4 seconds for reliable PnL, Equity & Stochastics updates
    setInterval(fetchPortfolioSummary, 4000);
});

function initEventListeners() {
    // Attack Move: Close All NAS100 Positions
    const attackBtn = document.getElementById('attackCloseNasBtn');
    if (attackBtn) {
        attackBtn.addEventListener('click', async (e) => {
            const confirmed = confirm("Execute Special Attack: Market Close ALL active NAS100 positions?");
            if (!confirmed) return;

            attackBtn.disabled = true;
            attackBtn.querySelector('.attack-title').innerText = "EXECUTING ATTACK...";
            attackBtn.querySelector('.attack-icon').innerText = "⚡";

            try {
                const res = await fetch('/api/close-all-nas100', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();

                alert(data.message || "NAS100 positions market closed successfully!");
                fetchPortfolioSummary();
            } catch (err) {
                alert("Attack execution error: " + err.message);
            } finally {
                attackBtn.disabled = false;
                attackBtn.querySelector('.attack-title').innerText = "ULTIMATE ATTACK: CLOSE ALL NAS100";
                attackBtn.querySelector('.attack-icon').innerText = "💥";
            }
        });
    }

    // Defensive Move: Set Break Even (BE), Positive Lock (+$5), -$5 and -$10 Stop Loss
    const defSelect = document.getElementById('defPosSelect');
    const btnSlBe = document.getElementById('btnSlBe');
    const btnSlP5 = document.getElementById('btnSlP5');
    const btnSl5 = document.getElementById('btnSl5');
    const btnSl10 = document.getElementById('btnSl10');

    // Max Power Move: Set +$10, +$15, +$20 Take Profit
    const btnTp10 = document.getElementById('btnTp10');
    const btnTp15 = document.getElementById('btnTp15');
    const btnTp20 = document.getElementById('btnTp20');

    if (defSelect) {
        defSelect.addEventListener('change', (e) => {
            const selectedId = e.target.value;
            const hasSelection = Boolean(selectedId);
            if (btnSlBe) btnSlBe.disabled = !hasSelection;
            if (btnSlP5) btnSlP5.disabled = !hasSelection;
            if (btnSl5) btnSl5.disabled = !hasSelection;
            if (btnSl10) btnSl10.disabled = !hasSelection;
            if (btnTp10) btnTp10.disabled = !hasSelection;
            if (btnTp15) btnTp15.disabled = !hasSelection;
            if (btnTp20) btnTp20.disabled = !hasSelection;
        });
    }

    const executeStopLoss = async (amount) => {
        const posId = defSelect ? defSelect.value : "all";
        let label = "";
        if (amount === 0) label = "Break Even (Exact Entry Price)";
        else if (amount > 0) label = `+$${amount}.00 Profit Lock`;
        else label = `-$${Math.abs(amount)}.00 Loss Cap`;

        const targetText = (posId && posId !== "all") ? `Position #${posId.slice(-6)}` : "ALL active open positions";
        const confirmed = confirm(`Apply Defensive Shield: Set ${label} Stop Loss on ${targetText}?`);
        if (!confirmed) return;

        if (btnSlBe) btnSlBe.disabled = true;
        if (btnSlP5) btnSlP5.disabled = true;
        if (btnSl5) btnSl5.disabled = true;
        if (btnSl10) btnSl10.disabled = true;

        try {
            const res = await fetch('/api/set-stoploss', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ positionId: posId, amount: amount })
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
            if (defSelect && (defSelect.value || defSelect.options.length > 0)) {
                if (btnSlBe) btnSlBe.disabled = false;
                if (btnSlP5) btnSlP5.disabled = false;
                if (btnSl5) btnSl5.disabled = false;
                if (btnSl10) btnSl10.disabled = false;
            }
        }
    };

    const executeTakeProfit = async (amount) => {
        const posId = defSelect ? defSelect.value : "all";
        const targetText = (posId && posId !== "all") ? `Position #${posId.slice(-6)}` : "ALL active open positions";
        const confirmed = confirm(`Unrealized Strike: Set Max Power +$${amount}.00 Take Profit on ${targetText}?`);
        if (!confirmed) return;

        if (btnTp10) btnTp10.disabled = true;
        if (btnTp15) btnTp15.disabled = true;
        if (btnTp20) btnTp20.disabled = true;

        try {
            const res = await fetch('/api/set-takeprofit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ positionId: posId, amount: amount })
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
            if (defSelect && (defSelect.value || defSelect.options.length > 0)) {
                if (btnTp10) btnTp10.disabled = false;
                if (btnTp15) btnTp15.disabled = false;
                if (btnTp20) btnTp20.disabled = false;
            }
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

    // --- POPULATE DEFENSIVE MOVE POSITION SELECTOR & ENABLE BUTTONS ---
    const defSelect = document.getElementById('defPosSelect');
    const btnSlBe = document.getElementById('btnSlBe');
    const btnSlP5 = document.getElementById('btnSlP5');
    const btnSl5 = document.getElementById('btnSl5');
    const btnSl10 = document.getElementById('btnSl10');

    const btnTp10 = document.getElementById('btnTp10');
    const btnTp15 = document.getElementById('btnTp15');
    const btnTp20 = document.getElementById('btnTp20');

    if (defSelect) {
        const currentSelected = defSelect.value;
        if (nasPositions.length === 0) {
            defSelect.innerHTML = `<option value="">No Open Positions</option>`;
            if (btnSlBe) btnSlBe.disabled = true;
            if (btnSlP5) btnSlP5.disabled = true;
            if (btnSl5) btnSl5.disabled = true;
            if (btnSl10) btnSl10.disabled = true;
            if (btnTp10) btnTp10.disabled = true;
            if (btnTp15) btnTp15.disabled = true;
            if (btnTp20) btnTp20.disabled = true;
        } else {
            const optionsHtml = `<option value="all">Apply to All Positions (${nasPositions.length})</option>` + nasPositions.map(p => {
                const pid = p.id || p.positionId;
                const side = (p.side || 'buy').toUpperCase();
                const qty = p.qty || 0.01;
                const entry = parseFloat(p.avgPrice || 0).toFixed(2);
                const slText = p.stopLoss ? ` [SL $${parseFloat(p.stopLoss).toFixed(2)}]` : '';
                const tpText = p.takeProfit ? ` [TP $${parseFloat(p.takeProfit).toFixed(2)}]` : '';
                return `<option value="${pid}" ${pid === currentSelected ? 'selected' : ''}>
                    #${pid.slice(-6)} (${side} ${qty}L @ ${entry})${slText}${tpText}
                </option>`;
            }).join('');
            
            defSelect.innerHTML = optionsHtml;

            if (currentSelected && (currentSelected === "all" || nasPositions.some(p => (p.id || p.positionId) === currentSelected))) {
                defSelect.value = currentSelected;
            } else {
                defSelect.value = "all";
            }

            if (btnSlBe) btnSlBe.disabled = false;
            if (btnSlP5) btnSlP5.disabled = false;
            if (btnSl5) btnSl5.disabled = false;
            if (btnSl10) btnSl10.disabled = false;
            if (btnTp10) btnTp10.disabled = false;
            if (btnTp15) btnTp15.disabled = false;
            if (btnTp20) btnTp20.disabled = false;
        }
    }

    // --- 3. DYNAMIC POKEMON MOOD ARTWORK SWITCHING (BULL VS BEAR BASED ON POSITION SIDE) ---
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
        if (nasOpenPnLVal >= 10.0) {
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
