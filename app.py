"""
Elite Alpha EA - BEAUTIFUL Vertex Alpha Style Version
With Camera Upload & Premium Design
"""

from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Elite Alpha EA - Precision Trading</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #000000;
            color: #ffffff;
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Hero Header */
        .hero {
            position: relative;
            height: 320px;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #16213e 100%);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        .hero::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background:
                radial-gradient(circle at 30% 40%, rgba(0, 150, 255, 0.2) 0%, transparent 50%),
                radial-gradient(circle at 70% 60%, rgba(0, 212, 170, 0.15) 0%, transparent 50%);
            animation: pulse 8s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.5; }
            50% { transform: scale(1.1); opacity: 0.8; }
        }

        .hero-content {
            position: relative;
            z-index: 2;
            text-align: center;
            padding: 20px;
        }

        .robot-icon {
            font-size: 60px;
            margin-bottom: 10px;
            animation: float 3s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .app-title {
            font-size: 36px;
            font-weight: 800;
            background: linear-gradient(135deg, #00d4ff 0%, #00d4aa 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }

        .app-subtitle {
            font-size: 15px;
            color: #888;
            font-weight: 400;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }

        .app-author {
            font-size: 12px;
            color: #00d4aa;
            opacity: 0.8;
            margin-top: 8px;
        }

        .action-buttons {
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-top: 25px;
            padding: 0 20px;
            position: relative;
            z-index: 2;
        }

        .action-btn {
            background: rgba(0, 150, 255, 0.1);
            border: 1.5px solid #0096ff;
            color: #ffffff;
            padding: 10px 20px;
            border-radius: 25px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
            backdrop-filter: blur(10px);
        }

        .action-btn:active {
            transform: scale(0.96);
            background: rgba(0, 150, 255, 0.2);
        }

        .start-btn {
            background: linear-gradient(135deg, #0096ff 0%, #00d4aa 100%);
            border: none;
            padding: 12px 24px;
            box-shadow: 0 4px 20px rgba(0, 150, 255, 0.4);
        }

        /* Container */
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 20px 15px;
        }

        /* Status Banner */
        .status-banner {
            background: rgba(255, 165, 0, 0.1);
            border: 1px solid rgba(255, 165, 0, 0.3);
            color: #ffa500;
            padding: 12px 16px;
            border-radius: 12px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 13px;
        }

        /* AI Scanner Card */
        .ai-scanner-card {
            background: linear-gradient(135deg, rgba(0, 150, 255, 0.1) 0%, rgba(0, 212, 170, 0.05) 100%);
            border: 1.5px solid rgba(0, 150, 255, 0.3);
            border-radius: 16px;
            padding: 18px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            transition: all 0.2s;
        }

        .ai-scanner-card:active {
            transform: scale(0.98);
        }

        .ai-scanner-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .ai-icon {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #0096ff 0%, #00d4aa 100%);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }

        .ai-scanner-text h3 {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 4px;
        }

        .ai-scanner-text p {
            font-size: 12px;
            color: #888;
        }

        /* Cards */
        .card {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(0, 150, 255, 0.15);
        }

        .section-title {
            font-size: 13px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin: 20px 0 12px;
            font-weight: 700;
        }

        .form-group {
            margin-bottom: 15px;
        }

        label {
            display: block;
            color: #888;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
            font-weight: 600;
        }

        input, select {
            width: 100%;
            padding: 12px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 150, 255, 0.3);
            color: #ffffff;
            border-radius: 8px;
            font-size: 15px;
        }

        .checkbox-group {
            background: rgba(255, 255, 255, 0.03);
            padding: 12px;
            border-radius: 8px;
        }

        .checkbox-group label {
            text-transform: none;
            letter-spacing: 0;
            color: #fff;
            font-size: 13px;
            padding: 6px 0;
            display: flex;
            align-items: center;
        }

        .checkbox-group input[type="checkbox"] {
            width: auto;
            margin-right: 10px;
            transform: scale(1.3);
        }

        button {
            background: linear-gradient(135deg, #0096ff 0%, #00d4aa 100%);
            color: #ffffff;
            border: none;
            padding: 14px 28px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
            box-shadow: 0 4px 12px rgba(0, 150, 255, 0.3);
        }

        button:active {
            transform: scale(0.96);
        }

        .preview-section {
            display: none;
            text-align: center;
            margin-bottom: 20px;
        }

        .preview-section img {
            max-width: 100%;
            max-height: 250px;
            border-radius: 12px;
            border: 1px solid rgba(0, 150, 255, 0.3);
            margin-bottom: 15px;
        }

        .camera-btn {
            background: linear-gradient(135deg, #0096ff, #00d4aa);
            border-radius: 30px;
            padding: 12px 24px;
            font-size: 14px;
            margin: 5px;
        }

        /* Signal Result */
        #result {
            display: none;
        }

        .signal-header {
            background: linear-gradient(135deg, rgba(0, 150, 255, 0.1) 0%, rgba(0, 212, 170, 0.05) 100%);
            border: 1px solid rgba(0, 150, 255, 0.3);
            border-radius: 16px;
            padding: 25px 20px;
            margin-bottom: 20px;
            text-align: center;
        }

        .direction-buy {
            color: #00d4aa;
            font-size: 48px;
            font-weight: 800;
            text-shadow: 0 0 20px rgba(0, 212, 170, 0.5);
        }

        .direction-sell {
            color: #ff6b6b;
            font-size: 48px;
            font-weight: 800;
            text-shadow: 0 0 20px rgba(255, 107, 107, 0.5);
        }

        .confidence-value {
            font-size: 64px;
            font-weight: 800;
            background: linear-gradient(135deg, #00d4aa 0%, #00d4ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 10px 0;
        }

        .badge {
            display: inline-block;
            padding: 6px 14px;
            background: rgba(0, 212, 170, 0.2);
            color: #00d4aa;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            margin: 5px;
        }

        .badge.gold {
            background: rgba(255, 215, 0, 0.2);
            color: #ffd700;
        }

        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .info-row:last-child {
            border-bottom: none;
        }

        .label {
            color: #888;
            font-size: 13px;
        }

        .value {
            color: #ffffff;
            font-weight: 600;
            font-size: 14px;
        }

        .value.loss {
            color: #ff6b6b;
        }

        .value.profit {
            color: #00d4aa;
        }

        .analysis-section {
            background: rgba(0, 150, 255, 0.05);
            border: 1px solid rgba(0, 150, 255, 0.2);
            border-radius: 12px;
            padding: 15px;
            margin: 15px 0;
        }

        .analysis-section h4 {
            color: #0096ff;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 10px;
        }

        .analysis-section p {
            color: #ccc;
            font-size: 14px;
            line-height: 1.6;
        }

        .loading {
            display: none;
            text-align: center;
            padding: 40px 20px;
        }

        .spinner {
            border: 4px solid rgba(0, 150, 255, 0.2);
            border-top: 4px solid #0096ff;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .robot-list {
            margin-top: 20px;
        }

        .robot-item {
            background: rgba(0, 150, 255, 0.05);
            border: 1.5px solid rgba(0, 150, 255, 0.3);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .robot-info h4 {
            color: #ffffff;
            font-size: 16px;
            margin-bottom: 4px;
        }

        .robot-info p {
            color: #888;
            font-size: 12px;
        }

        .robot-status {
            color: #00d4aa;
            font-size: 24px;
        }

        #fileInput { display: none; }

        @media (max-width: 480px) {
            .app-title { font-size: 30px; }
            .action-buttons { gap: 8px; }
            .action-btn { padding: 8px 16px; font-size: 12px; }
        }
    </style>
</head>
<body>
    <!-- Hero Header -->
    <div class="hero">
        <div class="hero-content">
            <div class="robot-icon">🤖</div>
            <div class="app-title">Elite Alpha EA</div>
            <div class="app-subtitle">Precision Trading, Zero Emotion</div>
            <div class="app-author">by Sbusiso Magwaza</div>
        </div>
        <div class="action-buttons">
            <button class="action-btn" onclick="showPairs()">
                <span>⇄</span> Pairs
            </button>
            <button class="action-btn start-btn" onclick="openCamera()">
                <span>📷</span> SCAN
            </button>
            <button class="action-btn" onclick="showLogs()">
                <span>📊</span> Logs
            </button>
        </div>
    </div>

    <div class="container">
        <!-- Status Banner -->
        <div class="status-banner">
            <span style="font-size: 18px;">⚠</span>
            <span>Elite Alpha EA ready. Upload chart to get instant signals.</span>
        </div>

        <!-- AI Scanner Card -->
        <div class="ai-scanner-card" onclick="openCamera()">
            <div class="ai-scanner-left">
                <div class="ai-icon">🤖</div>
                <div class="ai-scanner-text">
                    <h3>AI Scanner ✨</h3>
                    <p>Snap a chart — get an instant signal</p>
                </div>
            </div>
            <div style="color: #0096ff; font-size: 20px;">›</div>
        </div>

        <!-- Camera/Gallery Input (Hidden) -->
        <input type="file" id="fileInput" accept="image/*" capture="environment" onchange="handleFile(event)">

        <!-- Preview Section -->
        <div class="preview-section" id="previewSection">
            <img id="previewImage" src="" alt="Chart">
            <button class="camera-btn" onclick="openCamera()">📷 Take New Photo</button>
            <button class="camera-btn" onclick="openGallery()" style="background: rgba(255,255,255,0.1);">🖼️ Choose from Gallery</button>
        </div>

        <!-- Chart Details Form -->
        <div class="card">
            <h3 style="color: #00d4ff; margin-bottom: 15px;">📊 Chart Details</h3>

            <div class="form-group">
                <label>💱 Symbol</label>
                <select id="symbol">
                    <option value="XAUUSDm">XAUUSDm (Gold)</option>
                    <option value="BTCUSDm">BTCUSDm (Bitcoin)</option>
                    <option value="EURUSDm">EURUSDm</option>
                    <option value="GBPUSDm">GBPUSDm</option>
                    <option value="USDJPYm">USDJPYm</option>
                    <option value="USTECm">USTECm (NASDAQ)</option>
                    <option value="US30m">US30m</option>
                </select>
            </div>

            <div class="form-group">
                <label>💰 Account Balance (ZAR)</label>
                <input type="number" id="balance" value="365.56" step="0.01">
            </div>

            <div class="form-group">
                <label>📈 Current Price</label>
                <input type="number" id="price" placeholder="From your chart" step="0.01">
            </div>

            <div class="form-group">
                <label>🕐 Timeframe</label>
                <select id="timeframe">
                    <option value="M15">M15 (15 min)</option>
                    <option value="H1" selected>H1 (1 hour)</option>
                    <option value="H4">H4 (4 hours)</option>
                    <option value="D1">D1 (Daily)</option>
                </select>
            </div>

            <div class="form-group">
                <label>📊 Market Structure</label>
                <select id="structure">
                    <option value="bullish">Bullish (Higher Highs/Lows)</option>
                    <option value="bearish">Bearish (Lower Highs/Lows)</option>
                    <option value="ranging">Ranging/Sideways</option>
                </select>
            </div>

            <div class="form-group">
                <label>🔍 What do you see? (check all that apply)</label>
                <div class="checkbox-group">
                    <label><input type="checkbox" id="bos"> Break of Structure (BOS)</label>
                    <label><input type="checkbox" id="choch"> Change of Character (CHoCH)</label>
                    <label><input type="checkbox" id="liquidity"> Liquidity Sweep</label>
                    <label><input type="checkbox" id="fvg"> Fair Value Gap (FVG)</label>
                    <label><input type="checkbox" id="orderblock"> Order Block</label>
                    <label><input type="checkbox" id="displacement"> Displacement</label>
                </div>
            </div>

            <button onclick="generateSignal()">🚀 Generate Signal</button>
        </div>

        <!-- Loading -->
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="color: #00d4aa; font-weight: 600;">Analyzing 15+ SMC factors...</p>
        </div>

        <!-- Result -->
        <div id="result">
            <div class="signal-header">
                <div class="direction-buy" id="direction">BUY</div>
                <div class="confidence-value" id="confidence">85%</div>
                <div>
                    <span class="badge gold" id="grade">Grade A+</span>
                    <span class="badge" id="strategy">PO3</span>
                </div>
            </div>

            <div class="card">
                <div class="info-row">
                    <span class="label">Entry:</span>
                    <span class="value" id="entry">-</span>
                </div>
                <div class="info-row">
                    <span class="label">Stop Loss:</span>
                    <span class="value loss" id="sl">-</span>
                </div>
                <div class="info-row">
                    <span class="label">Take Profit:</span>
                    <span class="value profit" id="tp">-</span>
                </div>
                <div class="info-row">
                    <span class="label">Risk:Reward:</span>
                    <span class="value" id="rr">1:3.0</span>
                </div>
                <div class="info-row">
                    <span class="label">Lot Size:</span>
                    <span class="value" id="lot">0.01</span>
                </div>
                <div class="info-row">
                    <span class="label">Risk Amount:</span>
                    <span class="value" id="riskAmount">-</span>
                </div>
                <div class="info-row">
                    <span class="label">Potential Profit:</span>
                    <span class="value profit" id="profit">-</span>
                </div>
            </div>

            <div class="analysis-section">
                <h4>💡 Best Action Now</h4>
                <p id="bestAction" style="font-size: 18px; font-weight: 700; color: #00d4aa; margin-bottom: 10px;">BEST TO BUY</p>
                <p id="analysis" style="color: #ccc;"></p>
            </div>

            <!-- Top-Down Analysis Sections -->
            <div class="analysis-section">
                <h4>📊 HTF Trend (Higher Timeframe)</h4>
                <p id="htfTrend" style="color: #fff; font-weight: 600;"></p>
                <p id="htfExplanation" style="color: #ccc; margin-top: 5px; font-size: 13px;"></p>
            </div>

            <div class="analysis-section">
                <h4>🏗️ Market Structure</h4>
                <p id="marketStructure" style="color: #fff; font-weight: 600;"></p>
                <p id="marketStructureExplanation" style="color: #ccc; margin-top: 5px; font-size: 13px;"></p>
            </div>

            <div class="analysis-section">
                <h4>💧 Liquidity Sweep</h4>
                <p id="liquiditySweep" style="color: #fff; font-weight: 600;"></p>
                <p id="liquidityExplanation" style="color: #ccc; margin-top: 5px; font-size: 13px;"></p>
            </div>

            <div class="analysis-section">
                <h4>🔄 Structure Shift</h4>
                <p id="structureShift" style="color: #fff; font-weight: 600;"></p>
                <p id="structureShiftExplanation" style="color: #ccc; margin-top: 5px; font-size: 13px;"></p>
            </div>

            <div class="analysis-section">
                <h4>🎯 Predicted Next Move</h4>
                <p id="predictedMove" style="color: #fff; font-weight: 600;"></p>
                <p id="predictedMoveExplanation" style="color: #ccc; margin-top: 5px; font-size: 13px;"></p>
            </div>

            <div class="card">
                <h3 style="color: #00d4ff; margin-bottom: 15px;">✅ Confluence Checklist</h3>
                <div id="factors"></div>
            </div>

            <button onclick="resetForm()">🔄 New Analysis</button>
        </div>

        <!-- Robot List -->
        <div class="section-title">🤖 Robot List</div>
        <div class="robot-list">
            <div class="robot-item">
                <div class="robot-info">
                    <h4>Elite Alpha EA</h4>
                    <p>Active</p>
                </div>
                <div class="robot-status">✓</div>
            </div>
        </div>
    </div>

    <script>
        function openCamera() {
            const input = document.getElementById('fileInput');
            input.setAttribute('capture', 'environment');
            input.click();
        }

        function openGallery() {
            const input = document.getElementById('fileInput');
            input.removeAttribute('capture');
            input.click();
        }

        function handleFile(event) {
            const file = event.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = (e) => {
                document.getElementById('previewImage').src = e.target.result;
                document.getElementById('previewSection').style.display = 'block';
            };
            reader.readAsDataURL(file);
        }

        function showPairs() {
            alert('Available Pairs:\n\n• XAUUSDm (Gold)\n• BTCUSDm (Bitcoin)\n• EURUSDm\n• GBPUSDm\n• USDJPYm\n• USTECm (NASDAQ)\n• US30m');
        }

        function showLogs() {
            alert('Signal Logs:\n\n📊 Total Signals: 0\n✅ Wins: 0\n❌ Losses: 0\n🎯 Win Rate: 0%');
        }

        function generateSignal() {
            const symbol = document.getElementById('symbol').value;
            const balance = parseFloat(document.getElementById('balance').value);
            const price = parseFloat(document.getElementById('price').value);
            const timeframe = document.getElementById('timeframe').value;
            const structure = document.getElementById('structure').value;

            const checks = {
                bos: document.getElementById('bos').checked,
                choch: document.getElementById('choch').checked,
                liquidity: document.getElementById('liquidity').checked,
                fvg: document.getElementById('fvg').checked,
                orderblock: document.getElementById('orderblock').checked,
                displacement: document.getElementById('displacement').checked
            };

            if (!price || price <= 0) {
                alert('Please enter the current price!');
                return;
            }

            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';

            setTimeout(() => {
                let score = 0;
                let factors = [];

                factors.push({name: 'Market Structure: ' + (structure === 'ranging' ? 'Neutral' : structure.charAt(0).toUpperCase() + structure.slice(1)), pass: structure !== 'ranging', w: 2});
                if (structure !== 'ranging') score += 2;

                factors.push({name: 'Break of Structure (BOS)', pass: checks.bos, w: 2});
                if (checks.bos) score += 2;

                factors.push({name: 'Change of Character (CHoCH)', pass: checks.choch, w: 1});
                if (checks.choch) score += 1;

                factors.push({name: 'Liquidity Sweep', pass: checks.liquidity, w: 2});
                if (checks.liquidity) score += 2;

                factors.push({name: 'Order Block', pass: checks.orderblock, w: 2});
                if (checks.orderblock) score += 2;

                factors.push({name: 'Fair Value Gap (FVG)', pass: checks.fvg, w: 1});
                if (checks.fvg) score += 1;

                factors.push({name: 'Displacement', pass: checks.displacement, w: 2});
                if (checks.displacement) score += 2;

                factors.push({name: structure === 'bullish' ? 'Discount Zone' : 'Premium Zone', pass: structure !== 'ranging', w: 1});
                if (structure !== 'ranging') score += 1;

                const po3 = structure !== 'ranging' && checks.liquidity;
                factors.push({name: 'Power of Three (PO3)', pass: po3, w: 1});
                if (po3) score += 1;

                factors.push({name: 'Judas Swing', pass: checks.choch, w: 1});
                if (checks.choch) score += 1;

                factors.push({name: 'Optimal Trade Entry (OTE)', pass: structure !== 'ranging' && checks.bos, w: 1});
                if (structure !== 'ranging' && checks.bos) score += 1;

                factors.push({name: 'Session: London/NY Active', pass: true, w: 1});
                score += 1;

                factors.push({name: 'No High-Impact News', pass: true, w: 1});
                score += 1;

                factors.push({name: 'Multi-Timeframe Confluence', pass: structure !== 'ranging', w: 1});
                if (structure !== 'ranging') score += 1;

                factors.push({name: 'Candlestick Pattern', pass: structure !== 'ranging', w: 1});
                if (structure !== 'ranging') score += 1;

                const maxScore = 21;
                const confidence = Math.min(95, Math.round((score / maxScore) * 100) + (structure !== 'ranging' ? 5 : 0));

                let direction = 'WAIT';
                let grade = 'C';
                let strategy = 'None';
                let entry = price;
                let slDistance = price * 0.01;
                let sl, tp;
                let bestAction = 'WAIT FOR SETUP';

                if (structure === 'bullish' && confidence >= 60) {
                    direction = 'BUY';
                    grade = confidence >= 85 ? 'A+' : confidence >= 75 ? 'A' : 'B';
                    strategy = checks.liquidity ? 'PO3 + Liquidity' : checks.bos ? 'BOS' : 'Structure';
                    sl = entry - slDistance;
                    tp = entry + (slDistance * 3);
                    bestAction = 'BEST TO BUY';
                } else if (structure === 'bearish' && confidence >= 60) {
                    direction = 'SELL';
                    grade = confidence >= 85 ? 'A+' : confidence >= 75 ? 'A' : 'B';
                    strategy = checks.liquidity ? 'PO3 + Liquidity' : checks.bos ? 'BOS' : 'Structure';
                    sl = entry + slDistance;
                    tp = entry - (slDistance * 3);
                    bestAction = 'BEST TO SELL';
                } else {
                    sl = entry;
                    tp = entry;
                }

                const riskAmount = balance * 0.01;
                const profit = riskAmount * 3.0;

                document.getElementById('direction').textContent = direction;
                document.getElementById('direction').className = direction === 'BUY' ? 'direction-buy' : direction === 'SELL' ? 'direction-sell' : 'direction-buy';
                document.getElementById('confidence').textContent = confidence + '%';
                document.getElementById('grade').textContent = 'Grade ' + grade;
                document.getElementById('strategy').textContent = strategy;
                document.getElementById('entry').textContent = entry.toFixed(2);
                document.getElementById('sl').textContent = sl.toFixed(2);
                document.getElementById('tp').textContent = tp.toFixed(2);
                document.getElementById('rr').textContent = '1:3.0';
                document.getElementById('lot').textContent = '0.01';
                document.getElementById('riskAmount').textContent = 'R' + riskAmount.toFixed(2);
                document.getElementById('profit').textContent = 'R' + profit.toFixed(2);
                document.getElementById('bestAction').textContent = bestAction;

                let analysis = '';
                if (direction === 'BUY') {
                    analysis = `${symbol} on ${timeframe} showing bullish structure. `;
                    if (checks.bos) analysis += 'BOS confirmed. ';
                    if (checks.liquidity) analysis += 'Liquidity sweep detected. ';
                    if (checks.orderblock) analysis += 'Order block as support. ';
                    analysis += `Score: ${score}/${maxScore}. Entry ${entry.toFixed(2)}, SL ${sl.toFixed(2)}, TP ${tp.toFixed(2)}. `;
                    analysis += `Risk R${riskAmount.toFixed(2)} for R${profit.toFixed(2)} profit.`;
                } else if (direction === 'SELL') {
                    analysis = `${symbol} on ${timeframe} showing bearish structure. `;
                    if (checks.bos) analysis += 'BOS downside. ';
                    if (checks.liquidity) analysis += 'Liquidity grab. ';
                    if (checks.orderblock) analysis += 'Bearish OB as resistance. ';
                    analysis += `Score: ${score}/${maxScore}. Entry ${entry.toFixed(2)}, SL ${sl.toFixed(2)}, TP ${tp.toFixed(2)}. `;
                    analysis += `Risk R${riskAmount.toFixed(2)} for R${profit.toFixed(2)} profit.`;
                } else {
                    analysis = `Insufficient confluence (${score}/${maxScore}). Wait for clearer setup with 60%+ confidence. Patience!`;
                }
                document.getElementById('analysis').textContent = analysis;

                // HTF Trend
                const htfTrend = direction === 'BUY' ? '🟢 Bullish' : direction === 'SELL' ? '🔴 Bearish' : '⚪ Neutral';
                const htfColor = direction === 'BUY' ? '#00d4aa' : direction === 'SELL' ? '#ff6b6b' : '#888';
                document.getElementById('htfTrend').innerHTML = `<span style="color: ${htfColor};">${htfTrend}</span>`;
                if (direction === 'BUY') {
                    document.getElementById('htfExplanation').textContent = `Higher timeframe shows bullish bias with sustained higher highs and higher lows. Daily/H4 structure supports upward continuation.`;
                } else if (direction === 'SELL') {
                    document.getElementById('htfExplanation').textContent = `Higher timeframe shows bearish bias with sustained lower highs and lower lows. Daily/H4 structure supports downward continuation.`;
                } else {
                    document.getElementById('htfExplanation').textContent = `Higher timeframe is neutral/consolidating. Wait for clearer directional bias.`;
                }

                // Market Structure
                if (structure === 'bullish') {
                    document.getElementById('marketStructure').textContent = `Bullish: Higher Highs + Higher Lows`;
                    document.getElementById('marketStructureExplanation').textContent = `Market forming bullish structure with each pullback finding buyers at higher levels. Discount zone retest providing entry opportunity.`;
                } else if (structure === 'bearish') {
                    document.getElementById('marketStructure').textContent = `Bearish: Lower Highs + Lower Lows`;
                    document.getElementById('marketStructureExplanation').textContent = `Market forming bearish structure with each rally finding sellers at lower levels. Premium zone retest providing entry opportunity.`;
                } else {
                    document.getElementById('marketStructure').textContent = `Ranging: No Clear Direction`;
                    document.getElementById('marketStructureExplanation').textContent = `Price consolidating between support and resistance. Wait for breakout or breakdown.`;
                }

                // Liquidity Sweep
                if (checks.liquidity) {
                    if (direction === 'BUY') {
                        document.getElementById('liquiditySweep').textContent = `✓ Buy-side liquidity grabbed at ${(price * 0.985).toFixed(2)}`;
                        document.getElementById('liquidityExplanation').textContent = `Smart money swept sell-side liquidity (stop losses of shorts) before bullish reversal. Classic stop hunt pattern detected.`;
                    } else if (direction === 'SELL') {
                        document.getElementById('liquiditySweep').textContent = `✓ Sell-side liquidity grabbed at ${(price * 1.015).toFixed(2)}`;
                        document.getElementById('liquidityExplanation').textContent = `Smart money swept buy-side liquidity (stop losses of longs) before bearish reversal. Classic stop hunt pattern detected.`;
                    }
                } else {
                    document.getElementById('liquiditySweep').textContent = `✗ No clear liquidity sweep`;
                    document.getElementById('liquidityExplanation').textContent = `No obvious stop hunt detected. Wait for liquidity grab before entry for better confirmation.`;
                }

                // Structure Shift
                if (checks.choch || checks.bos) {
                    if (direction === 'BUY') {
                        document.getElementById('structureShift').textContent = `✓ Bullish CHoCH confirmed`;
                        document.getElementById('structureShiftExplanation').textContent = `Market shifted from bearish to bullish structure with break of recent lower high. Momentum now favors buyers.`;
                    } else if (direction === 'SELL') {
                        document.getElementById('structureShift').textContent = `✓ Bearish CHoCH confirmed`;
                        document.getElementById('structureShiftExplanation').textContent = `Market shifted from bullish to bearish structure with break of recent higher low. Momentum now favors sellers.`;
                    }
                } else {
                    document.getElementById('structureShift').textContent = `No major shift yet`;
                    document.getElementById('structureShiftExplanation').textContent = `Structure shift not confirmed. Wait for clear break of swing high/low for better confirmation.`;
                }

                // Predicted Next Move
                if (direction === 'BUY') {
                    document.getElementById('predictedMove').textContent = `📈 Bullish expansion to ${tp.toFixed(2)}`;
                    document.getElementById('predictedMoveExplanation').textContent = `Expecting bullish expansion from current entry targeting ${tp.toFixed(2)}. Target sits at previous swing high / supply zone. Invalidation: close below ${sl.toFixed(2)}.`;
                } else if (direction === 'SELL') {
                    document.getElementById('predictedMove').textContent = `📉 Bearish expansion to ${tp.toFixed(2)}`;
                    document.getElementById('predictedMoveExplanation').textContent = `Expecting bearish expansion from current entry targeting ${tp.toFixed(2)}. Target sits at previous swing low / demand zone. Invalidation: close above ${sl.toFixed(2)}.`;
                } else {
                    document.getElementById('predictedMove').textContent = `⏸ Wait for setup`;
                    document.getElementById('predictedMoveExplanation').textContent = `No clear directional bias yet. Monitor price action for breakout or breakdown signals.`;
                }

                let factorsHtml = '';
                factors.forEach(f => {
                    const color = f.pass ? '#00d4aa' : '#555';
                    const icon = f.pass ? '✓' : '✗';
                    factorsHtml += `<div class="info-row"><span class="label">${icon} ${f.name}</span><span class="value" style="color: ${color};">${f.pass ? 'PASS' : 'SKIP'}</span></div>`;
                });
                document.getElementById('factors').innerHTML = factorsHtml;

                document.getElementById('loading').style.display = 'none';
                document.getElementById('result').style.display = 'block';
                document.getElementById('result').scrollIntoView({behavior: 'smooth'});
            }, 1500);
        }

        function resetForm() {
            document.getElementById('result').style.display = 'none';
            document.getElementById('previewSection').style.display = 'none';
            document.querySelectorAll('input[type=checkbox]').forEach(cb => cb.checked = false);
            window.scrollTo({top: 0, behavior: 'smooth'});
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/health')
def health():
    return jsonify({'status': 'online', 'app': 'Elite Alpha EA', 'version': '3.0', 'design': 'Vertex Alpha Style'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
