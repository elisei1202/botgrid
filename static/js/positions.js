// Positions Page JavaScript

async function updatePositions() {
    try {
        await updateBotStatus();
        
        const positions = await apiGet('/api/positions');
        if (!positions) return;

        const tbody = document.getElementById('positionsTable');
        if (!tbody) return;

        if (positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center">No open positions</td></tr>';
            return;
        }

        tbody.innerHTML = positions.map(pos => `
            <tr>
                <td><strong>${pos.symbol}</strong></td>
                <td><span class="badge ${pos.side === 'Buy' ? 'bg-success' : 'bg-danger'}">${pos.side}</span></td>
                <td>${formatNumber(pos.size, 2)}</td>
                <td>${formatCurrency(pos.entry_price, 4)}</td>
                <td>${formatCurrency(pos.mark_price, 4)}</td>
                <td class="${pos.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}">
                    ${formatCurrency(pos.unrealized_pnl, 4)}
                </td>
                <td>${formatCurrency(pos.position_value, 2)}</td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error updating positions:', error);
    }
}
