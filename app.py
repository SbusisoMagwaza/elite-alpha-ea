"""
Elite Alpha EA - Professional Trading Robot
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime
import random

from config import LIVE_PRICES, ECONOMIC_EVENTS, DEFAULT_ACCOUNT, SCANNER_CONFIG
from scanner.smc_analyzer import generate_signal, calculate_position_size, calculate_risk_reward
from scanner.confluence import generate_confluence_checklist, generate_confluences_list
from scanner.topdown import generate_topdown_analysis

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/scan')
def scan():
    return render_template('scan.html')


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/api/prices')
def api_prices():
    prices = {}
    for symbol, data in LIVE_PRICES.items():
        change_pct = random.uniform(-2.5, 2.5)
        new_price = data['price'] * (1 + change_pct / 100)
        prices[symbol] = {
            'price': round(new_price, 4),
            'change': round(change_pct, 2),
            'high': data['high'],
            'low': data['low']
        }
    return jsonify(prices)


@app.route('/api/session')
def api_session():
    hour = datetime.utcnow().hour
    if 12 <= hour < 16:
        return jsonify({'session': 'EXCELLENT', 'detail': 'London/NY Overlap (Best Time!)', 'score': 95})
    elif 7 <= hour < 12:
        return jsonify({'session': 'GOOD', 'detail': 'London Session', 'score': 80})
    elif 16 <= hour < 21:
        return jsonify({'session': 'GOOD', 'detail': 'New York Session', 'score': 80})
    elif 21 <= hour < 23 or 0 <= hour < 7:
        return jsonify({'session': 'POOR', 'detail': 'Asian Session (Low Volatility)', 'score': 40})
    else:
        return jsonify({'session': 'FAIR', 'detail': 'Session Transition', 'score': 60})


@app.route('/api/news')
def api_news():
    current_hour = datetime.now().hour
    upcoming = []
    for event in ECONOMIC_EVENTS:
        event_hour = int(event['time'].split(':')[0])
        if 0 <= (event_hour - current_hour) % 24 <= 24:
            upcoming.append(event)
    return jsonify({'events': upcoming[:5]})


@app.route('/api/scan', methods=['POST'])
def api_scan():
    data = request.get_json() or {}
    symbol = data.get('symbol', 'BTCUSDm')
    timeframe = data.get('timeframe', 'H1')
    balance = float(data.get('balance', DEFAULT_ACCOUNT['balance']))
    risk_percent = float(data.get('risk_percent', DEFAULT_ACCOUNT['risk_percent']))

    signal = generate_signal(symbol, timeframe)
    signal['confluence_checklist'] = generate_confluence_checklist(signal)
    signal['confluences'] = generate_confluences_list(signal)
    signal['topdown'] = generate_topdown_analysis(signal)

    if signal['direction'] != 'WAIT':
        signal['risk_amount'] = round(balance * (risk_percent / 100), 2)
        signal['potential_profit'] = round(signal['risk_amount'] * 3, 2)
        signal['position_size'] = round(calculate_position_size(balance, risk_percent, signal['entry'], signal['sl']), 2)
    else:
        signal['risk_amount'] = 0
        signal['potential_profit'] = 0
        signal['position_size'] = 0

    return jsonify(signal)


@app.route('/api/auto-scan')
def api_auto_scan():
    signal = generate_signal('BTCUSDm', 'H1')
    signal['confluence_checklist'] = generate_confluence_checklist(signal)
    signal['confluences'] = generate_confluences_list(signal)
    signal['topdown'] = generate_topdown_analysis(signal)

    balance = DEFAULT_ACCOUNT['balance']
    risk_percent = DEFAULT_ACCOUNT['risk_percent']
    signal['risk_amount'] = round(balance * (risk_percent / 100), 2)
    signal['potential_profit'] = round(signal['risk_amount'] * 3.5, 2)

    return jsonify(signal)


@app.route('/health')
def health():
    return jsonify({
        'status': 'online',
        'app': 'Elite Alpha EA',
        'version': '7.0 PROFESSIONAL',
        'features': ['robot_image', 'live_ticker', 'session_indicator', 'btc_auto_scan', 'economic_calendar', '15_smc_factors', 'confluence_checklist', 'topdown_analysis', 'real_prices', 'risk_calculator', 'position_sizer', 'scan_history', 'daily_pnl', 'win_streak', 'sound_alerts', 'editable_settings']
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
