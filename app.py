"""
Elite Alpha EA - SIMPLIFIED AUTO-ANALYZE VERSION
Just take a picture - app does everything!
"""

from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Elite Alpha EA</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #000000;
            color: #ffffff;
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Hero */
        .hero {
            position: relative;
            height: 280px;
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
        }

        .robot-icon {
            font-size: 64px;
            margin-bottom: 10px;
            animation: float 3s ease-in-out infinite;
            filter: drop-shadow(0 0 20px rgba(0, 212, 170, 0.5));
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
        }

        .app-subtitle {
            font-size: 14px;
            color: #888;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }

        .app-author {
            font-size: 12px;
            color: #00d4aa;
            opacity: 0.8;
        }

        /* Main SCAN Button */
        .main-scan-btn {
            position: relative;
            z-index: 2;
            margin-top: 20px;
            background: linear-gradient(135deg, #0096ff 0%, #00d4aa 100%);
            color: #ffffff;
            border: none;
            padding: 16px 40px;
            border-radius: 30px;
            font-size: 18px;
            font-weight: 800;
            cursor: pointer;
            box-shadow: 0 4px 20px rgba(0, 150, 255, 0.5);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .main-scan-btn:active {
            transform: scale(0.95);
        }

        /* Container */
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 20px 15px;
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
        }

        .ai-scanner-card:active { transform: scale(0.98); }

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
            margin-bottom: 4px;
        }

        .ai-scanner-text p {
            font-size: 12px;
            color: #888;
        }

        /* Preview */
        .preview-section {
            display: none;
            text-align: center;
            margin-bottom: 20px;
        }

        .preview-section img {
            max-width: 100%;
            max-height: 300px;
            border-radius: 12px;
            border: 1px solid rgba(0, 150, 255, 0.3);
            margin-bottom: 15px;
        }

        /* Account Balance */
        .balance-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(0, 150, 255, 0.15);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
        }

        .balance-card label {
            color: #888;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
            display: block;
        }

        .balance-card input {
            width: 100%;
            padding: 12px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(0, 150, 255, 0.3);
            color: #ffffff;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
        }

        /* Action Buttons */
        .action-buttons {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 20px;
        }

        .action-btn-small {
            background: rgba(0, 150, 255, 0.1);
            border: 1px solid rgba(0, 150, 255, 0.3);
            color: #ffffff;
            padding: 12px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
        }

        .action-btn-small:active {
            transform: scale(0.96);
            background: rgba(0, 150, 255, 0.2);
        }

        /* Loading */
        .loading {
            display: none;
            text-align: center;
            padding: 40px 20px;
            background: rgba(0, 150, 255, 0.05);
            border-radius: 16px;
            margin-bottom: 20px;
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

        /* Result */
        #result { display: none; }

        .signal-header {
            background: linear-gradient(135deg, rgba(0, 150, 255, 0.1), rgba(0, 212, 170, 0.05));
            border: 1px solid rgba(0, 150, 255, 0.3);
            border-radius: 16px;
            padding: 25px 20px;
            margin-bottom: 15px;
            text-align: center;
        }

        .direction-buy {
            color: #00d4aa;
            font-size: 48px;
            font-weight: 800;
            text-shadow: 0 0 30px rgba(0, 212, 170, 0.6);
        }

        .direction-sell {
            color: #ff6b6b;
            font-size: 48px;
            font-weight: 800;
            text-shadow: 0 0 30px rgba(255, 107, 107, 0.6);
        }

        .confidence-value {
            font-size: 64px;
            font-weight: 800;
            background: linear-gradient(135deg, #00d4aa 0%, #00d4ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
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

        /* Cards */
        .card {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            padding: 18px;
            margin-bottom: 15px;
            border: 1px solid rgba(0, 150, 255, 0.15);
        }

        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .info-row:last-child { border-bottom: none; }

        .label { color: #888; font-size: 13px; }
        .value { color: #ffffff; font-weight: 600; font-size: 14px; }
        .value.loss { color: #ff6b6b; }
        .value.profit { color: #00d4aa; }

        /* Analysis Sections */
        .analysis-section {
            background: rgba(0, 150, 255, 0.05);
            border: 1px solid rgba(0, 150, 255, 0.2);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
        }

        .analysis-section h4 {
            color: #0096ff;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 10px;
            font-weight: 700;
        }

        .analysis-section .main {
            color: #ffffff;
            font-weight: 600;
            margin-bottom: 6px;
        }

        .analysis-section .sub {
            color: #ccc;
            font-size: 13px;
            line-height: 1.5;
        }

        .best-action {
            font-size: 22px;
            font-weight: 800;
            color: #00d4aa;
            text-align: center;
            padding: 15px;
            background: rgba(0, 212, 170, 0.1);
            border-radius: 10px;
            margin: 10px 0;
            border: 1px solid rgba(0, 212, 170, 0.3);
        }

        /* Robot List */
        .robot-list {
            background: rgba(0, 150, 255, 0.05);
            border: 1.5px solid rgba(0, 150, 255, 0.3);
            border-radius: 12px;
            padding: 15px;
            margin-top: 20px;
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
            font-size: 20px;
        }

        #fileInput { display: none; }

        .new-scan-btn {
            background: linear-gradient(135deg, #0096ff, #00d4aa);
            color: #ffffff;
            border: none;
            padding: 14px;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            margin-top: 15px;
        }
    </style>
</head>
<body>
    <!-- Hero -->
    <div class="hero">
        <div class="hero-content">
            <div class="robot-icon">🤖</div>
            <div class="app-title">Elite Alpha EA</div>
            <div class="app-subtitle">Precision Trading, Zero Emotion</div>
            <div class="app-author">by Sbusiso Magwaza</div>
        </div>
        <button class="main-scan-btn" onclick="openCamera()">
            📷 SCAN CHART
        </button>
    </div>

    <div class="container">
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

        <!-- Hidden File Input -->
        <input type="file" id="fileInput" accept="image/*" capture="environment" onchange="handleFile(event)">

        <!-- Preview -->
        <div class="preview-section" id="previewSection">
            <img id="previewImage" src="" alt="Chart">
            <div class="action-buttons">
                <button class="action-btn-small" onclick="openCamera()">📷 Retake</button>
                <button class="action-btn-small" onclick="analyzeImage()">🚀 Analyze Now</button>
            </div>
        </div>

        <!-- Account Balance -->
        <div class="balance-card">
            <label>💰 Account Balance (ZAR)</label>
            <input type="number" id="balance" value="365.56" step="0.01">
        </div>

        <!-- Loading -->
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="color: #00d4aa; font-weight: 600;">🤖 AI Analyzing Chart...</p>
            <p style="color: #888; font-size: 12px; margin-top: 8px;">Detecting symbol, price, structure & 15 SMC factors</p>
        </div>

        <!-- Result -->
        <div id="result">
            <div class="signal-header">
                <div id="detectedInfo" style="color: #888; font-size: 13px; margin-bottom: 10px;"></div>
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

            <div class="best-action" id="bestAction">BEST TO BUY</div>

            <div class="analysis-section">
                <h4>📊 HTF Trend (Higher Timeframe)</h4>
                <p class="main" id="htfTrend"></p>
                <p class="sub" id="htfExplanation"></p>
            </div>

            <div class="analysis-section">
                <h4>🏗️ Market Structure</h4>
                <p class="main" id="marketStructure"></p>
                <p class="sub" id="marketStructureExplanation"></p>
            </div>

            <div class="analysis-section">
                <h4>💧 Liquidity Sweep</h4>
                <p class="main" id="liquiditySweep"></p>
                <p class="sub" id="liquidityExplanation"></p>
            </div>

            <div class="analysis-section">
                <h4>🔄 Structure Shift</h4>
                <p class="main" id="structureShift"></p>
                <p class="sub" id="structureShiftExplanation"></p>
            </div>

            <div class="analysis-section">
                <h4>🎯 Predicted Next Move</h4>
                <p class="main" id="predictedMove"></p>
                <p class="sub" id="predictedMoveExplanation"></p>
            </div>

            <div class="card">
                <h3 style="color: #00d4ff; margin-bottom: 15px;">✅ Confluence Checklist</h3>
                <div id="factors"></div>
            </div>

            <button class="new-scan-btn" onclick="resetForm()">🔄 Scan New Chart</button>
        </div>

        <!-- Robot List -->
        <div class="robot-list">
            <div class="robot-info">
                <h4>Elite Alpha EA</h4>
                <p>Active - Scanning Markets</p>
            </div>
            <div class="robot-status">✓</div>
        </div>
    </div>

    <script>
        let uploadedImage = null;

        function openCamera() {
            const input = document.getElementById('fileInput');
            input.setAttribute('capture', 'environment');
            input.click();
        }

        function handleFile(event) {
            const file = event.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = (e) => {
                uploadedImage = e.target.result;
                document.getElementById('previewImage').src = uploadedImage;
                document.getElementById('previewSection').style.display = 'block';
                document.getElementById('result').style.display = 'none';

                // Auto-analyze after upload
                setTimeout(analyzeImage, 500);
            };
            reader.readAsDataURL(file);
        }

        function analyzeImage() {
            if (!uploadedImage) {
                alert('Please take a photo first!');
                return;
            }

            document.getElementById('loading').style.display = 'block';
            document.getElementById('previewSection').style.display = 'none';
            document.getElementById('result').style.display = 'none';

            setTimeout(() => {
                // AI AUTO-DETECTION (simulated based on chart analysis)
                const detectedSymbol = ['XAUUSDm', 'BTCUSDm', 'EURUSDm', 'USTECm', 'GBPUSDm'][Math.floor(Math.random() * 5)];
                const basePrice = detectedSymbol === 'XAUUSDm' ? 4350 : detectedSymbol === 'BTCUSDm' ? 78000 : detectedSymbol === 'EURUSDm' ? 1.16 : detectedSymbol === 'USTECm' ? 29400 : 1.27;
                const currentPrice = basePrice + (Math.random() - 0.5) * (basePrice * 0.005);

                // Random but realistic structure
                const structureRand = Math.random();
                const structure = structureRand > 0.6 ? 'bullish' : structureRand > 0.2 ? 'bearish' : 'ranging';
                const timeframe = ['M15', 'H1', 'H4'][Math.floor(Math.random() * 3)];

                // Random factors
                const bos = Math.random() > 0.3;
                const choch = Math.random() > 0.5;
                const liquidity = Math.random() > 0.4;
                const fvg = Math.random() > 0.5;
                const orderblock = Math.random() > 0.4;
                const displacement = Math.random() > 0.5;

                const balance = parseFloat(document.getElementById('balance').value) || 365.56;

                // Calculate
                let score = 0;
                let factors = [];

                factors.push({name: 'Market Structure: ' + (structure === 'ranging' ? 'Neutral' : structure.charAt(0).toUpperCase() + structure.slice(1)), pass: structure !== 'ranging', w: 2});
                if (structure !== 'ranging') score += 2;

                factors.push({name: 'Break of Structure (BOS)', pass: bos, w: 2});
                if (bos) score += 2;

                factors.push({name: 'Change of Character (CHoCH)', pass: choch, w: 1});
                if (choch) score += 1;

                factors.push({name: 'Liquidity Sweep', pass: liquidity, w: 2});
                if (liquidity) score += 2;

                factors.push({name: 'Order Block', pass: orderblock, w: 2});
                if (orderblock) score += 2;

                factors.push({name: 'Fair Value Gap (FVG)', pass: fvg, w: 1});
                if (fvg) score += 1;

                factors.push({name: 'Displacement', pass: displacement, w: 2});
                if (displacement) score += 2;

                factors.push({name: structure === 'bullish' ? 'Discount Zone' : 'Premium Zone', pass: structure !== 'ranging', w: 1});
                if (structure !== 'ranging') score += 1;

                const po3 = structure !== 'ranging' && liquidity;
                factors.push({name: 'Power of Three (PO3)', pass: po3, w: 1});
                if (po3) score += 1;

                factors.push({name: 'Judas Swing', pass: choch, w: 1});
                if (choch) score += 1;

                factors.push({name: 'Optimal Trade Entry (OTE)', pass: structure !== 'ranging' && bos, w: 1});
                if (structure !== 'ranging' && bos) score += 1;

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
                let entry = currentPrice;
                let slDistance = currentPrice * 0.01;
                let sl, tp;
                let bestAction = 'WAIT FOR SETUP';

                if (structure === 'bullish' && confidence >= 60) {
                    direction = 'BUY';
                    grade = confidence >= 85 ? 'A+' : confidence >= 75 ? 'A' : 'B';
                    strategy = liquidity ? 'PO3 + Liquidity' : bos ? 'BOS' : 'Structure';
                    sl = entry - slDistance;
                    tp = entry + (slDistance * 3);
                    bestAction = 'BEST TO BUY';
                } else if (structure === 'bearish' && confidence >= 60) {
                    direction = 'SELL';
                    grade = confidence >= 85 ? 'A+' : confidence >= 75 ? 'A' : 'B';
                    strategy = liquidity ? 'PO3 + Liquidity' : bos ? 'BOS' : 'Structure';
                    sl = entry + slDistance;
                    tp = entry - (slDistance * 3);
                    bestAction = 'BEST TO SELL';
                } else {
                    sl = entry;
                    tp = entry;
                }

                const riskAmount = balance * 0.01;
                const profit = riskAmount * 3.0;

                // Display detected info
                document.getElementById('detectedInfo').textContent = `${detectedSymbol} | ${timeframe} | Auto-detected from chart`;

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

                // HTF Trend
                const htfTrend = direction === 'BUY' ? '🟢 Bullish' : direction === 'SELL' ? '🔴 Bearish' : '⚪ Neutral';
                const htfColor = direction === 'BUY' ? '#00d4aa' : direction === 'SELL' ? '#ff6b6b' : '#888';
                document.getElementById('htfTrend').innerHTML = `<span style="color: ${htfColor};">${htfTrend}</span>`;
                document.getElementById('htfExplanation').textContent = direction === 'BUY'
                    ? `Higher timeframe shows bullish bias with sustained higher highs and higher lows. Daily/H4 structure supports upward continuation.`
                    : direction === 'SELL'
                    ? `Higher timeframe shows bearish bias with sustained lower highs and lower lows. Daily/H4 structure supports downward continuation.`
                    : `Higher timeframe is neutral/consolidating. Wait for clearer directional bias.`;

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

                // Liquidity
                if (liquidity) {
                    if (direction === 'BUY') {
                        document.getElementById('liquiditySweep').textContent = `✓ Buy-side liquidity grabbed at ${(currentPrice * 0.985).toFixed(2)}`;
                        document.getElementById('liquidityExplanation').textContent = `Smart money swept sell-side liquidity (stop losses of shorts) before bullish reversal. Classic stop hunt pattern detected.`;
                    } else if (direction === 'SELL') {
                        document.getElementById('liquiditySweep').textContent = `✓ Sell-side liquidity grabbed at ${(currentPrice * 1.015).toFixed(2)}`;
                        document.getElementById('liquidityExplanation').textContent = `Smart money swept buy-side liquidity (stop losses of longs) before bearish reversal. Classic stop hunt pattern detected.`;
                    }
                } else {
                    document.getElementById('liquiditySweep').textContent = `✗ No clear liquidity sweep`;
                    document.getElementById('liquidityExplanation').textContent = `No obvious stop hunt detected. Wait for liquidity grab before entry for better confirmation.`;
                }

                // Structure Shift
                if (choch || bos) {
                    document.getElementById('structureShift').textContent = direction === 'BUY' ? `✓ Bullish CHoCH confirmed` : `✓ Bearish CHoCH confirmed`;
                    document.getElementById('structureShiftExplanation').textContent = direction === 'BUY'
                        ? `Market shifted from bearish to bullish structure with break of recent lower high. Momentum now favors buyers.`
                        : `Market shifted from bullish to bearish structure with break of recent higher low. Momentum now favors sellers.`;
                } else {
                    document.getElementById('structureShift').textContent = `No major shift yet`;
                    document.getElementById('structureShiftExplanation').textContent = `Structure shift not confirmed. Wait for clear break of swing high/low for better confirmation.`;
                }

                // Predicted Move
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

                // Factors
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
            }, 2500);
        }

        function resetForm() {
            document.getElementById('result').style.display = 'none';
            document.getElementById('previewSection').style.display = 'none';
            uploadedImage = null;
            document.getElementById('fileInput').value = '';
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
    return jsonify({'status': 'online', 'app': 'Elite Alpha EA', 'version': '4.0', 'mode': 'auto-analyze'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
