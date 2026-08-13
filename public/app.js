let liveSummaryData = null;
let lastRefreshTimestamp = Date.now();

document.addEventListener('DOMContentLoaded', () => {
    lucide.createIcons();
    initEventListeners();
    init3DTiltEffect();
    fetchPortfolioSummary();

    // Auto refresh every 1.5 seconds (Safe from TradeLocker rate limits)
    setInterval(fetchPortfolioSummary, 1500);
    setInterval(updateRefreshTimeAgo, 500);
});

function initEventListeners() {
    // Attack Move: Close All NAS100 Positions
    const attackBtn = document.getElementById('attackCloseNasBtn');
    if (attackBtn) {
        attackBtn.addEventListener('click', async (e) => {
            e.stopPropagation(); // Prevents tilt jitter on click
            
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

    // Account Selector
    const accountSelect = document.getElementById('accountSelect');
    if (accountSelect) {
        accountSelect.addEventListener('change', async (e) => {
            const selectedId = e.target.value;
            try {
                await fetch('/api/select-account', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ accId: selectedId })
                });
                fetchPortfolioSummary();
            } catch (err) {
                console.error('Account switch failed:', err);
            }
        });
    }

    // Login Modal
    const modal = document.getElementById('loginModal');
    const openLoginBtn = document.getElementById('openLoginBtn');
    const closeLoginBtn = document.getElementById('closeLoginBtn');
    
    if (openLoginBtn && modal) openLoginBtn.addEventListener('click', () => modal.classList.add('open'));
    if (closeLoginBtn && modal) closeLoginBtn.addEventListener('click', () => modal.classList.remove('open'));

    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const connectBtn = document.getElementById('connectBtn');
            connectBtn.disabled = true;
            connectBtn.innerHTML = `<i data-lucide="loader-2" class="spin-icon"></i> Connecting...`;

            const payload = {
                environment: document.getElementById('loginEnv').value,
                server: document.getElementById('loginServer').value,
                email: document.getElementById('loginEmail').value,
                password: document.getElementById('loginPassword').value,
                targetAccId: "812189"
            };

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (data.status === 'ok') {
                    modal.classList.remove('open');
                    fetchPortfolioSummary();
                } else {
                    alert('Login failed: ' + (data.message || 'Check credentials'));
                }
            } catch (err) {
                alert('Connection error: ' + err.message);
            } finally {
                connectBtn.disabled = false;
                connectBtn.innerHTML = `<i data-lucide="plug"></i> Connect & Fetch Portfolio`;
                lucide.createIcons();
            }
        });
    }
}

function init3DTiltEffect() {
    const card = document.getElementById('cardWrapper');
    if (!card) return;

    card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        const centerX = rect.width / 2;
        const centerY = rect.height / 2;

        const rotateX = ((y - centerY) / centerY) * -12;
        const rotateY = ((x - centerX) / centerX) * 12;

        card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
    });

    card.addEventListener('mouseleave', () => {
        card.style.transform = `perspective(1000px) rotateX(0deg) rotateY(0deg) scale(1)`;
    });
}

async function fetchPortfolioSummary() {
    try {
        const res = await fetch('/api/summary');
        const data = await res.json();
        liveSummaryData = data;
        lastRefreshTimestamp = Date.now();
        renderData();
    } catch (err) {
        console.error('Failed to fetch summary:', err);
    }
}

function updateRefreshTimeAgo() {
    const elapsedSec = Math.floor((Date.now() - lastRefreshTimestamp) / 1000);
    const el = document.getElementById('lastRefresh');
    if (el) {
        el.querySelector('span').innerText = `Live (${elapsedSec}s ago)`;
    }
}

function renderData() {
    if (!liveSummaryData) return;

    const { account, openPnLByInstrument, metrics, openPositions } = liveSummaryData;

    // Header Account Info
    document.getElementById('accountName').innerText = `${account.server} (${account.environment ? account.environment.toUpperCase() : 'LIVE'})`;
    document.getElementById('cardArtBadge').innerText = `NO. ${account.accId} • US TECH 100`;

    // Account Selector
    const selectEl = document.getElementById('accountSelect');
    if (selectEl) {
        if (account.availableAccounts && account.availableAccounts.length > 0) {
            selectEl.innerHTML = account.availableAccounts.map(a => `
                <option value="${a.id}" ${a.isSelected ? 'selected' : ''}>
                    Acc #${a.id} ($${a.balance.toFixed(2)})
                </option>
            `).join('');
        } else {
            selectEl.innerHTML = `<option value="${account.accId}">Acc #${account.accId}</option>`;
        }
    }

    // --- POPULATE POKEMON / MTG CARD METRICS ---
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

    // 3. Move 2: NAS100 Cumulative Realized PnL
    const nasTotalPnLEl = document.getElementById('cardTotalPnL');
    nasTotalPnLEl.innerText = `${nasMetric.pnl >= 0 ? '+' : ''}$${nasMetric.pnl.toFixed(2)}`;
    nasTotalPnLEl.className = `move-pnl ${nasMetric.pnl > 0 ? 'positive' : nasMetric.pnl < 0 ? 'negative' : 'neutral'}`;
    document.getElementById('cardClosedSub').innerText = `NAS100 Cumulative Realized PnL (${nasMetric.total} Executed Trades)`;

    // 4. Move 3: NAS100 Win Rate & Record
    document.getElementById('cardWinRate').innerText = `${nasMetric.winRate.toFixed(1)}%`;
    document.getElementById('cardWinLossSub').innerText = `${nasMetric.wins} Wins / ${nasMetric.losses} Losses (${nasMetric.winRate.toFixed(1)}% NAS100 Accuracy)`;

    // 5. Stat Pills: Balance, Profit Factor, Retreat Fee (-$1 / LOT)
    document.getElementById('cardBalance').innerText = `$${account.balance.toFixed(2)}`;
    document.getElementById('cardProfitFactor').innerText = nasMetric.profitFactor ? nasMetric.profitFactor.toFixed(2) : (overallMetric.profitFactor ? overallMetric.profitFactor.toFixed(2) : '11.49');
    
    // Fee: -$1 / LOT
    const totalFee = (nasMetric.lots || 0.95) * 1.00;
    document.getElementById('cardFee').innerText = `-$1.00 / LOT (-$${totalFee.toFixed(2)})`;
}
