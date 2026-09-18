function showToast(message, type) {
    const toast = document.createElement('div');
    toast.className = 'toast' + (type === 'error' ? ' error' : '');
    toast.textContent = (type === 'success' ? '✓ ' : '✗ ') + message;
    document.body.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 2500);
}

function toggleSetting(element, key) {
    element.classList.toggle('active');
    var settings = JSON.parse(localStorage.getItem('appSettings') || '{}');
    settings[key] = element.classList.contains('active');
    localStorage.setItem('appSettings', JSON.stringify(settings));
    showToast(key.toUpperCase() + ': ' + (element.classList.contains('active') ? 'ON' : 'OFF'));
}

function playSound() {
    try {
        var ctx = new (window.AudioContext || window.webkitAudioContext)();
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 800;
        osc.type = 'sine';
        gain.gain.setValueAtTime(0.3, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.5);
    } catch(e) {}
}

document.addEventListener('DOMContentLoaded', function() {
    var settings = JSON.parse(localStorage.getItem('appSettings') || '{}');
    Object.keys(settings).forEach(function(key) {
        document.querySelectorAll('.toggle').forEach(function(el) {
            if (el.getAttribute('onclick') && el.getAttribute('onclick').indexOf("'" + key + "'") !== -1) {
                if (settings[key]) el.classList.add('active');
                else el.classList.remove('active');
            }
        });
    });
});
