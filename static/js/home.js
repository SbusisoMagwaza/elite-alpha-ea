function loadTicker() {
    fetch('/api/prices')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var html = '';
            Object.keys(data).forEach(function(symbol) {
                var info = data[symbol];
                var arrow = info.change > 0 ? '▲' : info.change < 0 ? '▼' : '●';
                var cls = info.change > 0 ? 'ticker-up' : info.change < 0 ? 'ticker-down' : '';
                var priceStr = symbol.indexOf('JPY') !== -1 ? info.price.toFixed(2) :
                               symbol === 'BTCUSDm' ? '$' + info.price.toFixed(0) :
                               (symbol === 'USTECm' || symbol === 'US30m') ? info.price.toFixed(0) :
                               info.price.toFixed(4);
                html += '<div class="ticker-item">' +
                    '<span class="ticker-symbol">' + symbol + '</span>' +
                    '<span class="ticker-price">' + priceStr + '</span>' +
                    '<span class="' + cls + '">' + arrow + ' ' + Math.abs(info.change).toFixed(2) + '%</span>' +
                    '</div>';
            });
            html += html;
            document.getElementById('tickerContent').innerHTML = html;
        });
}

function loadSession() {
    fetch('/api/session')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            document.getElementById('sessionName').textContent = data.detail;
            document.getElementById('sessionScore').textContent = data.session + ' (' + data.score + '%)';
        });
}

function loadNews() {
    fetch('/api/news')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var html = '';
            if (data.events.length === 0) {
                html = '<div style="color: #00d4aa; font-size: 13px;">✅ No major news in next 24h</div>';
            } else {
                data.events.forEach(function(event) {
                    var cls = event.impact === 'HIGH' ? 'news-impact-high' :
                               event.impact === 'MEDIUM' ? 'news-impact-medium' : 'news-impact-low';
                    html += '<div class="news-item">' +
                        '<span><strong>' + event.time + '</strong> ' + event.currency + ' - ' + event.event + '</span>' +
                        '<span class="' + cls + '">' + event.impact + '</span>' +
                        '</div>';
                });
            }
            document.getElementById('newsList').innerHTML = html;
        });
}

function updateAccountStats() {
    var account = JSON.parse(localStorage.getItem('accountData') || '{}');
    document.getElementById('accountBalance').textContent = 'R' + (account.balance || 369.19).toFixed(2);

    var today = new Date().toDateString();
    var trades = JSON.parse(localStorage.getItem('tradeHistory') || '[]');
    var todayPnl = trades
        .filter(function(t) { return new Date(t.time).toDateString() === today; })
        .reduce(function(sum, t) { return sum + t.pnl; }, 0);

    var todayEl = document.getElementById('todayPnl');
    todayEl.textContent = (todayPnl >= 0 ? '+' : '') + 'R' + todayPnl.toFixed(2);
    todayEl.style.color = todayPnl >= 0 ? '#00d4aa' : '#ff6b6b';

    var recentTrades = trades.slice(-5).reverse();
    var streak = 0;
    for (var i = 0; i < recentTrades.length; i++) {
        if (recentTrades[i].result === 'WIN') streak++;
        else break;
    }
    document.getElementById('winStreak').textContent = streak + '🔥';
}

function runAutoScan() {
    var resultDiv = document.getElementById('autoScanResult');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<div style="text-align: center;"><div class="spinner" style="margin: 10px auto;"></div><p style="color: #00d4aa;">Scanning BTC...</p></div>';

    fetch('/api/auto-scan')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            var dirColor = data.direction === 'BUY' ? '#00d4aa' : data.direction === 'SELL' ? '#ff6b6b' : '#888';
            var html = '<div style="text-align: center; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 10px; margin-bottom: 10px;">' +
                '<div style="font-size: 36px; font-weight: 800; color: ' + dirColor + ';">' + data.direction + '</div>' +
                '<div style="font-size: 48px; font-weight: 800; color: #00d4aa; margin: 8px 0;">' + data.confidence + '%</div>' +
                '<span class="badge gold">Grade ' + data.grade + '</span> ' +
                '<span class="badge">' + data.strategy + '</span></div>' +
                '<div style="background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; margin-bottom: 10px;">' +
                '<div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">Entry:</span><span style="color: #fff; font-weight: 700;">$' + data.entry + '</span></div>' +
                '<div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">SL:</span><span style="color: #ff6b6b; font-weight: 700;">$' + data.sl + '</span></div>' +
                '<div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">TP:</span><span style="color: #00d4aa; font-weight: 700;">$' + data.tp + '</span></div>' +
                '<div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">R:R:</span><span style="color: #00d4ff; font-weight: 700;">' + data.rr + '</span></div>' +
                '<div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">Risk:</span><span style="color: #ffd700; font-weight: 700;">R' + data.risk_amount + '</span></div>' +
                '<div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">Profit:</span><span style="color: #00d4aa; font-weight: 700;">R' + data.potential_profit + '</span></div>' +
                '</div>' +
                '<div style="background: rgba(0, 212, 170, 0.1); padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px;">' +
                '<div style="color: #00d4aa; font-weight: 700;">' + (data.direction === 'WAIT' ? '⏳ WAIT' : '📈 ' + data.topdown.best_action) + '</div></div>';

            html += '<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.1);">';
            html += '<div style="color: #00d4ff; font-size: 11px; font-weight: 700; margin-bottom: 8px;">📋 FACTORS (' + data.passed_count + '/' + data.total_count + ')</div>';
            Object.keys(data.factors).forEach(function(name) {
                var info = data.factors[name];
                var icon = info.pass ? '✓' : '✗';
                var color = info.pass ? '#00d4aa' : '#555';
                html += '<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px;"><span style="color: ' + color + ';">' + icon + ' ' + name + '</span></div>';
            });
            html += '</div>';

            html += '<div style="margin-top: 10px; font-size: 11px; color: #888; text-align: center;">Scanned: ' + data.timestamp + '</div>';
            resultDiv.innerHTML = html;
            resultDiv.scrollIntoView({behavior: 'smooth'});
            playSound();
        });
}

document.addEventListener('DOMContentLoaded', function() {
    loadTicker();
    loadSession();
    loadNews();
    updateAccountStats();
    setInterval(function() {
        loadTicker();
        loadSession();
        loadNews();
        updateAccountStats();
    }, 300000);
});
