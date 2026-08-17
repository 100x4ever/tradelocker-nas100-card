let liveSummaryData = null;
let lastRefreshTimestamp = Date.now();
let isCandleModalOpen = false;

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    fetchPortfolioSummary();

    // Auto refresh every 4 seconds for reliable PnL, Equity, Stochastics & 5m Candles
    setInterval(fetchPortfolioSummary, 4000);
});

function initEventListeners() {
    // CANDLE SIGHT MODAL TOGGLE
    const btnOpenCandleSight = document.getElementById('btnOpenCandleSight');
    const btnCloseCandleSight = document.getElementById('btnCloseCandleSight');
    const candleSightModal = document.getElementById('candleSightModal');

    if (btnOpenCandleSight && candleSightModal) {
        btnOpenCandleSight.addEventListener('click', () => {
            candleSightModal.style.display = 'flex';
            isCandleModalOpen = true;
            if (liveSummaryData && liveSummaryData.latest5mBars) {
                renderCandleSightModal(liveSummaryData.latest5mBars);
            }
        });
    }

    if (btnCloseCandleSight && candleSightModal) {
        btnCloseCandleSight.addEventListener('click', () => {
            candleSightModal.style.display = 'none';
            isCandleModalOpen = false;
        });
    }

    if (candleSightModal) {
        candleSightModal.addEventListener('click', (e) => {
            if (e.target === candleSightModal) {
                candleSightModal.style.display = 'none';
                isCandleModalOpen = false;
            }
        });
    }

    // BANISH Button: Instant Market Close ALL open positions
    const btnCloseNow = document.getElementById('btnCloseNow');
    if (btnCloseNow) {
        btnCloseNow.addEventListener('click', async () => {
            const confirmed = confirm("Arcane Strike BANISH: Market Close ALL active open positions immediately?");
            if (!confirmed) return;

            btnCloseNow.disabled = true;
            btnCloseNow.innerText = "BANISHING...";

            try {
                const res = await fetch('/api/close-all-nas100', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await res.json();

                alert(data.message || "All positions market closed & banished!");
                fetchPortfolioSummary();
            } catch (err) {
                alert("Banish error: " + err.message);
            } finally {
                btnCloseNow.disabled = false;
                btnCloseNow.innerText = "⚡ BANISH";
            }
        });
    }

    // Max Power Move: Set +$10, +$15, +$20 Take Profit
    const btnTp10 = document.getElementById('btnTp10');
    const btnTp15 = document.getElementById('btnTp15');
    const btnTp20 = document.getElementById('btnTp20');

    const executeTakeProfit = async (amount) => {
        const confirmed = confirm(`Arcane Strike: Set +$${amount}.00 Take Profit on ALL active open positions?`);
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

        if (isCandleModalOpen && data.latest5mBars) {
            renderCandleSightModal(data.latest5mBars);
        }
    } catch (err) {
        console.error('Failed to fetch summary:', err);
    }
}

function renderCandleSightModal(bars) {
    if (!bars || bars.length === 0) return;

    const canvas = document.getElementById('candleCanvas');
    const cardsGrid = document.getElementById('candleCardsGrid');
    if (!canvas || !cardsGrid) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Clear Canvas
    ctx.clearRect(0, 0, width, height);

    // Draw Background Grid
    ctx.strokeStyle = 'rgba(51, 65, 85, 0.4)';
    ctx.lineWidth = 1;
    for (let y = 30; y < height; y += 35) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    // Min and Max Prices for 3 Candles
    let minPrice = Infinity;
    let maxPrice = -Infinity;
    bars.forEach(b => {
        if (b.l < minPrice) minPrice = b.l;
        if (b.h > maxPrice) maxPrice = b.h;
    });

    const padding = (maxPrice - minPrice) * 0.15 || 5.0;
    minPrice -= padding;
    maxPrice += padding;

    const priceToY = (p) => {
        return height - 25 - ((p - minPrice) / (maxPrice - minPrice)) * (height - 50);
    };

    // Render 3 Candles on Canvas
    const numBars = bars.length;
    const colWidth = width / numBars;

    bars.forEach((b, idx) => {
        const xCenter = (idx + 0.5) * colWidth;
        const openY = priceToY(b.o);
        const closeY = priceToY(b.c);
        const highY = priceToY(b.h);
        const lowY = priceToY(b.l);

        const isBullish = b.c >= b.o;
        const color = isBullish ? '#10b981' : '#ef4444';

        // Draw Wick
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(xCenter, highY);
        ctx.lineTo(xCenter, lowY);
        ctx.stroke();

        // Draw Real Body
        const bodyTop = Math.min(openY, closeY);
        const bodyHeight = Math.max(Math.abs(closeY - openY), 4);
        ctx.fillStyle = color;
        ctx.fillRect(xCenter - 14, bodyTop, 28, bodyHeight);
        ctx.strokeStyle = isBullish ? '#34d399' : '#fca5a5';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(xCenter - 14, bodyTop, 28, bodyHeight);

        // Price Label Top (High)
        ctx.fillStyle = '#cbd5e1';
        ctx.font = '10px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(b.h.toFixed(1), xCenter, highY - 6);

        // Time / Label Bottom
        const d = new Date(b.t);
        const timeStr = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
        const label = idx === numBars - 1 ? `${timeStr} (LIVE)` : timeStr;

        ctx.fillStyle = idx === numBars - 1 ? '#38bdf8' : '#94a3b8';
        ctx.font = 'bold 9.5px "JetBrains Mono", monospace';
        ctx.fillText(label, xCenter, height - 6);
    });

    // Populate Readout Cards (Hiding OCHL, showing clean +/- point/dollar move per candle)
    cardsGrid.innerHTML = '';
    const labels = ["2 BARS AGO", "PREVIOUS", "CURRENT LIVE"];

    bars.forEach((b, idx) => {
        const isBullish = b.c >= b.o;
        const diff = b.c - b.o;
        const diffSign = diff >= 0 ? '+' : '';
        const d = new Date(b.t);
        const timeStr = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;

        const cardEl = document.createElement('div');
        cardEl.className = `c-card ${isBullish ? 'bullish' : 'bearish'}`;
        cardEl.innerHTML = `
            <div class="time-lbl">${timeStr} • ${labels[idx]}</div>
            <div class="badge-val ${isBullish ? 'green' : 'red'}">${diffSign}${diff.toFixed(1)} PTS</div>
        `;
        cardsGrid.appendChild(cardEl);
    });
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

    const hasOpenPositions = nasPositions.length > 0;

    // --- ENABLE / DISABLE TAKE PROFIT & BANISH BUTTONS ---
    const btnCloseNow = document.getElementById('btnCloseNow');
    const btnTp10 = document.getElementById('btnTp10');
    const btnTp15 = document.getElementById('btnTp15');
    const btnTp20 = document.getElementById('btnTp20');

    if (btnCloseNow) btnCloseNow.disabled = !hasOpenPositions;
    if (btnTp10) btnTp10.disabled = !hasOpenPositions;
    if (btnTp15) btnTp15.disabled = !hasOpenPositions;
    if (btnTp20) btnTp20.disabled = !hasOpenPositions;

    // --- SHINY GLOWING BORDER HIGHLIGHTING FOR ACTIVE TAKE PROFIT BUTTONS ---
    [btnTp10, btnTp15, btnTp20].forEach(b => b && b.classList.remove('active-tp-glow'));

    if (hasOpenPositions) {
        nasPositions.forEach(p => {
            const side = (p.side || 'buy').toLowerCase();
            const qty = parseFloat(p.qty || 0.01);
            const entry = parseFloat(p.avgPrice || 0);
            const tp = p.takeProfitPrice ? parseFloat(p.takeProfitPrice) : null;

            if (tp && entry > 0 && qty > 0) {
                const diff = side === 'buy' ? (tp - entry) * qty : (entry - tp) * qty;
                if (Math.abs(diff - 10.0) < 1.5 && btnTp10) btnTp10.classList.add('active-tp-glow');
                if (Math.abs(diff - 15.0) < 1.5 && btnTp15) btnTp15.classList.add('active-tp-glow');
                if (Math.abs(diff - 20.0) < 1.5 && btnTp20) btnTp20.classList.add('active-tp-glow');
            }
        });
    }

    // --- AEGIS SHIELD: SHOW ONLY THE ACTIVE STOPLOSS AMOUNT READOUT ---
    const shieldPowerEl = document.getElementById('cardShieldPower');
    if (shieldPowerEl) {
        if (!hasOpenPositions) {
            shieldPowerEl.innerText = "STANDBY";
            shieldPowerEl.className = "shield-power-val neutral";
        } else {
            const p = nasPositions[0];
            const side = (p.side || 'buy').toLowerCase();
            const qty = parseFloat(p.qty || 0.01);
            const entry = parseFloat(p.avgPrice || 0);

            if (p.trailingOffset) {
                shieldPowerEl.innerText = "🐾 STALKING";
                shieldPowerEl.className = "shield-power-val positive";
            } else {
                let diff = null;

                if (p.stopLossAmount !== undefined && p.stopLossAmount !== null) {
                    diff = parseFloat(p.stopLossAmount);
                } else if (p.stopLossPrice && entry > 0 && qty > 0) {
                    const slPrice = parseFloat(p.stopLossPrice);
                    diff = side === 'buy' ? (slPrice - entry) * qty : (entry - slPrice) * qty;
                }

                if (diff !== null && !isNaN(diff)) {
                    const rounded = Math.round(diff);
                    if (Math.abs(diff) < 0.25) {
                        shieldPowerEl.innerText = "🛡️ BE ($0)";
                        shieldPowerEl.className = "shield-power-val positive";
                    } else if (diff > 0) {
                        shieldPowerEl.innerText = `🛡️ +$${rounded}`;
                        shieldPowerEl.className = "shield-power-val positive";
                    } else {
                        shieldPowerEl.innerText = `🛡️ -$${Math.abs(rounded)}`;
                        shieldPowerEl.className = "shield-power-val negative";
                    }
                } else {
                    shieldPowerEl.innerText = "🛡️ -$10";
                    shieldPowerEl.className = "shield-power-val negative";
                }
            }
        }
    }

    // --- 3. DYNAMIC POKEMON MOOD ARTWORK SWITCHING ---
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

    // --- 4. Move 4: 5m REAL-TIME STOCHASTICS DISPLAY (Fast & Heavy) ---
    if (stochastics) {
        const sFast = stochastics.stoch_fast || stochastics.stoch_7_3_3 || { d: 35.0, status: "NEUTRAL", class: "neutral" };
        const sHeavy = stochastics.stoch_heavy || stochastics.stoch_40_1_4 || { d: 44.6, status: "NEUTRAL", class: "neutral" };

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

    // 5. Move 5: NAS100 Cumulative Realized PnL (War Spoils)
    const nasTotalPnLEl = document.getElementById('cardTotalPnL');
    nasTotalPnLEl.innerText = `${nasMetric.pnl >= 0 ? '+' : ''}$${nasMetric.pnl.toFixed(2)}`;
    nasTotalPnLEl.className = `move-pnl ${nasMetric.pnl > 0 ? 'positive' : nasMetric.pnl < 0 ? 'negative' : 'neutral'}`;

    // 6. Move 6: NAS100 Win Rate (Valor Accuracy)
    document.getElementById('cardWinRate').innerText = `${nasMetric.winRate.toFixed(1)}%`;

    // 7. Stat Pills: Gold Balance, War Factor, Retreat Toll (-$1 / LOT)
    document.getElementById('cardBalance').innerText = `$${account.balance.toFixed(2)}`;
    document.getElementById('cardProfitFactor').innerText = nasMetric.profitFactor ? nasMetric.profitFactor.toFixed(2) : (overallMetric.profitFactor ? overallMetric.profitFactor.toFixed(2) : '2.52');

    // Retreat Cost: Clean -$1.00 / LOT
    document.getElementById('cardFee').innerText = `-$1.00 / LOT`;
}
