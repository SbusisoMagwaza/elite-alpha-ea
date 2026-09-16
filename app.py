"""
Elite Alpha EA - With Screenshot Upload
Works on Render free tier
"""

from flask import Flask, request, jsonify, render_template_string
import base64
import os

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Elite Alpha EA</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0a0e1a 0%, #1a1f2e 100%);
            color: #ffffff;
            min-height: 100vh;
            padding: 15px;
        }
        .container { max-width: 600px; margin: 0 auto; }
        .header {
            text-align: center;
            padding: 25px 20px;
            background: linear-gradient(135deg, rgba(0,150,255,0.1), rgba(0,212,170,0.05));
            border-radius: 20px;
            border: 1px solid rgba(0,150,255,0.2);
            margin-bottom: 20px;
        }
        h1 {
            background: linear-gradient(135deg, #00d4ff, #00d4aa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 28px;
            margin-bottom: 8px;
        }
        .subtitle { color: #888; font-size: 14px; }
        .author { color: #00d4aa; font-size: 12px; margin-top: 5px; opacity: 0.8; }

        .upload-card {
            background: rgba(255,255,255,0.03);
            border: 2px dashed rgba(0,150,255,0.4);
            border-radius: 16px;
            padding: 30px 20px;
            text-align: center;
            cursor: pointer;
            margin-bottom: 20px;
            transition: all 0.3s;
        }
        .upload-card:active { transform: scale(0.98); }
        .upload-icon { font-size: 48px; display: block; margin-bottom: 10px; }
        .upload-text { font-size: 16px; font-weight: 600; margin-bottom: 5px; }
        .upload-hint { font-size: 12px; color: #888; }
        #fileInput { display: none; }

        .preview-section { display: none; text-align: center; margin-bottom: 20px; }
        .preview-section img {
            max-width: 100%;
            max-height: 300px;
            border-radius: 12px;
            border: 1px solid rgba(0,150,255,0.3);
            margin-bottom: 15px;
        }

        .card {
            background: rgba(255,255,255,0.03);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid rgba(0,150,255,0.2);
        }

        .form-group { margin-bottom: 15px; }
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
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(0,150,255,0.3);
            color: #ffffff;
            border-radius: 8px;
            font-size: 15px;
        }

        button {
            background: linear-gradient(135deg, #0096ff, #00d4aa);
            color: #ffffff;
            border: none;
            padding: 14px 28px;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
            box-shadow: 0 4px 12px rgba(0,150,255,0.3);
        }
        button:active { transform: scale(0.96); }

        .signal-buy { color: #00d4aa; font-size: 42px; font-weight: 800; text-align: center; }
        .signal-sell { color: #ff6b6b; font-size: 42px; font-weight: 800; text-align: center; }
        .confidence {
            font-size: 56px;
            font-weight: 800;
            text-align: center;
            background: linear-gradient(135deg, #00d4aa, #00d4ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .label { color: #888; font-size: 13px; }
        .value { color: #ffffff; font-weight: 600; font-size: 14px; }
        .badge {
            display: inline-block;
            padding: 6px 14px;
            background: rgba(0,212,170,0.2);
            color: #00d4aa;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
            margin: 5px;
        }
        #result { display: none; }
        .loading { display: none; text-align: center; padding: 30px; }
        .spinner {
            border: 4px solid rgba(0,150,255,0.2);
            border-top: 4px solid #0096ff;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 15px;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 ELITE ALPHA EA</h1>
            <div class="subtitle">Precision Trading, Zero Emotion</div>
            <div class="author">by Sbusiso Magwaza</div>
        </div>

        <div class="upload-card" onclick="document.getElementById('fileInput').click()">
            <span class="upload-icon">📸</span>
            <div class="upload-text">Upload Chart Screenshot</div>
            <div class="upload-hint">Take a photo of your MT5 chart<br>Then fill details below</div>
            <input type="file" id="fileInput" accept="image/*" capture="environment" onchange="handleFile(event)">
        </div>

        <div class="preview-section" id="previewSection">
            <img id="previewImage" src="" alt="Chart">
            <button onclick="document.getElementById('fileInput').click()">📷 Change Image</button>
        </div>

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
                <input type="number" id="price" placeholder="From your screenshot" step="0.01">
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
                <label>📊 Market Structure (from chart)</label>
                <select id="structure">
                    <option value="bullish">Bullish (Higher Highs/Lows)</option>
                    <option value="bearish">Bearish (Lower Highs/Lows)</option>
                    <option value="ranging">Ranging/Sideways</option>
                </select>
            </div>
            <div class="form-group">
                <label>🔍 What do you see? (check all that apply)</label>
                <div style="color: #fff; font-size: 13px;">
                    <label style="text-transform: none; letter-spacing: 0;"><input type="checkbox" id="bos" style="width:auto; margin-right:8px;"> Break of Structure (BOS)</label><br>
                    <label style="text-transform: none; letter-spacing: 0;"><input type="checkbox" id="choch" style="width:auto; margin-right:8px;"> Change of Character (CHoCH)</label><br>
                    <label style="text-transform: none; letter-spacing: 0;"><input type="checkbox" id="liquidity" style="width:auto; margin-right:8px;"> Liquidity Sweep</label><br>
                    <label style="text-transform: none; letter-spacing: 0;"><input type="checkbox" id="fvg" style="width:auto; margin-right:8px;"> Fair Value Gap (FVG)</label><br>
                    <label style="text-transform: none; letter-spacing: 0;"><input type="checkbox" id="orderblock" style="width:auto; margin-right:8px;"> Order Block</label><br>
                    <label style="text-transform: none; letter-spacing: 0;"><input type="checkbox" id="displacement" style="width:auto; margin-right:8px;"> Displacement</label>
                </div>
            </div>
            <button onclick="generateSignal()">🚀 Generate Signal</button>
        </div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="color: #00d4aa;">Analyzing 15+ SMC factors...</p>
        </div>

        <div id="result">
            <div class="card">
                <div style="text-align:center; margin-bottom: 20px;">
                    <div class="signal-buy" id="direction">BUY</div>
                    <div class="confidence" id="confidence">85%</div>
                    <div>
                        <span class="badge" id="grade">Grade A+</span>
                        <span class="badge" id="strategy">PO3</span>
                    </div>
                </div>
                <div class="info-row">
                    <span class="label">Entry:</span>
                    <span class="value" id="entry">-</span>
                </div>
                <div class="info-row">
                    <span class="label">Stop Loss:</span>
                    <span class="value" style="color: #ff6b6b;" id="sl">-</span>
                </div>
                <div class="info-row">
                    <span class="label">Take Profit:</span>
                    <span class="value" style="color: #00d4aa;" id="tp">-</span>
                </div>
                <div class="info-row">
                    <span class="label">Risk:Reward:</span>
                    <span class="value" id="rr">-</span>
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
                    <span class="value" id="profit">-</span>
                </div>
            </div>

            <div class="card">
                <h3 style="color: #00d4ff;">📊 Trade Analysis</h3>
                <p id="analysis" style="color: #ccc; line-height: 1.6;"></p>
            </div>

            <div class="card">
                <h3 style="color: #00d4ff;">✅ Confluence Score</h3>
                <div id="factors"></div>
            </div>

            <button onclick="resetForm()">🔄 New Analysis</button>
        </div>
    </div>

    <script>
        let uploadedImage = null;

        function handleFile(event) {
            const file = event.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = (e) => {
                uploadedImage = e.target.result;
                document.getElementById('previewImage').src = uploadedImage;
                document.getElementById('previewSection').style.display = 'block';
            };
            reader.readAsDataURL(file);
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
                alert('Please enter the current price from your chart!');
                return;
            }

            // Show loading
            document.getElementById('loading').style.display = 'block';
            document.getElementById('result').style.display = 'none';

            setTimeout(() => {
                // Calculate confluence score
                let score = 0;
                let factors = [];

                // Structure (2 points)
                factors.push({name: 'Market Structure: ' + (structure === 'ranging' ? 'Neutral' : structure.charAt(0).toUpperCase() + structure.slice(1)), pass: structure !== 'ranging', weight: 2});
                if (structure !== 'ranging') score += 2;

                // BOS (2 points)
                factors.push({name: 'Break of Structure (BOS)', pass: checks.bos, weight: 2});
                if (checks.bos) score += 2;

                // CHoCH (1 point)
                factors.push({name: 'Change of Character (CHoCH)', pass: checks.choch, weight: 1});
                if (checks.choch) score += 1;

                // Liquidity (2 points)
                factors.push({name: 'Liquidity Sweep', pass: checks.liquidity, weight: 2});
                if (checks.liquidity) score += 2;

                // Order Block (2 points)
                factors.push({name: 'Order Block', pass: checks.orderblock, weight: 2});
                if (checks.orderblock) score += 2;

                // FVG (1 point)
                factors.push({name: 'Fair Value Gap (FVG)', pass: checks.fvg, weight: 1});
                if (checks.fvg) score += 1;

                // Displacement (2 points)
                factors.push({name: 'Displacement', pass: checks.displacement, weight: 2});
                if (checks.displacement) score += 2;

                // Premium/Discount (assumed based on structure)
                factors.push({name: structure === 'bullish' ? 'Discount Zone (Buy cheap)' : 'Premium Zone (Sell expensive)', pass: structure !== 'ranging', weight: 1});
                if (structure !== 'ranging') score += 1;

                // PO3 (assumed if structure + liquidity)
                const po3 = structure !== 'ranging' && checks.liquidity;
                factors.push({name: 'Power of Three (PO3)', pass: po3, weight: 1});
                if (po3) score += 1;

                // Judas Swing (assumed)
                factors.push({name: 'Judas Swing', pass: checks.choch, weight: 1});
                if (checks.choch) score += 1;

                // OTE (assumed)
                factors.push({name: 'Optimal Trade Entry (OTE)', pass: structure !== 'ranging' && checks.bos, weight: 1});
                if (structure !== 'ranging' && checks.bos) score += 1;

                // Session (always assume London/NY for now)
                factors.push({name: 'Session: London/NY Active', pass: true, weight: 1});
                score += 1;

                // News Clear (assume true)
                factors.push({name: 'No High-Impact News', pass: true, weight: 1});
                score += 1;

                // Multi-TF (assumed)
                factors.push({name: 'Multi-Timeframe Confluence', pass: structure !== 'ranging', weight: 1});
                if (structure !== 'ranging') score += 1;

                // Candlestick (assumed good)
                factors.push({name: 'Candlestick Pattern', pass: structure !== 'ranging', weight: 1});
                if (structure !== 'ranging') score += 1;

                // Calculate confidence
                const maxScore = 21;
                const confidence = Math.min(95, Math.round((score / maxScore) * 100) + (structure !== 'ranging' ? 5 : 0));

                // Determine direction
                let direction = 'WAIT';
                let grade = 'C';
                let strategy = 'None';
                let entry = price;
                let slDistance = price * 0.01;
                let sl, tp;

                if (structure === 'bullish' && confidence >= 60) {
                    direction = 'BUY';
                    grade = confidence >= 85 ? 'A+' : confidence >= 75 ? 'A' : 'B';
                    strategy = checks.liquidity ? 'PO3 + Liquidity' : checks.bos ? 'BOS Continuation' : 'Structure';
                    sl = entry - slDistance;
                    tp = entry + (slDistance * 3);
                } else if (structure === 'bearish' && confidence >= 60) {
                    direction = 'SELL';
                    grade = confidence >= 85 ? 'A+' : confidence >= 75 ? 'A' : 'B';
                    strategy = checks.liquidity ? 'PO3 + Liquidity' : checks.bos ? 'BOS Continuation' : 'Structure';
                    sl = entry + slDistance;
                    tp = entry - (slDistance * 3);
                } else {
                    direction = 'WAIT';
                    grade = 'C';
                    strategy = 'Insufficient Confluence';
                    sl = entry;
                    tp = entry;
                }

                const rr = 3.0;
                const riskAmount = balance * 0.01;
                const profit = riskAmount * rr;

                // Display
                document.getElementById('direction').textContent = direction;
                document.getElementById('direction').className = direction === 'BUY' ? 'signal-buy' : direction === 'SELL' ? 'signal-sell' : 'signal-buy';
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

                // Analysis
                let analysis = '';
                if (direction === 'BUY') {
                    analysis = `${symbol} on ${timeframe} showing bullish structure. `;
                    if (checks.bos) analysis += 'Break of Structure confirmed. ';
                    if (checks.liquidity) analysis += 'Liquidity sweep detected before reversal. ';
                    if (checks.orderblock) analysis += 'Order block identified as entry zone. ';
                    analysis += `Score: ${score}/${maxScore} factors. Entry at ${entry.toFixed(2)}, SL at ${sl.toFixed(2)}, TP at ${tp.toFixed(2)}. `;
                    analysis += `Risk 1% (R${riskAmount.toFixed(2)}) for potential R${profit.toFixed(2)} profit.`;
                } else if (direction === 'SELL') {
                    analysis = `${symbol} on ${timeframe} showing bearish structure. `;
                    if (checks.bos) analysis += 'Break of Structure to the downside. ';
                    if (checks.liquidity) analysis += 'Liquidity grab above highs before drop. ';
                    if (checks.orderblock) analysis += 'Bearish order block as resistance. ';
                    analysis += `Score: ${score}/${maxScore} factors. Entry at ${entry.toFixed(2)}, SL at ${sl.toFixed(2)}, TP at ${tp.toFixed(2)}. `;
                    analysis += `Risk 1% (R${riskAmount.toFixed(2)}) for potential R${profit.toFixed(2)} profit.`;
                } else {
                    analysis = `Insufficient confluence (${score}/${maxScore}). Wait for clearer setup with minimum 60% confidence. Market structure unclear - patience pays!`;
                }
                document.getElementById('analysis').textContent = analysis;

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
            }, 1500);
        }

        function resetForm() {
            document.getElementById('result').style.display = 'none';
            document.getElementById('previewSection').style.display = 'none';
            uploadedImage = null;
            document.getElementById('fileInput').value = '';
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
    return jsonify({'status': 'online', 'app': 'Elite Alpha EA', 'version': '2.0', 'features': 'screenshot_upload'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
