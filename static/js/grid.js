// Grid Levels Page JavaScript

async function updateGridLevels() {
    try {
        await updateBotStatus();
        
        const data = await apiGet('/api/grid/levels');
        if (!data) return;

        // Update stats
        document.getElementById('centerPrice').textContent = formatCurrency(data.center_price, 4);
        document.getElementById('currentPrice').textContent = formatCurrency(data.current_price, 4);
        document.getElementById('buyOrdersCount').textContent = data.buy_orders.length;
        document.getElementById('sellOrdersCount').textContent = data.sell_orders.length;
        
        // Update position indicator
        const positionEl = document.getElementById('pricePosition');
        if (data.current_price > data.center_price) {
            positionEl.textContent = `Above center (+${formatPercent((data.current_price - data.center_price) / data.center_price * 100)})`;
        } else {
            positionEl.textContent = `Below center (${formatPercent((data.current_price - data.center_price) / data.center_price * 100)})`;
        }

        // Update tables
        updateOrdersTable('sellOrders', data.sell_orders, data.center_price, 'sell');
        updateOrdersTable('buyOrders', data.buy_orders, data.center_price, 'buy');
        
        // Update badges
        document.getElementById('sellBadge').textContent = `${data.sell_orders.length} orders`;
        document.getElementById('buyBadge').textContent = `${data.buy_orders.length} orders`;
        
        // Update visualization
        updateGridVisualization(data);

    } catch (error) {
        console.error('Error updating grid levels:', error);
    }
}

function updateOrdersTable(tbodyId, orders, centerPrice, type) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;

    if (orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">No orders</td></tr>';
        return;
    }

    tbody.innerHTML = orders.map(order => {
        const distance = ((order.price - centerPrice) / centerPrice * 100).toFixed(2);
        const notional = order.price * order.qty;
        
        return `
            <tr>
                <td>${formatCurrency(order.price, 4)}</td>
                <td>${formatNumber(order.qty, 2)}</td>
                <td>${formatCurrency(notional, 2)}</td>
                <td>${distance >= 0 ? '+' : ''}${distance}%</td>
                <td><span class="badge">${order.status}</span></td>
            </tr>
        `;
    }).join('');
}

function updateGridVisualization(data) {
    const viz = document.getElementById('gridVisualization');
    if (!viz) return;

    const allOrders = [
        ...data.sell_orders.map(o => ({...o, type: 'sell'})),
        {price: data.current_price, type: 'current', qty: 0},
        ...data.buy_orders.map(o => ({...o, type: 'buy'}))
    ].sort((a, b) => b.price - a.price);

    viz.innerHTML = allOrders.map(order => {
        if (order.type === 'current') {
            return `
                <div class="grid-level current">
                    <div style="flex: 1;">
                        <strong>Current Price: ${formatCurrency(order.price, 4)}</strong>
                    </div>
                </div>
            `;
        }
        
        const className = order.type === 'sell' ? 'sell' : 'buy';
        return `
            <div class="grid-level ${className}">
                <div style="flex: 1;">
                    ${order.type === 'sell' ? '🔴' : '🟢'} 
                    ${formatCurrency(order.price, 4)}
                </div>
                <div>Qty: ${formatNumber(order.qty, 2)}</div>
            </div>
        `;
    }).join('');
}
