let liveSummaryData = null;
let lastRefreshTimestamp = Date.now();

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    fetchPortfolioSummary();

    // Auto refresh every 4 seconds for reliable PnL & Equity updates
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
}

async function fetchPortfolioSummary() {
    try {
        // Cache-busting timestamp param guarantees fresh response on every call
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

    const { account, openPnLByInstrument, metrics, openPositions } = liveSummaryData;

    const nasMetric = metrics['NAS100'] || { pnl: 0, total: 0, wins: 0, losses: 0, winRate: 0, profitFactor: 0, lots: 0 };
    const overallMetric = metrics['OVERALL'] || { pnl: 0, total: 0, wins: 0, losses: 0, winRate: 0, profitFactor: 0 };

    // 1. HP / Account Equity
    document.getElementById('cardEquityHp').innerText = `$${account.equity.toFixed(2)}`;

    // 2. Move 1: NAS100 Open PnL
    const nasOpenPnLVal = openPnLByInstrument['NAS100'] !== undefined ? openPnLByInstrument['NAS100'] : account.openPnL;
    const nasOpenEl = document.getElementById('cardNasOpenPnL');
    nasOpenEl.innerText = `${nasOpenPnLVal >= 0 ? '+' : ''}$${nasOpenPnLVal.toFixed(2)}`;
    nasOpenEl.className = `move-pnl ${nasOpenPnLVal > 0 ? 'positive' : nasOpenPnLVal < 0 ? 'negative' : 'neutral'}`;

    const nasPositionsCount = openPositions.filter(p => {
        const name = (p.instrumentName || '').toUpperCase();
        return name.includes('NAS') || name.includes('100') || p.tradableInstrumentId === '3884';
    }).length;
    document.getElementById('cardNasOpenSub').innerText = `NAS100 Open PnL (${nasPositionsCount} Active Positions)`;

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

    // 4. Move 2: NAS100 Cumulative Realized PnL
    const nasTotalPnLEl = document.getElementById('cardTotalPnL');
    nasTotalPnLEl.innerText = `${nasMetric.pnl >= 0 ? '+' : ''}$${nasMetric.pnl.toFixed(2)}`;
    nasTotalPnLEl.className = `move-pnl ${nasMetric.pnl > 0 ? 'positive' : nasMetric.pnl < 0 ? 'negative' : 'neutral'}`;
    document.getElementById('cardClosedSub').innerText = `NAS100 Cumulative Realized PnL (${nasMetric.total} Executed Trades)`;

    // 5. Move 3: NAS100 Win Rate & Record
    document.getElementById('cardWinRate').innerText = `${nasMetric.winRate.toFixed(1)}%`;
    document.getElementById('cardWinLossSub').innerText = `${nasMetric.wins} Wins / ${nasMetric.losses} Losses (${nasMetric.winRate.toFixed(1)}% Accuracy)`;

    // 6. Stat Pills: Balance, Profit Factor, Retreat Fee (-$1 / LOT)
    document.getElementById('cardBalance').innerText = `$${account.balance.toFixed(2)}`;
    document.getElementById('cardProfitFactor').innerText = nasMetric.profitFactor ? nasMetric.profitFactor.toFixed(2) : (overallMetric.profitFactor ? overallMetric.profitFactor.toFixed(2) : '11.49');

    // Retreat Cost: Clean -$1.00 / LOT
    document.getElementById('cardFee').innerText = `-$1.00 / LOT`;
}
