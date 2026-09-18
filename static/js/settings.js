function saveSettings() {
    var balance = parseFloat(document.getElementById('accountBalanceInput').value);
    var riskPercent = parseFloat(document.getElementById('riskPercentInput').value);
    var minConfidence = parseInt(document.getElementById('minConfidenceInput').value);
    var scanInterval = parseInt(document.getElementById('scanIntervalInput').value);

    var accountData = {
        balance: balance,
        riskPercent: riskPercent,
        minConfidence: minConfidence,
        scanInterval: scanInterval
    };

    localStorage.setItem('accountData', JSON.stringify(accountData));
    showToast('Settings saved!');
}

function loadSettingsPage() {
    var accountData = JSON.parse(localStorage.getItem('accountData') || '{}');
    if (accountData.balance) document.getElementById('accountBalanceInput').value = accountData.balance;
    if (accountData.riskPercent) document.getElementById('riskPercentInput').value = accountData.riskPercent;
    if (accountData.minConfidence) document.getElementById('minConfidenceInput').value = accountData.minConfidence;
    if (accountData.scanInterval) document.getElementById('scanIntervalInput').value = accountData.scanInterval;

    var settings = JSON.parse(localStorage.getItem('appSettings') || '{}');
    Object.keys(settings).forEach(function(key) {
        document.querySelectorAll('.toggle').forEach(function(el) {
            if (el.getAttribute('onclick') && el.getAttribute('onclick').indexOf("'" + key + "'") !== -1) {
                if (settings[key]) el.classList.add('active');
                else el.classList.remove('active');
            }
        });
    });
}

function exportData() {
    var data = {
        accountData: JSON.parse(localStorage.getItem('accountData') || '{}'),
        appSettings: JSON.parse(localStorage.getItem('appSettings') || '{}'),
        scanHistory: JSON.parse(localStorage.getItem('scanHistory') || '[]'),
        tradeHistory: JSON.parse(localStorage.getItem('tradeHistory') || '[]'),
        exportDate: new Date().toISOString(),
        version: '7.0 PROFESSIONAL'
    };

    var blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = 'elite-alpha-ea-backup-' + Date.now() + '.json';
    a.click();
    URL.revokeObjectURL(url);
    showToast('Backup downloaded!');
}

function importData(event) {
    var file = event.target.files[0];
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function(e) {
        try {
            var data = JSON.parse(e.target.result);
            if (data.accountData) localStorage.setItem('accountData', JSON.stringify(data.accountData));
            if (data.appSettings) localStorage.setItem('appSettings', JSON.stringify(data.appSettings));
            if (data.scanHistory) localStorage.setItem('scanHistory', JSON.stringify(data.scanHistory));
            if (data.tradeHistory) localStorage.setItem('tradeHistory', JSON.stringify(data.tradeHistory));
            showToast('Data restored!');
            setTimeout(function() { location.reload(); }, 1500);
        } catch(err) {
            showToast('Invalid file', 'error');
        }
    };
    reader.readAsText(file);
}

function resetAllData() {
    if (confirm('⚠️ Reset ALL data? Cannot be undone!')) {
        localStorage.clear();
        showToast('All data reset!');
        setTimeout(function() { location.reload(); }, 1000);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadSettingsPage();
});
