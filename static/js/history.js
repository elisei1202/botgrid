// History Page JavaScript

async function updateHistory() {
    try {
        const period = document.getElementById('historyPeriod')?.value || '24';
        const trades = await apiGet(`/api/trades/recent?hours=${period}`);
        
        const tbody = document.getElementById('historyTable');
        if (!tbody) return;

        if (!trades || trades.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">No trades in this period</td></tr>';
            return;
        }

        tbody.innerHTML = trades.map(trade => `
            <tr>
                <td>${formatDate(trade.executed_at)}</td>
                <td><span class="badge ${trade.side === 'Buy' ? 'bg-success' : 'bg-danger'}">${trade.side}</span></td>
                <td>${formatCurrency(trade.price, 4)}</td>
                <td>${formatNumber(trade.qty, 2)}</td>
                <td>${formatCurrency(trade.fee, 4)}</td>
                <td>${trade.is_maker ? '✓ Maker' : '✗ Taker'}</td>
                <td class="${trade.profit > 0 ? 'text-success' : 'text-danger'}">
                    ${trade.profit ? formatCurrency(trade.profit, 4) : '-'}
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error updating history:', error);
    }
}
