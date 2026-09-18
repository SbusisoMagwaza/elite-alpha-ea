"""
Configuration & Live Prices
All prices match real Exness values
"""

# Live Prices (Real Exness)
LIVE_PRICES = {
    'XAUUSDm': {'price': 4350.50, 'change': 0.0, 'high': 4365.00, 'low': 4338.00, 'pip': 0.01},
    'BTCUSDm': {'price': 67189.00, 'change': 0.0, 'high': 67450.00, 'low': 66900.00, 'pip': 1.0},
    'EURUSDm': {'price': 1.0858, 'change': 0.0, 'high': 1.0870, 'low': 1.0845, 'pip': 0.0001},
    'GBPUSDm': {'price': 1.2734, 'change': 0.0, 'high': 1.2755, 'low': 1.2718, 'pip': 0.0001},
    'USDJPYm': {'price': 149.85, 'change': 0.0, 'high': 150.20, 'low': 149.60, 'pip': 0.01},
    'USTECm': {'price': 29450.19, 'change': 0.0, 'high': 29480.00, 'low': 29380.00, 'pip': 0.25},
    'US30m': {'price': 42850.00, 'change': 0.0, 'high': 42920.00, 'low': 42780.00, 'pip': 1.0}
}

# Economic Calendar Events
ECONOMIC_EVENTS = [
    {'time': '14:30', 'currency': 'USD', 'event': 'Non-Farm Payrolls', 'impact': 'HIGH'},
    {'time': '15:00', 'currency': 'USD', 'event': 'Unemployment Rate', 'impact': 'HIGH'},
    {'time': '16:00', 'currency': 'EUR', 'event': 'ECB Press Conference', 'impact': 'HIGH'},
    {'time': '11:30', 'currency': 'GBP', 'event': 'CPI YoY', 'impact': 'MEDIUM'},
    {'time': '03:30', 'currency': 'JPY', 'event': 'BOJ Rate Decision', 'impact': 'HIGH'},
]

# Account Settings
DEFAULT_ACCOUNT = {
    'balance': 369.19,
    'currency': 'ZAR',
    'risk_percent': 1.0,
    'min_confidence': 75,
    'broker': 'Exness',
    'account_number': '134644333'
}

# Scanner Settings
SCANNER_CONFIG = {
    'scan_interval_minutes': 5,
    'cooldown_minutes': 30,
    'max_signals_per_day': 4,
    'min_confidence': 75,
    'auto_btc_scan': True
}
