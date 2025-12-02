// Grid Trading Bot - Main JavaScript

// API Base URL
const API_BASE = window.location.origin;

// Utility Functions
function formatNumber(num, decimals = 2) {
    return Number(num).toFixed(decimals);
}

function formatCurrency(num, decimals = 2) {
    return '$' + formatNumber(num, decimals);
}

function formatPercent(num, decimals = 2) {
    return formatNumber(num, decimals) + '%';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

function showNotification(message, type = 'info') {
    // Simple notification (can be enhanced with a library)
    console.log(`[${type.toUpperCase()}] ${message}`);
    alert(message);
}

// Update current time
function updateTime() {
    const now = new Date();
    const timeEl = document.getElementById('currentTime');
    if (timeEl) {
        timeEl.textContent = now.toLocaleString();
    }
}

// API Calls
async function apiGet(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return null;
    }
}

async function apiPost(endpoint, data = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return null;
    }
}

// Bot Controls
async function toggleBot() {
    const status = await apiGet('/api/status');
    if (!status) return;

    const btn = document.getElementById('startStopBtn');
    
    if (status.running) {
        // Stop bot
        if (confirm('Are you sure you want to stop trading?')) {
            const result = await apiPost('/api/stop');
            if (result && result.status === 'success') {
                showNotification('Trading stopped', 'success');
                btn.textContent = 'Start Trading';
                btn.classList.remove('btn-danger');
                btn.classList.add('btn-primary');
            }
        }
    } else {
        // Start bot
        if (confirm('Start trading with current settings?')) {
            const result = await apiPost('/api/start');
            if (result && result.status === 'success') {
                showNotification('Trading started', 'success');
                btn.textContent = 'Stop Trading';
                btn.classList.remove('btn-primary');
                btn.classList.add('btn-danger');
            }
        }
    }
}

// Update bot status indicator
async function updateBotStatus() {
    const status = await apiGet('/api/status');
    if (!status) return;

    const statusBadge = document.getElementById('botStatus');
    if (statusBadge) {
        const dot = statusBadge.querySelector('.status-dot');
        const text = statusBadge.querySelector('.status-text');
        
        if (status.running) {
            statusBadge.classList.add('running');
            text.textContent = 'Running';
        } else {
            statusBadge.classList.remove('running');
            text.textContent = 'Stopped';
        }
    }

    const btn = document.getElementById('startStopBtn');
    if (btn) {
        if (status.running) {
            btn.textContent = 'Stop Trading';
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-danger');
        } else {
            btn.textContent = 'Start Trading';
            btn.classList.remove('btn-danger');
            btn.classList.add('btn-primary');
        }
    }
}

// Dashboard Updates
async function updateDashboard() {
    try {
        // Update status
        await updateBotStatus();
        
        // Get balance
        const balance = await apiGet('/api/balance');
        if (balance) {
            document.getElementById('totalEquity').textContent = formatCurrency(balance.total_equity);
            document.getElementById('availableBalance').textContent = formatCurrency(balance.available);
            
            // Calculate equity change (simplified)
            const change = balance.unrealized_pnl / balance.total_equity * 100;
            const changeEl = document.getElementById('equityChange');
            if (changeEl) {
                changeEl.textContent = (change >= 0 ? '+' : '') + formatPercent(change);
                changeEl.className = 'stat-change ' + (change >= 0 ? 'positive' : 'negative');
            }
        }

        // Get PnL
        const pnl = await apiGet('/api/pnl?period=24h');
        if (pnl) {
            const pnlEl = document.getElementById('pnl24h');
            const pnlChangeEl = document.getElementById('pnlChange');
            
            if (pnlEl) {
                pnlEl.textContent = formatCurrency(pnl.net_pnl);
            }
            
            if (pnlChangeEl) {
                const pnlPct = pnl.win_rate || 0;
                pnlChangeEl.textContent = formatPercent(pnlPct) + ' win rate';
                pnlChangeEl.className = 'stat-change ' + (pnlPct >= 50 ? 'positive' : 'negative');
            }
        }

        // Get status for trades count
        const status = await apiGet('/api/status');
        if (status) {
            document.getElementById('trades24h').textContent = status.trades_24h || 0;
            
            // Update grid info
            if (status.grid) {
                document.getElementById('centerPrice').textContent = formatCurrency(status.grid.center_price, 4);
                document.getElementById('activeOrders').textContent = status.grid.total_active_orders || 0;
            }
            
            if (status.profile) {
                document.getElementById('activeProfile').textContent = status.profile;
            }
        }

        // Get current price
        const gridData = await apiGet('/api/grid/levels');
        if (gridData) {
            document.getElementById('currentPrice').textContent = formatCurrency(gridData.current_price, 4);
        }

        // Get risk metrics
        const risk = await apiGet('/api/risk/metrics');
        if (risk) {
            document.getElementById('exposure').textContent = formatPercent(risk.exposure_pct || 0);
            document.getElementById('drawdown').textContent = formatPercent(risk.current_drawdown_pct || 0);
            document.getElementById('availableTrading').textContent = formatCurrency(risk.available_for_trading || 0);
            
            const killSwitchEl = document.getElementById('killSwitch');
            if (killSwitchEl) {
                killSwitchEl.textContent = risk.kill_switch_active ? '🔴 ACTIVE' : '🟢 Inactive';
                killSwitchEl.className = 'info-value ' + (risk.kill_switch_active ? 'text-danger' : 'text-success');
            }
        }

        // Get recent trades
        const trades = await apiGet('/api/trades/recent?hours=24');
        if (trades) {
            updateRecentTrades(trades.slice(0, 10));
        }

    } catch (error) {
        console.error('Error updating dashboard:', error);
    }
}

function updateRecentTrades(trades) {
    const tbody = document.getElementById('recentTrades');
    if (!tbody) return;

    if (!trades || trades.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center">No trades yet</td></tr>';
        return;
    }

    tbody.innerHTML = trades.map(trade => `
        <tr>
            <td>${formatDate(trade.executed_at)}</td>
            <td><span class="badge ${trade.side === 'Buy' ? 'bg-success' : 'bg-danger'}">${trade.side}</span></td>
            <td>${formatCurrency(trade.price, 4)}</td>
            <td>${formatNumber(trade.qty, 2)}</td>
            <td>${formatCurrency(trade.fee, 4)}</td>
            <td class="${trade.profit > 0 ? 'text-success' : 'text-danger'}">
                ${trade.profit ? formatCurrency(trade.profit, 4) : '-'}
            </td>
        </tr>
    `).join('');
}

// Equity Chart
let equityChart = null;

async function updateEquityChart() {
    const period = document.getElementById('chartPeriod')?.value || '24';
    const data = await apiGet(`/api/equity/chart?hours=${period}`);
    
    if (!data || data.length === 0) return;

    const ctx = document.getElementById('equityChart');
    if (!ctx) return;

    const labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());
    const equity = data.map(d => d.equity);

    if (equityChart) {
        equityChart.destroy();
    }

    equityChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Equity',
                data: equity,
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    grid: {
                        color: '#334155'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                x: {
                    grid: {
                        color: '#334155'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                }
            }
        }
    });
}
