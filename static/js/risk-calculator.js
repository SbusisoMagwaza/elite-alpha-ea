function calculateRisk() {
    var balance = parseFloat(document.getElementById('riskBalance').value) || 0;
    var riskPercent = parseFloat(document.getElementById('riskPercent').value) || 1;

    if (balance <= 0) {
        showToast('Enter valid balance', 'error');
        return;
    }

    var riskAmount = balance * (riskPercent / 100);
    var potentialProfit = riskAmount * 3;

    var entryText = document.getElementById('entry') ? document.getElementById('entry').textContent : '-';
    var slText = document.getElementById('sl') ? document.getElementById('sl').textContent : '-';

    var lotSize = 0;
    if (entryText !== '-' && slText !== '-') {
        var entry = parseFloat(entryText);
        var sl = parseFloat(slText);
        var riskPerUnit = Math.abs(entry - sl);
        if (riskPerUnit > 0) lotSize = riskAmount / riskPerUnit;
    }

    document.getElementById('riskAmountCalc').textContent = 'R' + riskAmount.toFixed(2);
    document.getElementById('profitAmountCalc').textContent = 'R' + potentialProfit.toFixed(2);
    document.getElementById('lotSizeCalc').textContent = lotSize > 0 ? lotSize.toFixed(2) + ' units' : 'N/A';

    document.getElementById('riskResult').style.display = 'block';
    showToast('Risk: R' + riskAmount.toFixed(2));
}
