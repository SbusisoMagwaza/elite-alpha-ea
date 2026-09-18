function openGallery() {
    var input = document.getElementById('fileInput');
    input.removeAttribute('capture');
    input.click();
}

function handleFile(event) {
    var file = event.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function(e) {
        document.getElementById('previewImage').src = e.target.result;
        document.getElementById('previewSection').style.display = 'block';
        document.getElementById('uploadCard').style.display = 'none';
        document.getElementById('analyzeBtn').disabled = false;
        document.getElementById('result').style.display = 'none';
    };
    reader.readAsDataURL(file);
}

function analyzeImage() {
    var symbol = document.getElementById('symbol').value;
    var timeframe = document.getElementById('timeframe').value;
    var account = JSON.parse(localStorage.getItem('accountData') || '{}');
    var balance = account.balance || 369.19;
    var riskPercent = account.riskPercent || 1;

    document.getElementById('loading').style.display = 'block';
    document.getElementById('previewSection').style.display = 'none';
    document.getElementById('result').style.display = 'none';

    setTimeout(function() {
        fetch('/api/scan', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                symbol: symbol,
                timeframe: timeframe,
                balance: balance,
                risk_percent: riskPercent
            })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            displayResults(data);
            if (data.direction !== 'WAIT' && data.confidence >= 75) playSound();
        })
        .catch(function() {
            alert('Analysis failed');
            document.getElementById('loading').style.display = 'none';
        });
    }, 300);
}

function displayResults(data) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('result').style.display = 'block';

    var dirEl = document.getElementById('direction');
    dirEl.textContent = data.direction;
    dirEl.className = data.direction === 'SELL' ? 'direction-sell' : 'direction-buy';
    document.getElementById('confidence').textContent = data.confidence + '%';
    document.getElementById('grade').textContent = 'Grade ' + data.grade;
    document.getElementById('strategy').textContent = data.strategy;
    document.getElementById('entry').textContent = data.entry.toFixed(2);
    document.getElementById('sl').textContent = data.sl.toFixed(2);
    document.getElementById('tp').textContent = data.tp.toFixed(2);
    document.getElementById('rr').textContent = data.rr;
    document.getElementById('riskAmount').textContent = 'R' + data.risk_amount.toFixed(2);
    document.getElementById('profit').textContent = 'R' + data.potential_profit.toFixed(2);
    document.getElementById('positionSize').textContent = data.position_size.toFixed(2);
    document.getElementById('bestAction').textContent = data.direction === 'BUY' ? 'BEST TO BUY' : data.direction === 'SELL' ? 'BEST TO SELL' : 'WAIT';

    var htfColor = data.direction === 'BUY' ? '#00d4aa' : '#ff6b6b';
    document.getElementById('htfTrend').innerHTML = data.direction === 'BUY' ? '<span style="color: ' + htfColor + ';">🟢 Bullish</span>' : '<span style="color: ' + htfColor + ';">🔴 Bearish</span>';
    document.getElementById('htfExplanation').textContent = data.direction === 'BUY' ? 'HTF shows bullish bias with HH and HL.' : 'HTF shows bearish bias with LH and LL.';

    document.getElementById('marketStructure').textContent = data.structure === 'bullish' ? 'Bullish: HH + HL' : data.structure === 'bearish' ? 'Bearish: LH + LL' : 'Ranging';
    document.getElementById('marketStructureExplanation').textContent = data.structure === 'ranging' ? 'No clear directional structure.' : 'Market forming ' + data.structure + ' structure.';

    document.getElementById('liquiditySweep').textContent = data.factors['Liquidity Sweep'].pass ? '✓ Liquidity grabbed' : '✗ No clear sweep';
    document.getElementById('liquidityExplanation').textContent = data.factors['Liquidity Sweep'].pass ? 'Smart money swept stops.' : 'No stop hunt detected.';

    var checklistHtml = '';
    data.confluence_checklist.forEach(function(item) {
        var icon = item.pass ? '✓' : '✗';
        var iconClass = item.pass ? '' : 'fail';
        checklistHtml += '<div class="confluence-check-item"><span class="confluence-check-icon ' + iconClass + '">' + icon + '</span><span class="confluence-check-text"><strong>' + item.name + '</strong> — ' + item.detail + '</span></div>';
    });
    document.getElementById('confluenceChecklistItems').innerHTML = checklistHtml;

    var confluencesHtml = '';
    if (data.confluences.length === 0) {
        confluencesHtml = '<div style="color: #888; font-size: 13px;">No clear confluences - wait for better setup</div>';
    } else {
        data.confluences.forEach(function(text) {
            confluencesHtml += '<div style="display: flex; align-items: flex-start; padding: 6px 0; font-size: 13px; color: #ccc;"><span style="color: #00d4aa; margin-right: 10px;">•</span><span>' + text + '</span></div>';
        });
    }
    document.getElementById('confluencesList').innerHTML = confluencesHtml;

    var actionEl = document.getElementById('topdownAction');
    var actionTextEl = document.getElementById('topdownActionText');
    if (data.direction === 'BUY') {
        actionEl.classList.add('topdown-action-buy');
        actionTextEl.textContent = 'BEST TO BUY';
    } else {
        actionEl.classList.remove('topdown-action-buy');
        actionTextEl.textContent = 'BEST TO SELL';
    }
    document.getElementById('nextTriggerText').textContent = data.topdown.next_trigger;
    document.getElementById('invalidationText').textContent = data.topdown.invalidation;

    document.getElementById('result').scrollIntoView({behavior: 'smooth'});
}

function resetForm() {
    document.getElementById('result').style.display = 'none';
    document.getElementById('previewSection').style.display = 'none';
    document.getElementById('uploadCard').style.display = 'block';
    document.getElementById('analyzeBtn').disabled = true;
    document.getElementById('fileInput').value = '';
    window.scrollTo({top: 0, behavior: 'smooth'});
}

document.addEventListener('DOMContentLoaded', function() {
    var account = JSON.parse(localStorage.getItem('accountData') || '{}');
    if (account.balance) document.getElementById('riskBalance').value = account.balance;
    if (account.riskPercent) document.getElementById('riskPercent').value = account.riskPercent;
});
