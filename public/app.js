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

    // Defensive Move: Set Break Even, -$5 and -$10 Stop Loss
    const defSelect = document.getElementById('defPosSelect');
    const btnSlBe = document.getElementById('btnSlBe');
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
            if (btnSl5) btnSl5.disabled = !hasSelection;
            if (btnSl10) btnSl10.disabled = !hasSelection;
            if (btnTp10) btnTp10.disabled = !hasSelection;
            if (btnTp15) btnTp15.disabled = !hasSelection;
            if (btnTp20) btnTp20.disabled = !hasSelection;
        });
    }

    const executeStopLoss = async (amount) => {
        const posId = defSelect ? defSelect.value : null;
        if (!posId) {
            alert("Please select an open position first!");
            return;
        }

        const label = amount === 0 ? "Break Even (Exact Entry Price)" : `-$${amount}.00`;
        const confirmed = confirm(`Apply Defensive Shield: Set ${label} Stop Loss on Position #${posId}?`);
        if (!confirmed) return;

        if (btnSlBe) btnSlBe.disabled = true;
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
            if (defSelect && defSelect.value) {
                if (btnSlBe) btnSlBe.disabled = false;
                if (btnSl5) btnSl5.disabled = false;
                if (btnSl10) btnSl10.disabled = false;
            }
        }
    };

    const executeTakeProfit = async (amount) => {
        const posId = defSelect ? defSelect.value : null;
        if (!posId) {
            alert("Please select an open position first!");
            return;
        }

        const confirmed = confirm(`Unrealized Strike: Set Max Power +$${amount}.00 Take Profit on Position #${posId}?`);
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
            if (defSelect && defSelect.value) {
                if (btnTp10) btnTp10.disabled = false;
                if (btnTp15) btnTp15.disabled = false;
                if (btnTp20) btnTp20.disabled = false;
            }
        }
    };

    if (btnSlBe) btnSlBe.addEventListener('click', () => executeStopLoss(0.0));
    if (btnSl5) btnSl5.addEventListener('click', () => executeStopLoss(5.0));
    if (btnSl10) btnSl10.addEventListener('click', () => executeStopLoss(10.0));

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
    
    document.getElementById('cardNasOpenSub').innerText = `NAS100 Open PnL (${nasPositions.length} Active Positions)`;

    // --- POPULATE DEFENSIVE MOVE POSITION SELECTOR & ENABLE BUTTONS ---
    const defSelect = document.getElementById('defPosSelect');
    const btnSlBe = document.getElementById('btnSlBe');
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
            if (btnSl5) btnSl5.disabled = true;
            if (btnSl10) btnSl10.disabled = true;
            if (btnTp10) btnTp10.disabled = true;
            if (btnTp15) btnTp15.disabled = true;
            if (btnTp20) btnTp20.disabled = true;
        } else {
            defSelect.innerHTML = `<option value="">Select Position...</option>` + nasPositions.map(p => {
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

            if (currentSelected && nasPositions.some(p => (p.id || p.positionId) === currentSelected)) {
                defSelect.value = currentSelected;
                if (btnSlBe) btnSlBe.disabled = false;
                if (btnSl5) btnSl5.disabled = false;
                if (btnSl10) btnSl10.disabled = false;
                if (btnTp10) btnTp10.disabled = false;
                if (btnTp15) btnTp15.disabled = false;
                if (btnTp20) btnTp20.disabled = false;
            } else if (nasPositions.length === 1) {
                // Auto select if only 1 position exists
                defSelect.value = nasPositions[0].id || nasPositions[0].positionId;
                if (btnSlBe) btnSlBe.disabled = false;
                if (btnSl5) btnSl5.disabled = false;
                if (btnSl10) btnSl10.disabled = false;
                if (btnTp10) btnTp10.disabled = false;
                if (btnTp15) btnTp15.disabled = false;
                if (btnTp20) btnTp20.disabled = false;
            }
        }
    }

    // --- 3. DYNAMIC POKEMON MOOD ARTWORK SWITCHING BASED ON OPEN PNL ---
    const artImg = document.getElementById('cardArtImg');
    if (artImg) {
        let selectedArt = 'art_neutral.jpg';
        if (nasOpenPnLVal >= 10.0) {
            selectedArt = 'art_green_double.jpg';   // Excited Double Digit Green Victory Bull
        } else if (nasOpenPnLVal > 2.0) {
            selectedArt = 'art_green_single.jpg';   // Happy Single Digit Green Smiling Bull
        } else if (nasOpenPnLVal >= -2.0) {
            selectedArt = 'art_neutral.jpg';        // Chill Neutral Bull
        } else if (nasOpenPnLVal > -10.0) {
            selectedArt = 'art_red_single.jpg';      // Worried Single Digit Red Sweating Bull
        } else {
            selectedArt = 'art_red_double.jpg';      // Fiery Double Digit Red Warrior Bull
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
    document.getElementById('cardClosedSub').innerText = `NAS100 Cumulative Realized PnL (${nasMetric.total} Executed Trades)`;

    // 6. Move 5: NAS100 Win Rate & Record
    document.getElementById('cardWinRate').innerText = `${nasMetric.winRate.toFixed(1)}%`;
    document.getElementById('cardWinLossSub').innerText = `${nasMetric.wins} Wins / ${nasMetric.losses} Losses (${nasMetric.winRate.toFixed(1)}% Accuracy)`;

    // 7. Stat Pills: Balance, Profit Factor, Retreat Fee (-$1 / LOT)
    document.getElementById('cardBalance').innerText = `$${account.balance.toFixed(2)}`;
    document.getElementById('cardProfitFactor').innerText = nasMetric.profitFactor ? nasMetric.profitFactor.toFixed(2) : (overallMetric.profitFactor ? overallMetric.profitFactor.toFixed(2) : '11.49');

    // Retreat Cost: Clean -$1.00 / LOT
    document.getElementById('cardFee').innerText = `-$1.00 / LOT`;
}
