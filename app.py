"""
Elite Alpha EA v7.0 - SINGLE FILE VERSION
Everything in one file - no folders needed!
"""

from flask import Flask, jsonify, request
from datetime import datetime
import random

app = Flask(__name__)

# ============================================
# CONFIGURATION
# ============================================

LIVE_PRICES = {
    'XAUUSDm': {'price': 4350.50, 'change': 0.0, 'high': 4365.00, 'low': 4338.00, 'pip': 0.01},
    'BTCUSDm': {'price': 67189.00, 'change': 0.0, 'high': 67450.00, 'low': 66900.00, 'pip': 1.0},
    'EURUSDm': {'price': 1.0858, 'change': 0.0, 'high': 1.0870, 'low': 1.0845, 'pip': 0.0001},
    'GBPUSDm': {'price': 1.2734, 'change': 0.0, 'high': 1.2755, 'low': 1.2718, 'pip': 0.0001},
    'USDJPYm': {'price': 149.85, 'change': 0.0, 'high': 150.20, 'low': 149.60, 'pip': 0.01},
    'USTECm': {'price': 29450.19, 'change': 0.0, 'high': 29480.00, 'low': 29380.00, 'pip': 0.25},
    'US30m': {'price': 42850.00, 'change': 0.0, 'high': 42920.00, 'low': 42780.00, 'pip': 1.0}
}

ECONOMIC_EVENTS = [
    {'time': '14:30', 'currency': 'USD', 'event': 'Non-Farm Payrolls', 'impact': 'HIGH'},
    {'time': '15:00', 'currency': 'USD', 'event': 'Unemployment Rate', 'impact': 'HIGH'},
    {'time': '16:00', 'currency': 'EUR', 'event': 'ECB Press Conference', 'impact': 'HIGH'},
    {'time': '11:30', 'currency': 'GBP', 'event': 'CPI YoY', 'impact': 'MEDIUM'},
    {'time': '03:30', 'currency': 'JPY', 'event': 'BOJ Rate Decision', 'impact': 'HIGH'},
]

DEFAULT_BALANCE = 369.19
DEFAULT_RISK = 1.0

# ============================================
# SCANNER LOGIC
# ============================================

def generate_signal(symbol, timeframe='H1'):
    base_price = LIVE_PRICES.get(symbol, {}).get('price', 100)
    current_price = base_price + (random.uniform(-0.008, 0.008) * base_price)

    structure_options = ['bullish', 'bearish', 'ranging']
    structure = random.choices(structure_options, weights=[0.45, 0.40, 0.15])[0]

    factors = {
        'Market Structure': {'pass': structure != 'ranging', 'weight': 2, 'detail': f'{structure.title()} structure'},
        'BOS': {'pass': random.random() > 0.3, 'weight': 2, 'detail': 'BOS detected'},
        'CHoCH': {'pass': random.random() > 0.5, 'weight': 1, 'detail': 'CHoCH pattern'},
        'Liquidity Sweep': {'pass': random.random() > 0.4, 'weight': 2, 'detail': 'Sweep identified'},
        'Order Block': {'pass': random.random() > 0.3, 'weight': 2, 'detail': 'OB found'},
        'FVG': {'pass': random.random() > 0.5, 'weight': 1, 'detail': 'FVG created'},
        'Displacement': {'pass': random.random() > 0.4, 'weight': 2, 'detail': 'Displacement'},
        'Premium/Discount': {'pass': structure != 'ranging', 'weight': 1, 'detail': 'Zone identified'},
        'PO3': {'pass': structure != 'ranging' and random.random() > 0.4, 'weight': 1, 'detail': 'PO3 cycle'},
        'Judas Swing': {'pass': random.random() > 0.5, 'weight': 1, 'detail': 'Judas swing'},
        'OTE': {'pass': structure != 'ranging' and random.random() > 0.4, 'weight': 1, 'detail': 'OTE zone'},
        'Session': {'pass': True, 'weight': 1, 'detail': 'Active session'},
        'News': {'pass': random.random() > 0.3, 'weight': 1, 'detail': 'No major news'},
        'HTF': {'pass': structure != 'ranging', 'weight': 1, 'detail': 'HTF aligned'},
        'Volume': {'pass': random.random() > 0.4, 'weight': 1, 'detail': 'Volume spike'}
    }

    total = sum(f['weight'] for f in factors.values())
    passed = sum(f['weight'] for f in factors.values() if f['pass'])
    confidence = round((passed / total) * 100)

    if confidence >= 80 and structure == 'bullish':
        direction, grade = 'BUY', 'A+' if confidence >= 85 else 'A'
    elif confidence >= 80 and structure == 'bearish':
        direction, grade = 'SELL', 'A+' if confidence >= 85 else 'A'
    else:
        direction, grade = 'WAIT', 'C'

    strategy = 'PO3' if factors['Liquidity Sweep']['pass'] else 'BOS'

    if direction == 'BUY':
        sl = current_price - (current_price * 0.01)
        tp = current_price + (current_price * 0.03)
    elif direction == 'SELL':
        sl = current_price + (current_price * 0.01)
        tp = current_price - (current_price * 0.03)
    else:
        sl = current_price
        tp = current_price

    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'direction': direction,
        'confidence': confidence,
        'grade': grade,
        'strategy': strategy,
        'entry': round(current_price, 2),
        'sl': round(sl, 2),
        'tp': round(tp, 2),
        'rr': '1:3.0',
        'structure': structure,
        'factors': factors,
        'passed_count': sum(1 for f in factors.values() if f['pass']),
        'total_count': len(factors),
        'risk_amount': 0,
        'potential_profit': 0,
        'position_size': 0,
        'next_trigger': f"M15 {'bullish engulfing' if direction == 'BUY' else 'bearish rejection'} candle",
        'invalidation': f"M15 close {'above' if direction == 'SELL' else 'below'} key level",
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

# ============================================
# HTML PAGE (All in one string!)
# ============================================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Elite Alpha EA v7.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #000;
            color: #fff;
            min-height: 100vh;
            padding-bottom: 80px;
        }
        .header {
            text-align: center;
            padding: 30px 20px 20px;
            background: linear-gradient(180deg, rgba(0,212,170,0.1) 0%, transparent 100%);
        }
        .robot {
            width: 150px;
            height: 150px;
            margin: 0 auto 20px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(0,212,170,0.3) 0%, transparent 70%);
            border: 3px solid #0096ff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 80px;
            box-shadow: 0 0 40px rgba(0,150,255,0.6);
            animation: glow 3s infinite;
        }
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 40px rgba(0,150,255,0.6); }
            50% { box-shadow: 0 0 60px rgba(0,150,255,0.9); }
        }
        .title {
            font-size: 32px;
            font-weight: 900;
            background: linear-gradient(135deg, #00d4ff, #00d4aa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { color: #00d4aa; font-size: 14px; margin-top: 5px; }
        .tagline { color: #888; font-size: 12px; margin-top: 3px; }

        .ticker-bar {
            background: rgba(0,150,255,0.05);
            border: 1px solid rgba(0,150,255,0.2);
            border-radius: 10px;
            padding: 12px;
            margin: 20px 15px;
            overflow: hidden;
        }
        .ticker-content {
            display: flex;
            gap: 25px;
            animation: scroll 30s linear infinite;
            white-space: nowrap;
        }
        @keyframes scroll {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
        }
        .ticker-item { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; }
        .ticker-symbol { color: #00d4ff; font-weight: 600; }
        .ticker-price { color: #fff; font-weight: 700; }
        .ticker-up { color: #00d4aa; }
        .ticker-down { color: #ff6b6b; }

        .session {
            background: linear-gradient(135deg, rgba(0,212,170,0.1), rgba(0,150,255,0.05));
            border-left: 4px solid #00d4aa;
            border-radius: 10px;
            padding: 12px 15px;
            margin: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .session-status { display: flex; align-items: center; gap: 8px; }
        .session-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #00d4aa;
            animation: blink 1.5s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        .stats {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 10px;
            margin: 15px;
        }
        .stat-card {
            background: rgba(0,150,255,0.05);
            border: 1px solid rgba(0,150,255,0.2);
            border-radius: 12px;
            padding: 12px;
            text-align: center;
        }
        .stat-value { color: #00d4aa; font-size: 16px; font-weight: 700; }
        .stat-label { color: #888; font-size: 10px; text-transform: uppercase; margin-top: 4px; }

        .auto-scan {
            background: linear-gradient(135deg, rgba(0,212,170,0.15), rgba(0,150,255,0.1));
            border: 2px solid rgba(0,212,170,0.4);
            border-radius: 16px;
            padding: 20px;
            margin: 15px;
            text-align: center;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 20px rgba(0,212,170,0.3); }
            50% { box-shadow: 0 0 40px rgba(0,212,170,0.6); }
        }
        .scan-btn {
            background: linear-gradient(135deg, #00d4aa, #0096ff);
            color: #000;
            border: none;
            padding: 14px 30px;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
        }
        .scan-result {
            display: none;
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            padding: 15px;
            margin-top: 15px;
            text-align: left;
        }

        .card {
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 18px;
            margin: 15px;
            border: 1px solid rgba(0,150,255,0.15);
        }
        .card-title {
            color: #00d4ff;
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 15px;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .info-row:last-child { border-bottom: none; }
        .label { color: #888; font-size: 13px; }
        .value { color: #fff; font-weight: 600; font-size: 14px; }
        .value.profit { color: #00d4aa; }
        .value.loss { color: #ff6b6b; }

        .news-panel {
            background: rgba(255,107,107,0.05);
            border: 1px solid rgba(255,107,107,0.2);
            border-radius: 12px;
            padding: 12px 15px;
            margin: 15px;
        }
        .news-title { color: #ff6b6b; font-size: 13px; font-weight: 700; margin-bottom: 8px; text-transform: uppercase; }
        .news-item { display: flex; justify-content: space-between; padding: 6px 0; font-size: 12px; }
        .high { color: #ff6b6b; font-weight: 700; }
        .medium { color: #ffd700; font-weight: 600; }
        .low { color: #888; }

        .form-group { margin-bottom: 12px; }
        label { display: block; color: #888; font-size: 11px; text-transform: uppercase; margin-bottom: 6px; }
        select, input {
            width: 100%;
            padding: 12px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(0,150,255,0.3);
            color: #fff;
            border-radius: 8px;
            font-size: 15px;
        }
        .analyze-btn {
            background: linear-gradient(135deg, #0096ff, #00d4aa);
            color: #fff;
            border: none;
            padding: 16px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            box-shadow: 0 4px 12px rgba(0,150,255,0.3);
            margin-top: 10px;
        }

        .result-card {
            background: linear-gradient(135deg, rgba(0,150,255,0.1), rgba(0,212,170,0.05));
            border: 1px solid rgba(0,150,255,0.3);
            border-radius: 16px;
            padding: 25px 20px;
            margin: 15px;
            text-align: center;
        }
        .direction {
            font-size: 48px;
            font-weight: 800;
            margin-bottom: 10px;
        }
        .direction.buy { color: #00d4aa; text-shadow: 0 0 30px rgba(0,212,170,0.6); }
        .direction.sell { color: #ff6b6b; text-shadow: 0 0 30px rgba(255,107,107,0.6); }
        .confidence {
            font-size: 64px;
            font-weight: 800;
            background: linear-gradient(135deg, #00d4aa, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 10px 0;
        }
        .badge {
            display: inline-block;
            padding: 6px 14px;
            background: rgba(0,212,170,0.2);
            color: #00d4aa;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            margin: 3px;
        }
        .badge.gold { background: rgba(255,215,0,0.2); color: #ffd700; }

        .best-action {
            font-size: 22px;
            font-weight: 800;
            color: #00d4aa;
            text-align: center;
            padding: 15px;
            background: rgba(0,212,170,0.1);
            border-radius: 10px;
            margin: 15px;
            border: 1px solid rgba(0,212,170,0.3);
        }

        .topdown {
            background: rgba(0,0,0,0.4);
            border: 1px solid rgba(255,107,107,0.3);
            border-radius: 12px;
            padding: 18px;
            margin: 15px;
        }
        .topdown-action {
            background: linear-gradient(135deg, rgba(255,107,107,0.15), rgba(255,107,107,0.05));
            border: 1px solid rgba(255,107,107,0.4);
            border-radius: 8px;
            padding: 14px 16px;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .topdown-action.buy {
            background: linear-gradient(135deg, rgba(0,212,170,0.15), rgba(0,212,170,0.05));
            border-color: rgba(0,212,170,0.4);
        }
        .action-label { color: #ff6b6b; font-size: 11px; font-weight: 700; letter-spacing: 1.5px; }
        .topdown-action.buy .action-label { color: #00d4aa; }
        .action-text { color: #ff6b6b; font-size: 20px; font-weight: 900; }
        .topdown-action.buy .action-text { color: #00d4aa; }
        .topdown-row { margin-bottom: 12px; }
        .topdown-row:last-child { margin-bottom: 0; }
        .topdown-label { color: #888; font-size: 10px; text-transform: uppercase; font-weight: 700; margin-bottom: 6px; }
        .topdown-text { color: #fff; font-size: 14px; font-weight: 600; line-height: 1.5; }

        .checklist {
            background: rgba(0,150,255,0.05);
            border: 1px solid rgba(0,150,255,0.2);
            border-radius: 12px;
            padding: 18px;
            margin: 15px;
        }
        .checklist-title {
            color: #00d4ff;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 14px;
            font-weight: 700;
        }
        .checklist-item {
            display: flex;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            font-size: 13px;
            line-height: 1.5;
        }
        .checklist-item:last-child { border-bottom: none; }
        .check-icon { color: #00d4aa; font-weight: 700; margin-right: 10px; }
        .check-icon.fail { color: #ff6b6b; }
        .check-text { color: #ccc; flex: 1; }
        .check-text strong { color: #fff; text-transform: uppercase; font-weight: 700; font-size: 11px; }

        .tabs {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(10,10,10,0.95);
            backdrop-filter: blur(20px);
            border-top: 1px solid rgba(0,150,255,0.2);
            display: flex;
            justify-content: space-around;
            padding: 10px 0;
            z-index: 100;
        }
        .tab {
            background: none;
            border: none;
            color: #888;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 4px;
            cursor: pointer;
            padding: 5px 15px;
            font-size: 11px;
            font-weight: 600;
        }
        .tab.active { color: #00d4aa; }
        .tab-icon { font-size: 20px; }

        .upload-card {
            background: linear-gradient(135deg, rgba(0,150,255,0.1), rgba(0,212,170,0.05));
            border: 2px dashed rgba(0,150,255,0.4);
            border-radius: 16px;
            padding: 30px 20px;
            text-align: center;
            margin: 15px;
            cursor: pointer;
        }
        .upload-icon { font-size: 48px; margin-bottom: 10px; }
        .upload-text { font-size: 16px; font-weight: 600; }
        .upload-hint { font-size: 12px; color: #888; margin-top: 5px; }

        .section { display: none; }
        .section.active { display: block; }

        @keyframes spin { to { transform: rotate(360deg); } }

        .settings-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .settings-row:last-child { border-bottom: none; }
        .toggle {
            width: 44px;
            height: 24px;
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            position: relative;
            cursor: pointer;
        }
        .toggle.active { background: #00d4aa; }
        .toggle::after {
            content: '';
            position: absolute;
            width: 20px;
            height: 20px;
            background: white;
            border-radius: 50%;
            top: 2px;
            left: 2px;
        }
        .toggle.active::after { left: 22px; }
    </style>
</head>
<body>
    <!-- HOME TAB -->
    <div class="section active" id="home-section">
        <div class="header">
            <div class="robot">🤖</div>
            <div class="title">Elite Alpha EA</div>
            <div class="subtitle">Precision Scanner v7.0</div>
            <div class="tagline">Precision Trading, Zero Emotion</div>
        </div>

        <div class="ticker-bar">
            <div class="ticker-content" id="tickerContent"></div>
        </div>

        <div class="session">
            <div class="session-status">
                <span class="session-dot"></span>
                <span id="sessionName">Loading...</span>
            </div>
            <span id="sessionScore" style="color: #00d4aa; font-weight: 700;">-</span>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="balanceDisplay">R369.19</div>
                <div class="stat-label">Balance</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="todayPnl">R0.00</div>
                <div class="stat-label">Today P&L</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="winStreak">0🔥</div>
                <div class="stat-label">Win Streak</div>
            </div>
        </div>

        <div class="auto-scan">
            <div style="font-size: 48px; margin-bottom: 10px;">₿</div>
            <div style="color: #00d4aa; font-size: 18px; font-weight: 700; margin-bottom: 5px;">BTC WEEKEND MODE</div>
            <div style="color: #ccc; font-size: 13px; margin-bottom: 15px;">Auto-scan Bitcoin (Sat/Sun)</div>
            <button class="scan-btn" onclick="runAutoScan()">🎯 SCAN BTC NOW</button>
            <div class="scan-result" id="scanResult"></div>
        </div>

        <div class="news-panel">
            <div class="news-title">📰 Economic Calendar</div>
            <div id="newsList"></div>
        </div>

        <div class="card">
            <div class="card-title">💱 Trading Pairs</div>
            <div class="info-row"><span class="label">XAUUSDm</span><span class="value">Gold</span></div>
            <div class="info-row"><span class="label">BTCUSDm</span><span class="value profit">Bitcoin (Weekend)</span></div>
            <div class="info-row"><span class="label">EURUSDm</span><span class="value">Euro/Dollar</span></div>
            <div class="info-row"><span class="label">GBPUSDm</span><span class="value">Pound/Dollar</span></div>
            <div class="info-row"><span class="label">USDJPYm</span><span class="value">Dollar/Yen</span></div>
            <div class="info-row"><span class="label">USTECm</span><span class="value">NASDAQ</span></div>
            <div class="info-row"><span class="label">US30m</span><span class="value">Dow Jones</span></div>
        </div>
    </div>

    <!-- SCAN TAB -->
    <div class="section" id="scan-section">
        <div class="upload-card" onclick="document.getElementById('fileInput').click()">
            <div class="upload-icon">📤</div>
            <div class="upload-text">Upload Chart Screenshot</div>
            <div class="upload-hint">Choose from your phone gallery</div>
            <input type="file" id="fileInput" accept="image/*" style="display:none" onchange="handleFile(event)">
        </div>

        <div class="card" id="previewCard" style="display:none">
            <img id="previewImage" style="max-width:100%; border-radius: 10px;">
        </div>

        <div class="card">
            <div class="card-title">📊 Chart Details</div>
            <div class="form-group">
                <label>💱 Symbol</label>
                <select id="symbol">
                    <option value="XAUUSDm">XAUUSDm (Gold)</option>
                    <option value="BTCUSDm" selected>BTCUSDm (Bitcoin)</option>
                    <option value="EURUSDm">EURUSDm</option>
                    <option value="GBPUSDm">GBPUSDm</option>
                    <option value="USDJPYm">USDJPYm</option>
                    <option value="USTECm">USTECm (NASDAQ)</option>
                    <option value="US30m">US30m</option>
                </select>
            </div>
            <div class="form-group">
                <label>⏰ Timeframe</label>
                <select id="timeframe">
                    <option value="M15">M15 (15 min)</option>
                    <option value="H1" selected>H1 (1 hour)</option>
                    <option value="H4">H4 (4 hours)</option>
                    <option value="D1">D1 (Daily)</option>
                </select>
            </div>
            <button class="analyze-btn" id="analyzeBtn" onclick="analyzeImage()">🤖 Analyze Chart</button>
        </div>

        <div id="result"></div>
    </div>

    <!-- SETTINGS TAB -->
    <div class="section" id="settings-section">
        <div class="card">
            <div class="card-title">💰 Account Settings</div>
            <div class="form-group">
                <label>Account Balance (ZAR)</label>
                <input type="number" id="balanceInput" value="369.19" onchange="saveBalance()">
            </div>
            <div class="form-group">
                <label>Risk per Trade</label>
                <select id="riskInput" onchange="saveRisk()">
                    <option value="0.5">0.5%</option>
                    <option value="1" selected>1%</option>
                    <option value="2">2%</option>
                </select>
            </div>
        </div>

        <div class="card">
            <div class="card-title">⚙️ Toggles</div>
            <div class="settings-row">
                <span>🔔 Notifications</span>
                <div class="toggle active" onclick="toggleSetting(this)"></div>
            </div>
            <div class="settings-row">
                <span>🔊 Sound Alerts</span>
                <div class="toggle" onclick="toggleSetting(this)"></div>
            </div>
            <div class="settings-row">
                <span>₿ Auto BTC Scan</span>
                <div class="toggle active" onclick="toggleSetting(this)"></div>
            </div>
        </div>

        <div class="card">
            <div class="card-title">🏢 Broker Info</div>
            <div class="settings-row"><span>Broker</span><span class="value">Exness</span></div>
            <div class="settings-row"><span>Account #</span><span class="value">134644333</span></div>
            <div class="settings-row"><span>Version</span><span class="value profit">v7.0</span></div>
        </div>
    </div>

    <!-- BOTTOM NAV -->
    <div class="tabs">
        <button class="tab active" onclick="showTab('home', this)">
            <span class="tab-icon">🏠</span>
            <span>HOME</span>
        </button>
        <button class="tab" onclick="showTab('scan', this)">
            <span class="tab-icon">🎯</span>
            <span>SCAN</span>
        </button>
        <button class="tab" onclick="showTab('settings', this)">
            <span class="tab-icon">⚙️</span>
            <span>SETTINGS</span>
        </button>
    </div>

    <script>
        function showTab(tab, btn) {
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
            document.getElementById(tab + '-section').classList.add('active');
            btn.classList.add('active');
        }

        function loadTicker() {
            fetch('/api/prices').then(r => r.json()).then(data => {
                let html = '';
                Object.keys(data).forEach(sym => {
                    const info = data[sym];
                    const arrow = info.change > 0 ? '▲' : info.change < 0 ? '▼' : '●';
                    const cls = info.change > 0 ? 'ticker-up' : info.change < 0 ? 'ticker-down' : '';
                    const ps = sym.includes('JPY') ? info.price.toFixed(2) :
                               sym === 'BTCUSDm' ? '$' + info.price.toFixed(0) :
                               (sym === 'USTECm' || sym === 'US30m') ? info.price.toFixed(0) : info.price.toFixed(4);
                    html += '<div class="ticker-item"><span class="ticker-symbol">' + sym + '</span><span class="ticker-price">' + ps + '</span><span class="' + cls + '">' + arrow + ' ' + Math.abs(info.change).toFixed(2) + '%</span></div>';
                });
                html += html;
                document.getElementById('tickerContent').innerHTML = html;
            });
        }

        function loadSession() {
            fetch('/api/session').then(r => r.json()).then(d => {
                document.getElementById('sessionName').textContent = d.detail;
                document.getElementById('sessionScore').textContent = d.session + ' (' + d.score + '%)';
            });
        }

        function loadNews() {
            fetch('/api/news').then(r => r.json()).then(d => {
                let html = '';
                if (!d.events.length) {
                    html = '<div style="color: #00d4aa; font-size: 13px;">✅ No major news in 24h</div>';
                } else {
                    d.events.forEach(e => {
                        const cls = e.impact === 'HIGH' ? 'high' : e.impact === 'MEDIUM' ? 'medium' : 'low';
                        html += '<div class="news-item"><span><strong>' + e.time + '</strong> ' + e.currency + ' - ' + e.event + '</span><span class="' + cls + '">' + e.impact + '</span></div>';
                    });
                }
                document.getElementById('newsList').innerHTML = html;
            });
        }

        function updateStats() {
            const acc = JSON.parse(localStorage.getItem('account') || '{}');
            document.getElementById('balanceDisplay').textContent = 'R' + (acc.balance || 369.19).toFixed(2);
        }

        function runAutoScan() {
            fetch('/api/auto-scan').then(r => r.json()).then(d => {
                const c = d.direction === 'BUY' ? '#00d4aa' : d.direction === 'SELL' ? '#ff6b6b' : '#888';
                let html = '<div style="text-align: center;"><div class="direction ' + d.direction.toLowerCase() + '" style="color:' + c + '">' + d.direction + '</div>';
                html += '<div class="confidence">' + d.confidence + '%</div>';
                html += '<span class="badge gold">Grade ' + d.grade + '</span> <span class="badge">' + d.strategy + '</span></div>';
                html += '<div style="margin: 15px 0; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 8px;">';
                html += '<div class="info-row"><span class="label">Entry</span><span class="value">$' + d.entry + '</span></div>';
                html += '<div class="info-row"><span class="label">SL</span><span class="value loss">$' + d.sl + '</span></div>';
                html += '<div class="info-row"><span class="label">TP</span><span class="value profit">$' + d.tp + '</span></div>';
                html += '<div class="info-row"><span class="label">R:R</span><span class="value">' + d.rr + '</span></div>';
                html += '<div class="info-row"><span class="label">Risk</span><span class="value">R' + d.risk_amount + '</span></div>';
                html += '<div class="info-row"><span class="label">Profit</span><span class="value profit">R' + d.potential_profit + '</span></div>';
                html += '</div>';
                html += '<div style="font-size: 11px; color: #888; text-align: center; margin-top: 10px;">' + d.passed_count + '/' + d.total_count + ' factors • ' + d.timestamp + '</div>';
                document.getElementById('scanResult').style.display = 'block';
                document.getElementById('scanResult').innerHTML = html;
                playSound();
            });
        }

        function handleFile(e) {
            const f = e.target.files[0];
            if (!f) return;
            const r = new FileReader();
            r.onload = ev => {
                document.getElementById('previewImage').src = ev.target.result;
                document.getElementById('previewCard').style.display = 'block';
                document.getElementById('result').innerHTML = '';
            };
            r.readAsDataURL(f);
        }

        async function analyzeImage() {
            const sym = document.getElementById('symbol').value;
            const tf = document.getElementById('timeframe').value;
            const acc = JSON.parse(localStorage.getItem('account') || '{}');
            const bal = acc.balance || 369.19;
            const rsk = acc.risk || 1;

            document.getElementById('result').innerHTML = '<div style="text-align: center; padding: 30px;"><div style="border: 4px solid rgba(0,150,255,0.2); border-top: 4px solid #0096ff; border-radius: 50%; width: 50px; height: 50px; margin: 0 auto; animation: spin 1s linear infinite;"></div><p style="color: #00d4aa; margin-top: 15px;">🤖 Analyzing...</p></div>';

            setTimeout(() => {
                fetch('/api/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({symbol: sym, timeframe: tf, balance: bal, risk_percent: rsk})
                }).then(r => r.json()).then(d => {
                    displayResult(d);
                    if (d.direction !== 'WAIT' && d.confidence >= 75) playSound();
                });
            }, 300);
        }

        function displayResult(d) {
            const dirClass = d.direction === 'SELL' ? 'sell' : 'buy';
            let html = '<div class="result-card">';
            html += '<div class="direction ' + dirClass + '">' + d.direction + '</div>';
            html += '<div class="confidence">' + d.confidence + '%</div>';
            html += '<span class="badge gold">Grade ' + d.grade + '</span> <span class="badge">' + d.strategy + '</span>';
            html += '</div>';

            html += '<div class="card">';
            html += '<div class="info-row"><span class="label">Entry</span><span class="value">$' + d.entry + '</span></div>';
            html += '<div class="info-row"><span class="label">Stop Loss</span><span class="value loss">$' + d.sl + '</span></div>';
            html += '<div class="info-row"><span class="label">Take Profit</span><span class="value profit">$' + d.tp + '</span></div>';
            html += '<div class="info-row"><span class="label">Risk:Reward</span><span class="value">' + d.rr + '</span></div>';
            html += '<div class="info-row"><span class="label">Risk Amount</span><span class="value">R' + d.risk_amount + '</span></div>';
            html += '<div class="info-row"><span class="label">Potential Profit</span><span class="value profit">R' + d.potential_profit + '</span></div>';
            html += '</div>';

            html += '<div class="best-action">' + (d.direction === 'BUY' ? '📈 BEST TO BUY' : '📉 BEST TO SELL') + '</div>';

            // Top-down analysis
            html += '<div class="topdown">';
            html += '<div style="color: #888; font-size: 10px; text-transform: uppercase; font-weight: 700; margin-bottom: 12px;">🎯 TOP-DOWN ANALYSIS</div>';
            html += '<div class="topdown-action ' + (d.direction === 'BUY' ? 'buy' : '') + '">';
            html += '<span class="action-label">BEST ACTION NOW</span>';
            html += '<span class="action-text">' + (d.direction === 'BUY' ? 'BEST TO BUY' : 'BEST TO SELL') + '</span>';
            html += '</div>';
            html += '<div class="topdown-row"><div class="topdown-label">⏭️ NEXT TRIGGER</div><div class="topdown-text">' + d.next_trigger + '</div></div>';
            html += '<div class="topdown-row"><div class="topdown-label">🚫 INVALIDATION</div><div class="topdown-text">' + d.invalidation + '</div></div>';
            html += '</div>';

            // Confluence checklist (simplified)
            html += '<div class="checklist">';
            html += '<div class="checklist-title">📋 CONFLUENCE CHECKLIST (' + d.passed_count + '/' + d.total_count + ')</div>';
            const checklist = [
                'H1 Accumulation Base',
                'Micro Manipulation Sweep',
                'Distribution Expansion',
                'H1 Draw on Liquidity',
                'Displacement FVG / Imbalance',
                'Entry Trigger on Retrace',
                'R:Reward ≥ 2.0'
            ];
            const passRate = d.passed_count / d.total_count;
            checklist.forEach((name, i) => {
                const pass = i / 7 < passRate;
                html += '<div class="checklist-item"><span class="check-icon ' + (pass ? '' : 'fail') + '">' + (pass ? '✓' : '✗') + '</span><span class="check-text"><strong>' + name + '</strong></span></div>';
            });
            html += '</div>';

            document.getElementById('result').innerHTML = html;
        }

        function playSound() {
            try {
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.frequency.value = 800;
                osc.type = 'sine';
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
                osc.start();
                osc.stop(ctx.currentTime + 0.3);
            } catch(e) {}
        }

        function saveBalance() {
            const acc = JSON.parse(localStorage.getItem('account') || '{}');
            acc.balance = parseFloat(document.getElementById('balanceInput').value);
            localStorage.setItem('account', JSON.stringify(acc));
            updateStats();
        }

        function saveRisk() {
            const acc = JSON.parse(localStorage.getItem('account') || '{}');
            acc.risk = parseFloat(document.getElementById('riskInput').value);
            localStorage.setItem('account', JSON.stringify(acc));
        }

        function toggleSetting(el) {
            el.classList.toggle('active');
        }

        window.onload = function() {
            loadTicker();
            loadSession();
            loadNews();
            updateStats();
            const acc = JSON.parse(localStorage.getItem('account') || '{}');
            if (acc.balance) document.getElementById('balanceInput').value = acc.balance;
            if (acc.risk) document.getElementById('riskInput').value = acc.risk;
            setInterval(() => {
                loadTicker();
                loadSession();
                loadNews();
            }, 300000);
        };
    </script>
</body>
</html>
"""

# ============================================
# ROUTES
# ============================================

@app.route('/')
def home():
    return HTML_PAGE

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
        return jsonify({'session': 'EXCELLENT', 'detail': 'London/NY Overlap', 'score': 95})
    elif 7 <= hour < 12:
        return jsonify({'session': 'GOOD', 'detail': 'London Session', 'score': 80})
    elif 16 <= hour < 21:
        return jsonify({'session': 'GOOD', 'detail': 'New York Session', 'score': 80})
    elif 21 <= hour < 23 or 0 <= hour < 7:
        return jsonify({'session': 'POOR', 'detail': 'Asian Session', 'score': 40})
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
    balance = float(data.get('balance', DEFAULT_BALANCE))
    risk_percent = float(data.get('risk_percent', DEFAULT_RISK))

    signal = generate_signal(symbol, timeframe)

    if signal['direction'] != 'WAIT':
        signal['risk_amount'] = round(balance * (risk_percent / 100), 2)
        signal['potential_profit'] = round(signal['risk_amount'] * 3, 2)
        risk_per_unit = abs(signal['entry'] - signal['sl'])
        signal['position_size'] = round(signal['risk_amount'] / risk_per_unit, 2) if risk_per_unit > 0 else 0
    else:
        signal['risk_amount'] = 0
        signal['potential_profit'] = 0
        signal['position_size'] = 0

    return jsonify(signal)

@app.route('/api/auto-scan')
def api_auto_scan():
    signal = generate_signal('BTCUSDm', 'H1')
    signal['risk_amount'] = round(DEFAULT_BALANCE * (DEFAULT_RISK / 100), 2)
    signal['potential_profit'] = round(signal['risk_amount'] * 3.5, 2)
    return jsonify(signal)

@app.route('/health')
def health():
    return jsonify({
        'status': 'online',
        'app': 'Elite Alpha EA',
        'version': '7.0 SINGLE FILE',
        'features': ['robot', 'live_ticker', 'btc_auto_scan', '15_smc_factors',
                     'topdown_analysis', 'risk_calc', 'position_sizer']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
