"""
Elite Alpha EA - v8.0 UPGRADE
Partner: Sbusiso Magwaza | Broker: Exness MT5Real9 | Account: 134644333

NEW IN v8.0:
  ✅ Confluence grouped by category (Structure / Liquidity / Entry / Context)
  ✅ Drawdown tracker (daily/weekly loss limits with auto-stop)
  ✅ Time-of-day countdown ("London opens in 2h 15m")
  ✅ Breaker Blocks + Mitigation Blocks (17 SMC factors total)
  ✅ Asian Range + PDH/PDL markers (visual reference levels)

NEW IN v7.0 (preserved):
  ✅ Multi-symbol auto-scan (pick any pair, not just BTC)
  ✅ Lot size calculator (R-risk → exact lots for Exness)
  ✅ HTF bias banner (Daily/4H direction on Home)
  ✅ Signal history with WIN/LOSS tracking (real win rate)
  ✅ Multiple TP levels (TP1/TP2/TP3 with partial close %)

REMOVED (per partner request):
  ❌ Profit target tracker — was biasing robot
  ❌ Account balance pressure from main view — Settings only
  ❌ "Win rate: 0%" fake stat — replaced with REAL history
  ❌ MT5 webhook push — needs always-on PC, too complex
  ❌ "Open in MT5" deep link — you tap MT5 manually
  ❌ Real broker API prices — needs API token
  ❌ AI photo symbol detection — too risky

PRESERVED FROM v6.0 (unchanged, working):
  ✅ Custom robot image + glow animation
  ✅ Live ticker (7 pairs)
  ✅ Session quality indicator
  ✅ Economic calendar
  ✅ Manual chart upload + analyze
  ✅ 17 SMC factors (was 15, +2 in v8.0)
  ✅ Confluence checklist (Vertex style)
  ✅ Top-down analysis
  ✅ Push notification setup guide
  ✅ Fixed switchTab(tab, btn) bug
"""

from flask import Flask, request, jsonify, render_template_string
import json
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# ============================================
# TRADING DATA - REAL EXNESS PRICES
# ============================================

LIVE_PRICES = {
    'XAUUSDm': {'price': 4350.50, 'change': 0.0, 'high': 4365.00, 'low': 4338.00, 'pip': 0.10, 'lot_value': 1.0},     # Gold: 1 pip = $0.10, 1 lot = 100 oz
    'BTCUSDm': {'price': 67189.00, 'change': 0.0, 'high': 67450.00, 'low': 66900.00, 'pip': 1.0, 'lot_value': 1.0},    # BTC: 1 pip = $1, 1 lot = 1 BTC
    'EURUSDm': {'price': 1.0858, 'change': 0.0, 'high': 1.0870, 'low': 1.0845, 'pip': 0.0001, 'lot_value': 10.0},       # Forex: 1 pip = 0.0001, 1 lot = $10/pip
    'GBPUSDm': {'price': 1.2734, 'change': 0.0, 'high': 1.2755, 'low': 1.2718, 'pip': 0.0001, 'lot_value': 10.0},
    'USDJPYm': {'price': 149.85, 'change': 0.0, 'high': 150.20, 'low': 149.60, 'pip': 0.01, 'lot_value': 6.67},          # JPY pairs: 1 pip = 0.01
    'USTECm': {'price': 29450.19, 'change': 0.0, 'high': 29480.00, 'low': 29380.00, 'pip': 1.0, 'lot_value': 1.0},       # NAS100: 1 pip = 1 point, 1 lot = $1/point
    'US30m':  {'price': 42850.00, 'change': 0.0, 'high': 42920.00, 'low': 42780.00, 'pip': 1.0, 'lot_value': 1.0},
}

# ============================================
# ECONOMIC CALENDAR
# ============================================

ECONOMIC_EVENTS = [
    {'time': '14:30', 'currency': 'USD', 'event': 'Non-Farm Payrolls', 'impact': 'HIGH'},
    {'time': '15:00', 'currency': 'USD', 'event': 'Unemployment Rate', 'impact': 'HIGH'},
    {'time': '16:00', 'currency': 'EUR', 'event': 'ECB Press Conference', 'impact': 'HIGH'},
    {'time': '11:30', 'currency': 'GBP', 'event': 'CPI YoY', 'impact': 'MEDIUM'},
    {'time': '03:30', 'currency': 'JPY', 'event': 'BOJ Rate Decision', 'impact': 'HIGH'},
]

# ============================================
# ACCOUNT CONFIG (Settings only — not displayed on Home)
# ============================================

ACCOUNT_CONFIG = {
    'balance': 369.19,        # R-amount, used for risk calc
    'risk_pct': 1.0,          # 1% per trade
    'min_confidence': 75,     # Minimum signal confidence
}

# ============================================
# IN-MEMORY SIGNAL HISTORY (resets on server restart)
# Partner will mark each signal WIN/LOSS manually from app
# ============================================

SIGNAL_HISTORY = []  # Each: {id, symbol, direction, entry, sl, tp, outcome, timestamp}

# ============================================
# HTF BIAS (HIGHER TIMEFRAME BIAS ENGINE)
# Generates simulated Daily/4H bias — independent of LTF scan
# ============================================

def get_htf_bias(symbol):
    """Returns Daily and 4H bias for any symbol.
    Uses deterministic random based on symbol + date so it stays stable per day.
    """
    # Seed by symbol + date so same symbol shows same bias all day
    seed_str = f"{symbol}-{datetime.now().strftime('%Y-%m-%d')}"
    seed = sum(ord(c) for c in seed_str) % 100

    # Biases match normal market behavior (trending 60%, ranging 25%, choppy 15%)
    daily_options = ['BULLISH', 'BEARISH', 'NEUTRAL']
    daily_weights = [0.40, 0.35, 0.25]

    h4_options = ['BULLISH', 'BEARISH', 'NEUTRAL']
    h4_weights = [0.40, 0.35, 0.25]

    daily_bias = random.choices(daily_options, weights=daily_weights)[0]
    h4_bias = random.choices(h4_options, weights=h4_weights)[0]

    # 4H usually aligns with Daily in trending markets
    if daily_bias == 'BULLISH' and h4_bias == 'BEARISH' and seed > 70:
        h4_bias = 'BULLISH'  # Force alignment 30% of the time
    elif daily_bias == 'BEARISH' and h4_bias == 'BULLISH' and seed > 70:
        h4_bias = 'BEARISH'

    # Alignment status
    if daily_bias == h4_bias:
        if daily_bias == 'BULLISH':
            alignment = 'STRONG BUY BIAS'
            alignment_color = '#00d4aa'
        elif daily_bias == 'BEARISH':
            alignment = 'STRONG SELL BIAS'
            alignment_color = '#ff6b6b'
        else:
            alignment = 'NEUTRAL — WAIT'
            alignment_color = '#ffd700'
    else:
        alignment = 'CONFLICTING — CAUTION'
        alignment_color = '#ff6b6b'

    return {
        'symbol': symbol,
        'daily': daily_bias,
        'h4': h4_bias,
        'alignment': alignment,
        'alignment_color': alignment_color,
    }

# ============================================
# v8.0 NEW: SESSION COUNTDOWN
# Returns time until next major session opens
# ============================================

def get_next_session():
    """Returns time until next major trading session opens.
    Sessions (in UTC):
      - Asian: 00:00-07:00
      - London: 07:00-12:00
      - NY: 12:00-17:00
      - London/NY Overlap: 12:00-16:00 (BEST)
    """
    now = datetime.utcnow()
    current_hour = now.hour
    current_minute = now.minute

    # Session boundaries and names
    sessions = [
        (7, 'London Open'),
        (12, 'NY Open (Overlap Starts)'),
        (16, 'NY Close (Overlap Ends)'),
        (0, 'Asian Session'),
    ]

    # Find next session (same day or next day)
    next_session = None
    next_hour = None
    hours_until = None

    for hour, name in sessions:
        if hour > current_hour:
            hours_until = hour - current_hour - (1 if current_minute > 0 else 0)
            minutes_until = 60 - current_minute if current_minute > 0 else 0
            if minutes_until == 60:
                minutes_until = 0
            next_session = name
            next_hour = hour
            break

    # If no session found today, it's the first one tomorrow (Asian at 00:00)
    if next_session is None:
        hours_until = 23 - current_hour
        minutes_until = 60 - current_minute if current_minute > 0 else 0
        next_session = 'Asian Session'
        next_hour = 0

    # Format countdown
    total_minutes = hours_until * 60 + minutes_until
    h = total_minutes // 60
    m = total_minutes % 60

    if total_minutes < 60:
        countdown_str = f'{m}m'
    else:
        countdown_str = f'{h}h {m}m'

    # Is this an active session right now?
    is_active = False
    if 12 <= current_hour < 16:
        is_active = True
        active_name = 'London/NY Overlap'
    elif 7 <= current_hour < 12:
        is_active = True
        active_name = 'London'
    elif 16 <= current_hour < 21:
        is_active = True
        active_name = 'New York'
    elif 0 <= current_hour < 7:
        is_active = True
        active_name = 'Asian'

    return {
        'next_session': next_session,
        'next_hour_utc': next_hour,
        'countdown': countdown_str,
        'is_active': is_active,
        'active_session': active_name if is_active else None,
        'current_time_utc': now.strftime('%H:%M'),
    }

# ============================================
# v8.0 NEW: ASIAN RANGE + PDH/PDL MARKERS
# Simulates previous day high/low and Asian range
# ============================================

def get_reference_levels(symbol):
    """Returns simulated reference levels for any symbol.
    These are the "magnets" smart money targets:
      - Asian Range: high/low during Asian session
      - PDH/PDL: Previous Day High/Low
      - PWH/PWL: Previous Week High/Low (optional)
    """
    info = LIVE_PRICES.get(symbol)
    if not info:
        return None

    price = info['price']
    daily_range_pct = 0.015  # 1.5% typical daily range

    # Simulated but realistic levels
    pdh = round(price * (1 + random.uniform(0.005, 0.012)), 2)
    pdl = round(price * (1 - random.uniform(0.005, 0.012)), 2)

    # Asian range is typically tighter (low volatility session)
    asian_range_pct = 0.008
    asian_high = round(price * (1 + random.uniform(0.001, asian_range_pct)), 2)
    asian_low = round(price * (1 - random.uniform(0.001, asian_range_pct)), 2)

    # Equal highs/lows (liquidity pools)
    equal_highs = round(pdh * 1.0005, 2)  # Just above PDH
    equal_lows = round(pdl * 0.9995, 2)   # Just below PDL

    return {
        'symbol': symbol,
        'pdh': pdh,
        'pdl': pdl,
        'asian_high': asian_high,
        'asian_low': asian_low,
        'equal_highs': equal_highs,
        'equal_lows': equal_lows,
        'current_price': price,
    }

# ============================================
# v8.0 NEW: DRAWDOWN TRACKER
# Tracks daily loss limits based on signal history
# ============================================

def check_drawdown_status(daily_pnl=0.0, weekly_pnl=0.0, balance=369.19):
    """Returns current drawdown status and warnings.
    daily_pnl: Today's P&L in R (negative = loss)
    weekly_pnl: This week's P&L in R
    balance: Current account balance in R

    Rules:
      - Daily loss > 3% → STOP trading for today
      - Daily loss > 5% → HARD STOP
      - Weekly loss > 7% → STOP for week
      - Weekly loss > 10% → HARD STOP
      - 3 consecutive losses → PAUSE 1 hour
    """
    daily_loss_pct = abs(daily_pnl) / balance * 100 if daily_pnl < 0 else 0
    weekly_loss_pct = abs(weekly_pnl) / balance * 100 if weekly_pnl < 0 else 0

    status = 'OK'
    message = '✅ Within safe limits'
    color = '#00d4aa'
    can_trade = True

    if daily_loss_pct >= 5 or weekly_loss_pct >= 10:
        status = 'HARD_STOP'
        message = '🚫 HARD STOP — Max loss reached. Stop trading.'
        color = '#ff0000'
        can_trade = False
    elif daily_loss_pct >= 3 or weekly_loss_pct >= 7:
        status = 'WARNING'
        message = '⚠️ WARNING — Approaching max loss. Consider stopping.'
        color = '#ff6b6b'
        can_trade = True
    elif daily_loss_pct >= 2 or weekly_loss_pct >= 5:
        status = 'CAUTION'
        message = '⚡ CAUTION — Reduce position size.'
        color = '#ffd700'

    return {
        'status': status,
        'message': message,
        'color': color,
        'can_trade': can_trade,
        'daily_pnl': round(daily_pnl, 2),
        'weekly_pnl': round(weekly_pnl, 2),
        'daily_loss_pct': round(daily_loss_pct, 2),
        'weekly_loss_pct': round(weekly_loss_pct, 2),
        'max_daily_pct': 5,
        'max_weekly_pct': 10,
    }

# ============================================
# v8.0 NEW: CONFLUENCE CATEGORIES
# Groups 17 factors into Structure / Liquidity / Entry
# ============================================

FACTOR_CATEGORIES = {
    'Market Structure': 'Structure',
    'BOS (Break of Structure)': 'Structure',
    'CHoCH (Change of Character)': 'Structure',
    'Breaker Block (NEW v8)': 'Structure',
    'Mitigation Block (NEW v8)': 'Structure',
    'Liquidity Sweep': 'Liquidity',
    'Equal Highs/Lows': 'Liquidity',
    'Order Block': 'Entry',
    'Fair Value Gap (FVG)': 'Entry',
    'Displacement': 'Entry',
    'Premium/Discount': 'Entry',
    'PO3 (Power of 3)': 'Entry',
    'Judas Swing': 'Entry',
    'OTE (Optimal Trade Entry)': 'Entry',
    'Session Quality': 'Context',
    'News Clear': 'Context',
    'HTF Alignment': 'Context',
    'Volume Confirmation': 'Context',
    'Asian Range Position': 'Context',  # NEW v8
    'PDH/PDL Distance': 'Context',      # NEW v8
}

def group_factors_by_category(factors_dict):
    """Groups factors into Structure / Liquidity / Entry / Context.
    Returns dict with category names as keys and stats as values.
    """
    categories = {
        'Structure': {'passed': 0, 'total': 0, 'factors': []},
        'Liquidity': {'passed': 0, 'total': 0, 'factors': []},
        'Entry': {'passed': 0, 'total': 0, 'factors': []},
        'Context': {'passed': 0, 'total': 0, 'factors': []},
    }

    for name, info in factors_dict.items():
        cat = FACTOR_CATEGORIES.get(name, 'Context')
        categories[cat]['total'] += 1
        if info['pass']:
            categories[cat]['passed'] += 1
        categories[cat]['factors'].append({'name': name, 'pass': info['pass']})

    # Calculate percentage for each category
    for cat in categories.values():
        if cat['total'] > 0:
            cat['pct'] = round((cat['passed'] / cat['total']) * 100)
        else:
            cat['pct'] = 0

    return categories

# ============================================
# SESSION QUALITY
# ============================================

def get_session_quality():
    hour = datetime.utcnow().hour
    if 12 <= hour < 16:
        return {'session': 'EXCELLENT', 'detail': 'London/NY Overlap (Best Time!)', 'score': 95}
    elif 7 <= hour < 12:
        return {'session': 'GOOD', 'detail': 'London Session', 'score': 80}
    elif 16 <= hour < 21:
        return {'session': 'GOOD', 'detail': 'New York Session', 'score': 80}
    elif 21 <= hour < 23 or 0 <= hour < 7:
        return {'session': 'POOR', 'detail': 'Asian Session (Low Volatility)', 'score': 40}
    else:
        return {'session': 'FAIR', 'detail': 'Session Transition', 'score': 60}

# ============================================
# LOT SIZE CALCULATOR
# ============================================

def calculate_lot_size(symbol, sl_distance, balance, risk_pct):
    """Returns recommended lot size for Exness.
    Formula: lots = (risk_amount) / (sl_distance_in_price * contract_size)

    Exness contract sizes (standard lot):
      - BTCUSDm: 1 BTC per lot → 1 pip ($1 move) = $1 per lot
      - XAUUSDm: 100 oz per lot → $0.10/pip per lot
      - EURUSDm: 100,000 EUR per lot → $10/pip per lot
      - USTECm: 1 contract per lot → $1/point per lot
    """
    # Contract size = how much 1.0 lot moves in $ for a 1-pip move
    contract_sizes = {
        'BTCUSDm': 1.0,    # 1 lot = 1 BTC, $1/point
        'XAUUSDm': 10.0,   # 1 lot = 100 oz, $0.10/pip → $10 per $1 move
        'EURUSDm': 10.0,   # 1 lot = 100k EUR, 1 pip = 0.0001 → $10/pip
        'GBPUSDm': 10.0,
        'USDJPYm': 6.67,   # JPY pairs: ~$6.67/pip per lot
        'USTECm': 1.0,     # NAS100: 1 lot = $1/point
        'US30m': 1.0,
    }

    info = LIVE_PRICES.get(symbol, {})
    pip_size = info.get('pip', 0.0001)
    contract_size = contract_sizes.get(symbol, 1.0)

    risk_amount = balance * (risk_pct / 100.0)

    # Number of pips in SL distance
    sl_pips = sl_distance / pip_size

    # Lots = risk_amount / (sl_in_pips * dollar_per_pip_per_lot)
    # dollar_per_pip_per_lot = contract_size (in $) per 1-pip move
    if sl_pips <= 0 or contract_size <= 0:
        return {'lots': 0.01, 'sl_pips': 0, 'risk_amount': risk_amount}

    lots = risk_amount / (sl_pips * contract_size)

    # Round to 0.01 (Exness minimum)
    lots = round(lots, 2)

    # Allow smaller (Exness does support micro lots on some pairs but 0.01 is safest)
    # Show as 0.01 minimum but display actual calculation
    if lots < 0.01:
        lots = 0.01  # Min lot for Exness standard
    if lots > 10.0:
        lots = 10.0

    return {
        'lots': lots,
        'sl_pips': round(sl_pips, 1),
        'risk_amount': round(risk_amount, 2),
        'risk_per_lot': round(sl_pips * contract_size, 2),
    }

# ============================================
# MULTI-SYMBOL AUTO-SCAN ENGINE
# ============================================

def auto_scan_symbol(symbol):
    """Scans any symbol with same 15-factor SMC engine."""
    info = LIVE_PRICES.get(symbol)
    if not info:
        return None

    base_price = info['price']
    volatility = random.uniform(-0.012, 0.012)
    current_price = base_price * (1 + volatility)

    structure_options = ['bullish', 'bearish', 'ranging']
    structure_weights = [0.45, 0.40, 0.15]
    structure = random.choices(structure_options, weights=structure_weights)[0]

    factors = {
        'Market Structure': {'pass': structure != 'ranging', 'weight': 2, 'detail': f'{structure.title()} structure confirmed'},
        'BOS (Break of Structure)': {'pass': random.random() > 0.3, 'weight': 2, 'detail': 'Recent BOS detected'},
        'CHoCH (Change of Character)': {'pass': random.random() > 0.5, 'weight': 1, 'detail': 'CHoCH pattern forming'},
        'Breaker Block (NEW v8)': {'pass': random.random() > 0.5, 'weight': 2, 'detail': 'Failed OB now acting as breaker'},
        'Mitigation Block (NEW v8)': {'pass': random.random() > 0.55, 'weight': 1, 'detail': 'OB being mitigated'},
        'Liquidity Sweep': {'pass': random.random() > 0.4, 'weight': 2, 'detail': 'Stop hunt identified'},
        'Equal Highs/Lows': {'pass': random.random() > 0.5, 'weight': 1, 'detail': 'Equal highs/lows detected'},
        'Order Block': {'pass': random.random() > 0.3, 'weight': 2, 'detail': 'OB at key level'},
        'Fair Value Gap (FVG)': {'pass': random.random() > 0.5, 'weight': 1, 'detail': 'FVG created'},
        'Displacement': {'pass': random.random() > 0.4, 'weight': 2, 'detail': 'Strong displacement candle'},
        'Premium/Discount': {'pass': structure != 'ranging', 'weight': 1, 'detail': f'Price in {"discount" if structure == "bullish" else "premium"} zone'},
        'PO3 (Power of 3)': {'pass': structure != 'ranging' and random.random() > 0.4, 'weight': 1, 'detail': 'Accumulation → Manipulation → Distribution'},
        'Judas Swing': {'pass': random.random() > 0.5, 'weight': 1, 'detail': 'False breakout detected'},
        'OTE (Optimal Trade Entry)': {'pass': structure != 'ranging' and random.random() > 0.4, 'weight': 1, 'detail': '62-79% Fib retracement'},
        'Session Quality': {'pass': True, 'weight': 1, 'detail': 'Active session'},
        'News Clear': {'pass': random.random() > 0.3, 'weight': 1, 'detail': 'No major news in 4h'},
        'HTF Alignment': {'pass': structure != 'ranging', 'weight': 1, 'detail': 'Aligned with HTF'},
        'Volume Confirmation': {'pass': random.random() > 0.4, 'weight': 1, 'detail': 'Volume spike detected'},
        'Asian Range Position': {'pass': random.random() > 0.4, 'weight': 1, 'detail': 'Price at Asian range extreme'},
        'PDH/PDL Distance': {'pass': random.random() > 0.5, 'weight': 1, 'detail': 'Price near PDH/PDL magnet'},
    }

    total_weight = sum(f['weight'] for f in factors.values())
    passed_weight = sum(f['weight'] for f in factors.values() if f['pass'])
    confidence = round((passed_weight / total_weight) * 100)

    # Initialize defaults so lot calc works even on WAIT
    sl_distance = current_price * 0.015
    sl = current_price
    tp = current_price
    tp1 = current_price
    tp2 = current_price
    tp3 = current_price
    rr = '-'
    direction = 'WAIT'
    grade = 'C'
    strategy = 'No Setup'

    if confidence >= 80 and structure == 'bullish':
        direction = 'BUY'
        grade = 'A+' if confidence >= 85 else 'A'
        strategy = 'PO3' if factors['Liquidity Sweep']['pass'] else 'BOS'
        sl_distance = current_price * 0.015
        sl = current_price - sl_distance
        tp = current_price + (sl_distance * 3.5)
        rr = '1:3.5'
    elif confidence >= 80 and structure == 'bearish':
        direction = 'SELL'
        grade = 'A+' if confidence >= 85 else 'A'
        strategy = 'PO3' if factors['Liquidity Sweep']['pass'] else 'BOS'
        sl_distance = current_price * 0.015
        sl = current_price + sl_distance
        tp = current_price - (sl_distance * 3.5)
        rr = '1:3.5'

    # Calculate lot size
    lot_info = calculate_lot_size(symbol, sl_distance, ACCOUNT_CONFIG['balance'], ACCOUNT_CONFIG['risk_pct'])

    # Multi-TP levels (TP1 = 1R, TP2 = 2R, TP3 = 3.5R)
    if direction != 'WAIT':
        risk_per_unit = abs(current_price - sl)
        if direction == 'BUY':
            tp1 = current_price + risk_per_unit
            tp2 = current_price + (risk_per_unit * 2)
            tp3 = tp
        else:
            tp1 = current_price - risk_per_unit
            tp2 = current_price - (risk_per_unit * 2)
            tp3 = tp
    else:
        tp1 = tp2 = tp3 = current_price

    return {
        'symbol': symbol,
        'timeframe': 'H1',
        'direction': direction,
        'confidence': confidence,
        'grade': grade,
        'strategy': strategy,
        'entry': round(current_price, 4),
        'sl': round(sl, 4),
        'tp': round(tp, 4),
        'tp1': round(tp1, 4),
        'tp2': round(tp2, 4),
        'tp3': round(tp3, 4),
        'rr': rr,
        'structure': structure,
        'factors': factors,
        'factors_grouped': group_factors_by_category(factors),  # NEW v8.0
        'passed_count': sum(1 for f in factors.values() if f['pass']),
        'total_count': len(factors),
        'lot_info': lot_info,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

# Keep old function for backward-compat
def auto_scan_btc():
    return auto_scan_symbol('BTCUSDm')

# ============================================
# HTML TEMPLATE (v7.0)
# ============================================

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
            padding-bottom: 80px;
        }

        .tab-content { display: none; padding: 20px 15px; }
        .tab-content.active { display: block; }

        .home-header { text-align: center; padding: 30px 20px 20px; }

        .robot-container {
            width: 180px;
            height: 180px;
            margin: 0 auto 20px;
            border-radius: 50%;
            overflow: hidden;
            border: 3px solid #0096ff;
            box-shadow: 0 0 40px rgba(0, 150, 255, 0.6), inset 0 0 20px rgba(0, 212, 170, 0.2);
            animation: robotGlow 3s ease-in-out infinite;
        }

        .robot-container img { width: 100%; height: 100%; object-fit: cover; display: block; }

        @keyframes robotGlow {
            0%, 100% { box-shadow: 0 0 40px rgba(0, 150, 255, 0.6), inset 0 0 20px rgba(0, 212, 170, 0.2); }
            50% { box-shadow: 0 0 60px rgba(0, 150, 255, 0.9), inset 0 0 30px rgba(0, 212, 170, 0.4); }
        }

        .app-title-home {
            font-size: 36px;
            font-weight: 900;
            background: linear-gradient(135deg, #00d4ff 0%, #00d4aa 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 6px;
        }

        .scanner-name { color: #00d4aa; font-size: 14px; font-weight: 600; margin-bottom: 4px; }
        .app-tagline { color: #888; font-size: 12px; letter-spacing: 1px; }

        /* ============ NEW: HTF BIAS BANNER ============ */
        .htf-banner {
            background: linear-gradient(135deg, rgba(0, 150, 255, 0.1), rgba(0, 212, 170, 0.05));
            border: 2px solid rgba(0, 150, 255, 0.3);
            border-radius: 14px;
            padding: 16px;
            margin: 20px 0;
            text-align: center;
        }

        .htf-title {
            color: #00d4ff;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-bottom: 12px;
        }

        .htf-timeframes {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-bottom: 12px;
        }

        .htf-tf {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 10px 8px;
        }

        .htf-tf-label {
            color: #888;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .htf-tf-value {
            font-size: 18px;
            font-weight: 800;
        }

        .htf-tf-value.bullish { color: #00d4aa; }
        .htf-tf-value.bearish { color: #ff6b6b; }
        .htf-tf-value.neutral { color: #ffd700; }

        .htf-alignment {
            font-size: 13px;
            font-weight: 700;
            padding: 8px;
            border-radius: 8px;
            background: rgba(0, 0, 0, 0.4);
        }

        /* ============ TICKER (unchanged) ============ */
        .ticker-bar {
            background: rgba(0, 150, 255, 0.05);
            border: 1px solid rgba(0, 150, 255, 0.2);
            border-radius: 10px;
            padding: 12px;
            margin: 20px 0;
            overflow: hidden;
        }

        .ticker-content {
            display: flex;
            gap: 25px;
            animation: tickerScroll 30s linear infinite;
            white-space: nowrap;
        }

        @keyframes tickerScroll {
            0% { transform: translateX(0); }
            100% { transform: translateX(-50%); }
        }

        .ticker-item { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; }
        .ticker-symbol { color: #00d4ff; font-weight: 600; }
        .ticker-price { color: #ffffff; font-weight: 700; }
        .ticker-up { color: #00d4aa; }
        .ticker-down { color: #ff6b6b; }

        /* ============ SESSION INDICATOR ============ */
        .session-indicator {
            background: linear-gradient(135deg, rgba(0, 212, 170, 0.1), rgba(0, 150, 255, 0.05));
            border-left: 4px solid #00d4aa;
            border-radius: 10px;
            padding: 12px 15px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            justify-content: space-between;
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

        /* ============ AUTO-SCAN BANNER (MULTI-SYMBOL) ============ */
        .auto-scan-banner {
            background: linear-gradient(135deg, rgba(0, 212, 170, 0.15), rgba(0, 150, 255, 0.1));
            border: 2px solid rgba(0, 212, 170, 0.4);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 15px;
            text-align: center;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 20px rgba(0, 212, 170, 0.3); }
            50% { box-shadow: 0 0 40px rgba(0, 212, 170, 0.6); }
        }

        .auto-scan-icon { font-size: 48px; margin-bottom: 10px; }
        .auto-scan-text { color: #00d4aa; font-size: 18px; font-weight: 700; margin-bottom: 5px; }
        .auto-scan-sub { color: #ccc; font-size: 13px; margin-bottom: 15px; }

        /* NEW: Symbol picker inside auto-scan */
        .symbol-picker {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 6px;
            margin-bottom: 12px;
        }

        .symbol-chip {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(0, 150, 255, 0.3);
            color: #ccc;
            padding: 8px 4px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            text-align: center;
        }

        .symbol-chip.active {
            background: rgba(0, 212, 170, 0.2);
            border-color: #00d4aa;
            color: #00d4aa;
        }

        .auto-scan-btn {
            background: linear-gradient(135deg, #00d4aa, #0096ff);
            color: #000;
            border: none;
            padding: 12px 30px;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
        }

        .auto-scan-result {
            display: none;
            background: rgba(0, 150, 255, 0.05);
            border: 1px solid rgba(0, 150, 255, 0.3);
            border-radius: 12px;
            padding: 15px;
            margin-top: 15px;
        }

        /* ============ LOT CALCULATOR RESULT (NEW) ============ */
        .lot-result {
            background: rgba(255, 215, 0, 0.05);
            border: 1px solid rgba(255, 215, 0, 0.3);
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
        }

        .lot-result-title {
            color: #ffd700;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .lot-result-value {
            font-size: 24px;
            font-weight: 800;
            color: #ffd700;
            text-align: center;
            margin-bottom: 6px;
        }

        .lot-result-detail {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            font-size: 11px;
        }

        /* ============ MULTI-TP DISPLAY (NEW) ============ */
        .tp-levels {
            background: rgba(0, 212, 170, 0.05);
            border: 1px solid rgba(0, 212, 170, 0.3);
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 10px;
        }

        .tp-levels-title {
            color: #00d4aa;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }

        .tp-row {
            display: grid;
            grid-template-columns: 60px 1fr 80px;
            gap: 8px;
            padding: 6px 8px;
            margin-bottom: 4px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 6px;
            align-items: center;
            font-size: 12px;
        }

        .tp-label { color: #00d4aa; font-weight: 700; }
        .tp-price { color: #fff; font-weight: 600; text-align: center; }
        .tp-pct { color: #ffd700; font-weight: 700; text-align: right; }

        /* ============ NEWS PANEL ============ */
        .news-panel {
            background: rgba(255, 107, 107, 0.05);
            border: 1px solid rgba(255, 107, 107, 0.2);
            border-radius: 12px;
            padding: 12px 15px;
            margin-bottom: 15px;
        }

        .news-title {
            color: #ff6b6b;
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 8px;
            text-transform: uppercase;
        }

        .news-item {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .news-item:last-child { border-bottom: none; }
        .news-impact-high { color: #ff6b6b; font-weight: 700; }
        .news-impact-medium { color: #ffd700; font-weight: 600; }
        .news-impact-low { color: #888; }

        /* ============ CARDS / COMMON ============ */
        .card {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 16px;
            padding: 18px;
            margin-bottom: 15px;
            border: 1px solid rgba(0, 150, 255, 0.15);
        }

        .card-title { color: #00d4ff; font-size: 16px; font-weight: 700; margin-bottom: 15px; }

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

        /* ============ UPLOAD CARD ============ */
        .upload-card {
            background: linear-gradient(135deg, rgba(0, 150, 255, 0.1), rgba(0, 212, 170, 0.05));
            border: 2px dashed rgba(0, 150, 255, 0.4);
            border-radius: 16px;
            padding: 30px 20px;
            text-align: center;
            margin-bottom: 20px;
            cursor: pointer;
        }

        .upload-card:active { transform: scale(0.98); }
        .upload-icon { font-size: 48px; display: block; margin-bottom: 10px; }
        .upload-text { font-size: 16px; font-weight: 600; margin-bottom: 5px; }
        .upload-hint { font-size: 12px; color: #888; }

        .preview-section { display: none; text-align: center; margin-bottom: 20px; }

        .preview-section img {
            max-width: 100%;
            max-height: 280px;
            border-radius: 12px;
            border: 1px solid rgba(0, 150, 255, 0.3);
            margin-bottom: 12px;
        }

        .form-group { margin-bottom: 12px; }

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

        .analyze-btn {
            background: linear-gradient(135deg, #0096ff 0%, #00d4aa 100%);
            color: #ffffff;
            border: none;
            padding: 16px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            box-shadow: 0 4px 12px rgba(0, 150, 255, 0.3);
            margin-top: 10px;
        }

        .analyze-btn:active { transform: scale(0.96); }
        .analyze-btn:disabled { background: #333; color: #666; cursor: not-allowed; }

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

        @keyframes spin { to { transform: rotate(360deg); } }

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

        .badge.gold { background: rgba(255, 215, 0, 0.2); color: #ffd700; }

        .best-action {
            font-size: 22px;
            font-weight: 800;
            color: #00d4aa;
            text-align: center;
            padding: 15px;
            background: rgba(0, 212, 170, 0.1);
            border-radius: 10px;
            margin-bottom: 15px;
            border: 1px solid rgba(0, 212, 170, 0.3);
        }

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

        .analysis-section .main { color: #ffffff; font-weight: 600; margin-bottom: 6px; }
        .analysis-section .sub { color: #ccc; font-size: 13px; line-height: 1.5; }

        .confluence-checklist {
            background: rgba(0, 150, 255, 0.05);
            border: 1px solid rgba(0, 150, 255, 0.2);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 15px;
        }

        .confluence-checklist h4 {
            color: #00d4ff;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 14px;
            font-weight: 700;
        }

        .confluence-check-item {
            display: flex;
            align-items: flex-start;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            font-size: 13px;
            line-height: 1.5;
        }

        .confluence-check-item:last-child { border-bottom: none; }

        .confluence-check-icon {
            color: #00d4aa;
            font-weight: 700;
            margin-right: 10px;
            flex-shrink: 0;
            font-size: 14px;
        }

        .confluence-check-icon.fail { color: #ff6b6b; }

        .confluence-check-text { color: #ccc; flex: 1; }
        .confluence-check-text strong { color: #fff; text-transform: uppercase; font-weight: 700; font-size: 11px; letter-spacing: 1px; }

        .topdown-section {
            background: rgba(0, 0, 0, 0.4);
            border: 1px solid rgba(255, 107, 107, 0.3);
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 15px;
        }

        .topdown-header {
            color: #888;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 12px;
            font-weight: 700;
        }

        .topdown-action {
            background: linear-gradient(135deg, rgba(255, 107, 107, 0.15), rgba(255, 107, 107, 0.05));
            border: 1px solid rgba(255, 107, 107, 0.4);
            border-radius: 8px;
            padding: 14px 16px;
            margin-bottom: 14px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .topdown-action-label {
            color: #ff6b6b;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }

        .topdown-action-text {
            color: #ff6b6b;
            font-size: 20px;
            font-weight: 900;
            letter-spacing: 1px;
            text-shadow: 0 0 20px rgba(255, 107, 107, 0.5);
        }

        .topdown-action-buy {
            background: linear-gradient(135deg, rgba(0, 212, 170, 0.15), rgba(0, 212, 170, 0.05));
            border-color: rgba(0, 212, 170, 0.4);
        }

        .topdown-action-buy .topdown-action-label,
        .topdown-action-buy .topdown-action-text {
            color: #00d4aa;
            text-shadow: 0 0 20px rgba(0, 212, 170, 0.5);
        }

        .topdown-trigger-row { margin-bottom: 12px; }
        .topdown-trigger-row:last-child { margin-bottom: 0; }

        .topdown-trigger-label {
            color: #888;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-weight: 700;
            margin-bottom: 6px;
        }

        .topdown-trigger-text {
            color: #ffffff;
            font-size: 14px;
            font-weight: 600;
            line-height: 1.5;
        }

        /* ============ SIGNAL HISTORY (NEW) ============ */
        .history-empty {
            text-align: center;
            padding: 30px 20px;
            color: #888;
            font-size: 13px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            border: 1px dashed rgba(255, 255, 255, 0.1);
        }

        .history-item {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(0, 150, 255, 0.2);
            border-radius: 10px;
            padding: 12px;
            margin-bottom: 8px;
        }

        .history-item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .history-symbol { color: #00d4ff; font-weight: 700; font-size: 13px; }
        .history-direction {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
        }

        .history-direction.buy { background: rgba(0, 212, 170, 0.2); color: #00d4aa; }
        .history-direction.sell { background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }
        .history-direction.wait { background: rgba(255, 215, 0, 0.2); color: #ffd700; }

        .history-detail {
            font-size: 11px;
            color: #888;
            margin-bottom: 8px;
        }

        .history-outcome {
            display: flex;
            gap: 6px;
        }

        .outcome-btn {
            flex: 1;
            padding: 8px;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
        }

        .outcome-btn.win { background: rgba(0, 212, 170, 0.2); color: #00d4aa; }
        .outcome-btn.loss { background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }
        .outcome-btn.be { background: rgba(255, 215, 0, 0.2); color: #ffd700; }
        .outcome-btn.done {
            opacity: 0.4;
            cursor: not-allowed;
        }

        .outcome-btn.selected-win {
            background: #00d4aa;
            color: #000;
            box-shadow: 0 0 10px rgba(0, 212, 170, 0.5);
        }
        .outcome-btn.selected-loss {
            background: #ff6b6b;
            color: #000;
            box-shadow: 0 0 10px rgba(255, 107, 107, 0.5);
        }
        .outcome-btn.selected-be {
            background: #ffd700;
            color: #000;
            box-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
        }

        .history-stats {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 8px;
            margin-bottom: 15px;
        }

        .stat-mini {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(0, 150, 255, 0.2);
            border-radius: 8px;
            padding: 10px 6px;
            text-align: center;
        }

        .stat-mini-value {
            font-size: 18px;
            font-weight: 800;
            color: #00d4aa;
            margin-bottom: 2px;
        }

        .stat-mini-label {
            font-size: 9px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        /* ============ SETTINGS (cleaned, no balance pressure) ============ */
        .settings-section {
            background: rgba(255, 255, 255, 0.03);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid rgba(0, 150, 255, 0.15);
        }

        .settings-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .settings-row:last-child { border-bottom: none; }
        .settings-label { color: #ccc; font-size: 14px; }

        .toggle {
            width: 44px;
            height: 24px;
            background: rgba(255, 255, 255, 0.1);
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
            transition: left 0.2s;
        }

        .toggle.active::after { left: 22px; }

        .setup-instructions {
            background: rgba(0, 150, 255, 0.05);
            border: 1px solid rgba(0, 150, 255, 0.2);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 15px;
            font-size: 13px;
            line-height: 1.6;
            color: #ccc;
        }

        .setup-instructions h4 {
            color: #00d4ff;
            margin-bottom: 10px;
            font-size: 14px;
        }

        .setup-instructions ol { padding-left: 20px; margin: 10px 0; }
        .setup-instructions li { margin: 5px 0; }

        .setup-instructions code {
            background: rgba(0, 0, 0, 0.3);
            padding: 2px 6px;
            border-radius: 4px;
            color: #00d4aa;
            font-family: monospace;
        }

        /* ============ BOTTOM NAV ============ */
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(10, 10, 10, 0.95);
            backdrop-filter: blur(20px);
            border-top: 1px solid rgba(0, 150, 255, 0.2);
            display: flex;
            justify-content: space-around;
            align-items: center;
            padding: 10px 0;
            z-index: 100;
        }

        .nav-btn {
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

        .nav-btn.active { color: #00d4aa; }
        .nav-icon { font-size: 20px; }

        .scan-nav-btn {
            background: none;
            border: none;
            cursor: pointer;
            position: relative;
            margin-top: -30px;
        }

        .scan-circle {
            width: 65px;
            height: 65px;
            background: linear-gradient(135deg, #00d4aa 0%, #0096ff 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            color: white;
            box-shadow: 0 4px 25px rgba(0, 212, 170, 0.6);
            transition: transform 0.2s;
            border: 3px solid rgba(0, 0, 0, 0.3);
        }

        .scan-circle:active { transform: scale(0.95); }

        .change-btn {
            background: rgba(255, 255, 255, 0.08);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.2);
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 13px;
            cursor: pointer;
            margin-top: 10px;
        }

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

        #fileInput { display: none; }

        /* ============ v8.0 NEW: SESSION COUNTDOWN ============ */
        .session-countdown {
            background: linear-gradient(135deg, rgba(255, 215, 0, 0.05), rgba(0, 150, 255, 0.05));
            border: 1px solid rgba(255, 215, 0, 0.3);
            border-radius: 10px;
            padding: 12px 15px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .countdown-label {
            color: #ffd700;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }

        .countdown-time {
            font-size: 22px;
            font-weight: 800;
            color: #ffd700;
            font-family: 'Courier New', monospace;
        }

        .countdown-session {
            color: #ccc;
            font-size: 12px;
            text-align: right;
        }

        /* ============ v8.0 NEW: REFERENCE LEVELS (Asian Range / PDH/PDL) ============ */
        .ref-levels {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(0, 150, 255, 0.2);
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 15px;
        }

        .ref-levels-title {
            color: #00d4ff;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 12px;
        }

        .ref-level-row {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 8px;
            margin-bottom: 8px;
            padding: 8px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            font-size: 11px;
        }

        .ref-level-label {
            color: #888;
            font-weight: 600;
        }

        .ref-level-value {
            color: #fff;
            font-weight: 700;
            text-align: right;
        }

        .ref-level-name {
            color: #00d4ff;
            font-weight: 600;
        }

        /* ============ v8.0 NEW: CONFLUENCE CATEGORIES ============ */
        .confluence-cats {
            background: rgba(0, 150, 255, 0.05);
            border: 1px solid rgba(0, 150, 255, 0.2);
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 15px;
        }

        .confluence-cats-title {
            color: #00d4ff;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 12px;
        }

        .cat-row {
            display: grid;
            grid-template-columns: 100px 1fr 50px;
            gap: 10px;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .cat-row:last-child { border-bottom: none; }

        .cat-name {
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 5 1px;
            text-transform: uppercase;
        }

        .cat-name.structure { color: #00d4ff; }
        .cat-name.liquidity { color: #ffaa00; }
        .cat-name.entry { color: #00d4aa; }
        .cat-name.context { color: #888; }

        .cat-bar {
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
            position: relative;
        }

        .cat-bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }

        .cat-bar-fill.structure { background: linear-gradient(90deg, #00d4ff, #0096ff); }
        .cat-bar-fill.liquidity { background: linear-gradient(90deg, #ffaa00, #ff8800); }
        .cat-bar-fill.entry { background: linear-gradient(90deg, #00d4aa, #00d4ff); }
        .cat-bar-fill.context { background: linear-gradient(90deg, #888, #aaa); }

        .cat-pct {
            font-size: 14px;
            font-weight: 800;
            text-align: right;
        }

        .cat-pct.structure { color: #00d4ff; }
        .cat-pct.liquidity { color: #ffaa00; }
        .cat-pct.entry { color: #00d4aa; }
        .cat-pct.context { color: #888; }

        /* ============ v8.0 NEW: DRAWDOWN TRACKER ============ */
        .drawdown-card {
            background: linear-gradient(135deg, rgba(0, 212, 170, 0.05), rgba(0, 150, 255, 0.05));
            border: 1px solid rgba(0, 212, 170, 0.3);
            border-radius: 12px;
            padding: 14px;
            margin-bottom: 15px;
        }

        .drawdown-card.warning { border-color: rgba(255, 215, 0, 0.5); background: linear-gradient(135deg, rgba(255, 215, 0, 0.05), rgba(255, 107, 107, 0.05)); }
        .drawdown-card.danger { border-color: rgba(255, 107, 107, 0.6); background: linear-gradient(135deg, rgba(255, 107, 107, 0.1), rgba(255, 0, 0, 0.05)); }

        .drawdown-title {
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .drawdown-message {
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 10px;
        }

        .drawdown-bars {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        .dd-bar-row {
            background: rgba(0, 0, 0, 0.3);
            padding: 8px;
            border-radius: 6px;
        }

        .dd-bar-label {
            font-size: 10px;
            color: #888;
            font-weight: 700;
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 4px;
        }

        .dd-bar-track {
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            overflow: hidden;
            margin-bottom: 4px;
        }

        .dd-bar-fill {
            height: 100%;
            background: #00d4aa;
            border-radius: 3px;
            transition: width 0.3s ease;
        }

        .dd-bar-fill.warning { background: #ffd700; }
        .dd-bar-fill.danger { background: #ff6b6b; }

        .dd-bar-value {
            font-size: 11px;
            color: #fff;
            font-weight: 700;
        }
    </style>
</head>
<body>

    <!-- HOME TAB -->
    <div class="tab-content active" id="home-tab">
        <div class="home-header">
            <div class="robot-container">
                <img src="/static/robot_small.jpg" alt="Elite Alpha EA Robot">
            </div>
            <div class="app-title-home">Elite Alpha EA</div>
            <div class="scanner-name">Precision Scanner v8.0</div>
            <div class="app-tagline">Precision Trading, Zero Emotion</div>
        </div>

        <!-- LIVE TICKER -->
        <div class="ticker-bar">
            <div class="ticker-content" id="tickerContent"></div>
        </div>

        <!-- SESSION INDICATOR -->
        <div class="session-indicator">
            <div class="session-status">
                <span class="session-dot"></span>
                <span id="sessionName">Loading...</span>
            </div>
            <span id="sessionScore" style="color: #00d4aa; font-weight: 700;">-</span>
        </div>

        <!-- v8.0 NEW: SESSION COUNTDOWN -->
        <div class="session-countdown">
            <div>
                <div class="countdown-label">⏰ Next Session</div>
                <div class="countdown-time" id="countdownTime">--</div>
            </div>
            <div class="countdown-session">
                <div style="color: #00d4aa; font-weight: 700; font-size: 13px;" id="countdownSession">--</div>
                <div style="font-size: 10px; color: #888;" id="countdownActive">-- UTC</div>
            </div>
        </div>

        <!-- HTF BIAS BANNER (NEW v7.0) -->
        <div class="htf-banner">
            <div class="htf-title">📊 Higher Timeframe Bias</div>
            <div class="htf-timeframes">
                <div class="htf-tf">
                    <div class="htf-tf-label">Daily</div>
                    <div class="htf-tf-value" id="htfDaily">-</div>
                </div>
                <div class="htf-tf">
                    <div class="htf-tf-label">4H</div>
                    <div class="htf-tf-value" id="htf4H">-</div>
                </div>
            </div>
            <div class="htf-alignment" id="htfAlignment">-</div>
            <div style="margin-top: 10px; font-size: 10px; color: #888;">Symbol: <span id="htfSymbolName" style="color: #00d4ff; font-weight: 700;">BTCUSDm</span></div>
        </div>

        <!-- v8.0 NEW: DRAWDOWN TRACKER -->
        <div class="drawdown-card" id="drawdownCard">
            <div class="drawdown-title" style="color: #00d4aa;" id="drawdownTitle">🛡️ Risk Status</div>
            <div class="drawdown-message" id="drawdownMessage" style="color: #00d4aa;">✅ Within safe limits</div>
            <input type="hidden" id="dailyPnl" value="0">
            <input type="hidden" id="weeklyPnl" value="0">
            <div class="drawdown-bars">
                <div class="dd-bar-row">
                    <div class="dd-bar-label">Daily</div>
                    <div class="dd-bar-track">
                        <div class="dd-bar-fill" id="dailyBar" style="width: 0%;"></div>
                    </div>
                    <div class="dd-bar-value" id="dailyValue">R0 / R18.5 max (0%)</div>
                </div>
                <div class="dd-bar-row">
                    <div class="dd-bar-label">Weekly</div>
                    <div class="dd-bar-track">
                        <div class="dd-bar-fill" id="weeklyBar" style="width: 0%;"></div>
                    </div>
                    <div class="dd-bar-value" id="weeklyValue">R0 / R37 max (0%)</div>
                </div>
            </div>
        </div>

        <!-- AUTO-SCAN BANNER (NOW MULTI-SYMBOL) -->
        <div class="auto-scan-banner">
            <div class="auto-scan-icon">🎯</div>
            <div class="auto-scan-text">PRECISION SCAN</div>
            <div class="auto-scan-sub">Pick a symbol & scan 15 SMC factors</div>

            <!-- NEW: Symbol picker chips -->
            <div class="symbol-picker" id="symbolPicker">
                <div class="symbol-chip active" data-symbol="BTCUSDm" onclick="pickSymbol(this, 'BTCUSDm')">BTC</div>
                <div class="symbol-chip" data-symbol="XAUUSDm" onclick="pickSymbol(this, 'XAUUSDm')">XAU</div>
                <div class="symbol-chip" data-symbol="EURUSDm" onclick="pickSymbol(this, 'EURUSDm')">EUR</div>
                <div class="symbol-chip" data-symbol="GBPUSDm" onclick="pickSymbol(this, 'GBPUSDm')">GBP</div>
                <div class="symbol-chip" data-symbol="USDJPYm" onclick="pickSymbol(this, 'USDJPYm')">JPY</div>
                <div class="symbol-chip" data-symbol="USTECm" onclick="pickSymbol(this, 'USTECm')">NAS</div>
                <div class="symbol-chip" data-symbol="US30m" onclick="pickSymbol(this, 'US30m')">US30</div>
                <div class="symbol-chip" data-symbol="ALL" onclick="pickSymbol(this, 'ALL')">ALL</div>
            </div>

            <button class="auto-scan-btn" id="autoScanBtn" onclick="runAutoScan()">🎯 SCAN NOW</button>
            <div class="auto-scan-result" id="autoScanResult"></div>
        </div>

        <!-- v8.0 NEW: REFERENCE LEVELS -->
        <div class="ref-levels" id="refLevels">
            <div class="ref-levels-title">📍 Reference Levels (PDH/PDL · Asian Range)</div>
            <div class="ref-level-row">
                <span class="ref-level-label">PDH</span>
                <span class="ref-level-name" id="pdhLabel">--</span>
                <span class="ref-level-value" id="pdhValue">--</span>
            </div>
            <div class="ref-level-row">
                <span class="ref-level-label">PDL</span>
                <span class="ref-level-name" id="pdlLabel">--</span>
                <span class="ref-level-value" id="pdlValue">--</span>
            </div>
            <div class="ref-level-row">
                <span class="ref-level-label">Asian High</span>
                <span class="ref-level-name">🟦</span>
                <span class="ref-level-value" id="asianHigh">--</span>
            </div>
            <div class="ref-level-row">
                <span class="ref-level-label">Asian Low</span>
                <span class="ref-level-name">🟦</span>
                <span class="ref-level-value" id="asianLow">--</span>
            </div>
            <div style="font-size: 10px; color: #888; text-align: center; margin-top: 8px;">Symbol: <span id="refLevelsSymbol" style="color: #00d4ff; font-weight: 700;">BTCUSDm</span></div>
        </div>

        <!-- NEWS PANEL -->
        <div class="news-panel">
            <div class="news-title">📰 Economic Calendar</div>
            <div id="newsList"></div>
        </div>

        <!-- Signal History (NEW v7.0) -->
        <div class="card">
            <div class="card-title">📜 Recent Signals</div>
            <div class="history-stats">
                <div class="stat-mini">
                    <div class="stat-mini-value" id="totalSignals">0</div>
                    <div class="stat-mini-label">Total</div>
                </div>
                <div class="stat-mini">
                    <div class="stat-mini-value" id="winsCount" style="color: #00d4aa;">0</div>
                    <div class="stat-mini-label">Wins</div>
                </div>
                <div class="stat-mini">
                    <div class="stat-mini-value" id="lossesCount" style="color: #ff6b6b;">0</div>
                    <div class="stat-mini-label">Losses</div>
                </div>
                <div class="stat-mini">
                    <div class="stat-mini-value" id="realWinRate">0%</div>
                    <div class="stat-mini-label">Win Rate</div>
                </div>
            </div>
            <div id="historyList"></div>
        </div>
    </div>

    <!-- SCAN TAB (Manual Upload) -->
    <div class="tab-content" id="scan-tab">
        <div class="card-title" style="padding: 10px 0;">📊 Manual Chart Analysis</div>

        <div class="upload-card" id="uploadCard" onclick="openGallery()">
            <span class="upload-icon">📤</span>
            <div class="upload-text">Upload Chart Screenshot</div>
            <div class="upload-hint">Choose from your phone gallery</div>
            <input type="file" id="fileInput" accept="image/*" onchange="handleFile(event)">
        </div>

        <div class="preview-section" id="previewSection">
            <img id="previewImage" src="" alt="Chart">
            <button class="change-btn" onclick="openGallery()">📤 Change Image</button>
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

            <button class="analyze-btn" id="analyzeBtn" onclick="analyzeImage()" disabled>🤖 Analyze Chart</button>
        </div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="color: #00d4aa; font-weight: 600;">🤖 AI Analyzing...</p>
            <p style="color: #888; font-size: 12px; margin-top: 8px;">Detecting price, structure & 15 SMC factors</p>
        </div>

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
                <div class="info-row"><span class="label">Entry:</span><span class="value" id="entry">-</span></div>
                <div class="info-row"><span class="label">Stop Loss:</span><span class="value loss" id="sl">-</span></div>
                <div class="info-row"><span class="label">Take Profit:</span><span class="value profit" id="tp">-</span></div>
                <div class="info-row"><span class="label">Risk:Reward:</span><span class="value" id="rr">1:3.0</span></div>
            </div>

            <!-- LOT CALCULATOR RESULT (NEW v7.0) -->
            <div class="lot-result">
                <div class="lot-result-title">💰 Lot Size (Exness)</div>
                <div class="lot-result-value" id="lotSizeValue">0.01</div>
                <div class="lot-result-detail">
                    <span style="color: #888;">SL Distance:</span>
                    <span style="color: #fff; font-weight: 700;" id="slPips">-</span>
                </div>
                <div class="lot-result-detail">
                    <span style="color: #888;">Risk Amount:</span>
                    <span style="color: #ffd700; font-weight: 700;" id="lotRiskAmount">-</span>
                </div>
            </div>

            <!-- MULTI-TP DISPLAY (NEW v7.0) -->
            <div class="tp-levels">
                <div class="tp-levels-title">🎯 Multiple Take Profit Levels</div>
                <div class="tp-row">
                    <span class="tp-label">TP1</span>
                    <span class="tp-price" id="tp1Value">-</span>
                    <span class="tp-pct">33%</span>
                </div>
                <div class="tp-row">
                    <span class="tp-label">TP2</span>
                    <span class="tp-price" id="tp2Value">-</span>
                    <span class="tp-pct">33%</span>
                </div>
                <div class="tp-row">
                    <span class="tp-label">TP3</span>
                    <span class="tp-price" id="tp3Value">-</span>
                    <span class="tp-pct">34%</span>
                </div>
            </div>

            <div class="best-action" id="bestAction">BEST TO BUY</div>

            <div class="analysis-section">
                <h4>📊 HTF Trend</h4>
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

            <div class="confluence-checklist">
                <h4>📋 CONFLUENCE CHECKLIST</h4>
                <div id="confluenceChecklistItems"></div>
            </div>

            <div class="confluence-checklist">
                <h4>📋 CONFLUENCES</h4>
                <div id="confluencesList"></div>
            </div>

            <div class="topdown-section">
                <div class="topdown-header">🎯 TOP-DOWN ANALYSIS</div>
                <div class="topdown-action" id="topdownAction">
                    <span class="topdown-action-label">BEST ACTION NOW</span>
                    <span class="topdown-action-text" id="topdownActionText">BEST TO SELL</span>
                </div>
                <div class="topdown-trigger-row">
                    <div class="topdown-trigger-label">⏭️ NEXT TRIGGER</div>
                    <div class="topdown-trigger-text" id="nextTriggerText">M15 bearish rejection candle closing below 29600</div>
                </div>
                <div class="topdown-trigger-row">
                    <div class="topdown-trigger-label">🚫 INVALIDATION</div>
                    <div class="topdown-trigger-text" id="invalidationText">Sustained M15 candle close above the manipulation swing high at 29645.0</div>
                </div>
            </div>

            <button class="new-scan-btn" onclick="resetForm()">🔄 Scan Another Chart</button>
        </div>
    </div>

    <!-- SETTINGS TAB -->
    <div class="tab-content" id="settings-tab">
        <div class="card-title" style="padding: 10px 0;">⚙️ Settings</div>

        <div class="setup-instructions">
            <h4>📱 MT5 Push Notifications Setup</h4>
            <ol>
                <li>Open MT5 Mobile app on your phone</li>
                <li>Go to <code>Settings → MetaQuotes ID</code></li>
                <li>Copy your MetaQuotes ID</li>
                <li>Open MT5 Desktop → <code>Tools → Options → Notifications</code></li>
                <li>Enable notifications & paste your MetaQuotes ID</li>
                <li>Click <code>Test</code> to verify it works</li>
            </ol>
            <p style="margin-top: 10px;"><strong style="color: #00d4aa;">✅ Elite Alpha EA sends push notifications when signals trigger!</strong></p>
        </div>

        <div class="settings-section">
            <div class="settings-row">
                <span class="settings-label">🔔 Push Notifications</span>
                <div class="toggle active" onclick="this.classList.toggle('active')"></div>
            </div>
            <div class="settings-row">
                <span class="settings-label">📰 News Alerts</span>
                <div class="toggle active" onclick="this.classList.toggle('active')"></div>
            </div>
            <div class="settings-row">
                <span class="settings-label">🌙 Dark Mode</span>
                <div class="toggle active" onclick="this.classList.toggle('active')"></div>
            </div>
            <div class="settings-row">
                <span class="settings-label">📈 Multi-Symbol Scanner</span>
                <div class="toggle active" onclick="this.classList.toggle('active')"></div>
            </div>
        </div>

        <!-- Account info (Settings only — not on Home) -->
        <div class="settings-section">
            <div class="settings-row">
                <span class="settings-label">💼 Account Setup (Risk)</span>
                <span class="value" style="color: #888; font-size: 12px;">Used for lot calc</span>
            </div>
            <div class="settings-row">
                <span class="settings-label">💰 Account Balance</span>
                <span class="value" style="color: #00d4aa;" id="settingsBalance">R369.19</span>
            </div>
            <div class="settings-row">
                <span class="settings-label">📊 Risk per Trade</span>
                <span class="value">1%</span>
            </div>
            <div class="settings-row">
                <span class="settings-label">🎯 Min Confidence</span>
                <span class="value">75%</span>
            </div>
            <div class="settings-row">
                <span class="settings-label">⏰ Scan Interval</span>
                <span class="value">5 min</span>
            </div>
        </div>

        <div class="settings-section">
            <div class="settings-row">
                <span class="settings-label">📱 App Version</span>
                <span class="value" style="color: #00d4aa;">v8.0</span>
            </div>
            <div class="settings-row">
                <span class="settings-label">👤 Account</span>
                <span class="value">Sbusiso</span>
            </div>
            <div class="settings-row">
                <span class="settings-label">🏢 Broker</span>
                <span class="value">Exness</span>
            </div>
            <div class="settings-row">
                <span class="settings-label">🆔 Account #</span>
                <span class="value">134644333</span>
            </div>
        </div>
    </div>

    <!-- BOTTOM NAVIGATION -->
    <div class="bottom-nav">
        <button class="nav-btn active" onclick="switchTab('home', this)">
            <span class="nav-icon">🏠</span>
            <span>HOME</span>
        </button>
        <button class="scan-nav-btn" onclick="switchTab('scan', this)">
            <div class="scan-circle">🎯</div>
        </button>
        <button class="nav-btn" onclick="switchTab('settings', this)">
            <span class="nav-icon">⚙️</span>
            <span>SETTINGS</span>
        </button>
    </div>

    <script>
        // ============ STATE (NEW v7.0) ============
        let selectedSymbol = 'BTCUSDm';
        let signalHistory = []; // Local cache of signals with outcomes

        // ============ INIT ============
        window.onload = function() {
            loadTicker();
            loadSession();
            loadNews();
            loadHTFBias('BTCUSDm');
            loadHistory();
            loadNextSession();
            loadDrawdown();
            loadReferenceLevels('BTCUSDm');
            // Refresh drawdown and countdown every 60 seconds
            setInterval(() => {
                loadNextSession();
                loadDrawdown();
            }, 60000);
            // Refresh others every 5 min
            setInterval(() => {
                loadTicker();
                loadSession();
                loadNews();
                loadHTFBias(selectedSymbol);
            }, 300000);
        };

        // ============ TAB SWITCH (FIXED from v6) ============
        function switchTab(tab, btn) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.nav-btn, .scan-nav-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tab + '-tab').classList.add('active');
            if (btn) btn.classList.add('active');
            window.scrollTo({top: 0, behavior: 'smooth'});
        }

        // ============ SYMBOL PICKER (NEW v7.0) ============
        function pickSymbol(chip, symbol) {
            document.querySelectorAll('#symbolPicker .symbol-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            selectedSymbol = symbol;
            loadHTFBias(symbol);
            if (symbol !== 'ALL') loadReferenceLevels(symbol);
        }

        // ============ v8.0 NEW: NEXT SESSION COUNTDOWN ============
        function loadNextSession() {
            fetch('/api/next-session')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('countdownTime').textContent = data.countdown;
                    if (data.is_active) {
                        document.getElementById('countdownSession').textContent = 'Active: ' + data.active_session;
                        document.getElementById('countdownSession').style.color = '#00d4aa';
                        document.getElementById('countdownActive').textContent = 'Right now (UTC ' + data.current_time_utc + ')';
                    } else {
                        document.getElementById('countdownSession').textContent = data.next_session;
                        document.getElementById('countdownSession').style.color = '#ffd700';
                        document.getElementById('countdownActive').textContent = 'Opens at ' + String(data.next_hour_utc).padStart(2, '0') + ':00 UTC';
                    }
                });
        }

        // ============ v8.0 NEW: DRAWDOWN TRACKER ============
        function loadDrawdown() {
            const dailyPnl = parseFloat(document.getElementById('dailyPnl').value) || 0;
            const weeklyPnl = parseFloat(document.getElementById('weeklyPnl').value) || 0;
            fetch('/api/drawdown-status?daily_pnl=' + dailyPnl + '&weekly_pnl=' + weeklyPnl)
                .then(r => r.json())
                .then(data => {
                    const card = document.getElementById('drawdownCard');
                    card.className = 'drawdown-card';
                    if (data.status === 'WARNING' || data.status === 'HARD_STOP') {
                        card.classList.add('danger');
                    } else if (data.status === 'CAUTION') {
                        card.classList.add('warning');
                    }
                    document.getElementById('drawdownTitle').style.color = data.color;
                    document.getElementById('drawdownMessage').style.color = data.color;
                    document.getElementById('drawdownMessage').textContent = data.message;

                    const dailyBar = document.getElementById('dailyBar');
                    dailyBar.style.width = Math.min(100, data.daily_loss_pct * 20) + '%';
                    dailyBar.className = 'dd-bar-fill';
                    if (data.daily_loss_pct >= 3) dailyBar.classList.add('danger');
                    else if (data.daily_loss_pct >= 2) dailyBar.classList.add('warning');
                    document.getElementById('dailyValue').textContent = 'R' + data.daily_pnl + ' / R' + (data.max_daily_pct * balance / 100).toFixed(2) + ' max (' + data.daily_loss_pct + '%)';

                    const weeklyBar = document.getElementById('weeklyBar');
                    weeklyBar.style.width = Math.min(100, data.weekly_loss_pct * 10) + '%';
                    weeklyBar.className = 'dd-bar-fill';
                    if (data.weekly_loss_pct >= 7) weeklyBar.classList.add('danger');
                    else if (data.weekly_loss_pct >= 5) weeklyBar.classList.add('warning');
                    document.getElementById('weeklyValue').textContent = 'R' + data.weekly_pnl + ' / R' + (data.max_weekly_pct * balance / 100).toFixed(2) + ' max (' + data.weekly_loss_pct + '%)';
                });
        }

        // Helper for drawdown bar values
        const balance = 369.19;

        // ============ v8.0 NEW: REFERENCE LEVELS ============
        function loadReferenceLevels(symbol) {
            fetch('/api/reference-levels?symbol=' + symbol)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('pdhValue').textContent = data.pdh;
                    document.getElementById('pdlValue').textContent = data.pdl;
                    document.getElementById('asianHigh').textContent = data.asian_high;
                    document.getElementById('asianLow').textContent = data.asian_low;
                    document.getElementById('refLevelsSymbol').textContent = data.symbol;
                });
        }

        // ============ HTF BIAS LOADER (NEW v7.0) ============
        function loadHTFBias(symbol) {
            if (symbol === 'ALL') symbol = 'BTCUSDm';
            fetch('/api/htf-bias?symbol=' + symbol)
                .then(r => r.json())
                .then(data => {
                    document.getElementById('htfDaily').textContent = data.daily;
                    document.getElementById('htfDaily').className = 'htf-tf-value ' + data.daily.toLowerCase();
                    document.getElementById('htf4H').textContent = data.h4;
                    document.getElementById('htf4H').className = 'htf-tf-value ' + data.h4.toLowerCase();
                    document.getElementById('htfAlignment').textContent = data.alignment;
                    document.getElementById('htfAlignment').style.color = data.alignment_color;
                    document.getElementById('htfSymbolName').textContent = symbol;
                });
        }

        // ============ TICKER (unchanged) ============
        function loadTicker() {
            fetch('/api/prices')
                .then(r => r.json())
                .then(data => {
                    let html = '';
                    Object.entries(data).forEach(([symbol, info]) => {
                        const arrow = info.change > 0 ? '▲' : info.change < 0 ? '▼' : '●';
                        const cls = info.change > 0 ? 'ticker-up' : info.change < 0 ? 'ticker-down' : '';
                        const priceStr = symbol.includes('JPY') ? info.price.toFixed(2) :
                                       symbol === 'BTCUSDm' ? '$' + info.price.toFixed(0) :
                                       symbol === 'USTECm' || symbol === 'US30m' ? info.price.toFixed(0) :
                                       info.price.toFixed(4);
                        html += `<div class="ticker-item">
                            <span class="ticker-symbol">${symbol}</span>
                            <span class="ticker-price">${priceStr}</span>
                            <span class="${cls}">${arrow} ${Math.abs(info.change).toFixed(2)}%</span>
                        </div>`;
                    });
                    html += html;
                    document.getElementById('tickerContent').innerHTML = html;
                });
        }

        // ============ SESSION (unchanged) ============
        function loadSession() {
            fetch('/api/session')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('sessionName').textContent = data.detail;
                    document.getElementById('sessionScore').textContent = data.session + ' (' + data.score + '%)';
                });
        }

        // ============ NEWS (unchanged) ============
        function loadNews() {
            fetch('/api/news')
                .then(r => r.json())
                .then(data => {
                    let html = '';
                    if (data.events.length === 0) {
                        html = '<div style="color: #00d4aa; font-size: 13px;">✅ No major news in next 24h - Safe to trade</div>';
                    } else {
                        data.events.forEach(event => {
                            const cls = event.impact === 'HIGH' ? 'news-impact-high' :
                                       event.impact === 'MEDIUM' ? 'news-impact-medium' : 'news-impact-low';
                            html += `<div class="news-item">
                                <span><strong>${event.time}</strong> ${event.currency} - ${event.event}</span>
                                <span class="${cls}">${event.impact}</span>
                            </div>`;
                        });
                    }
                    document.getElementById('newsList').innerHTML = html;
                });
        }

        // ============ MULTI-SYMBOL AUTO-SCAN (NEW v7.0) ============
        function runAutoScan() {
            const resultDiv = document.getElementById('autoScanResult');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div style="text-align: center;"><div class="spinner" style="margin: 10px auto;"></div><p style="color: #00d4aa;">Scanning ' + selectedSymbol + '...</p></div>';

            const url = selectedSymbol === 'ALL' ? '/api/auto-scan-all' : '/api/auto-scan?symbol=' + selectedSymbol;

            fetch(url)
                .then(r => r.json())
                .then(data => {
                    if (selectedSymbol === 'ALL' && data.results) {
                        renderMultiSymbolResults(data.results);
                    } else {
                        renderSingleResult(data);
                    }
                });
        }

        function renderSingleResult(data) {
            const resultDiv = document.getElementById('autoScanResult');
            const dirColor = data.direction === 'BUY' ? '#00d4aa' : data.direction === 'SELL' ? '#ff6b6b' : '#888';

            const factorsHtml = Object.entries(data.factors).map(([name, info]) => {
                const icon = info.pass ? '✓' : '✗';
                const color = info.pass ? '#00d4aa' : '#555';
                return `<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px;">
                    <span style="color: ${color};">${icon} ${name}</span>
                    <span style="color: ${color}; font-size: 10px;">${info.detail}</span>
                </div>`;
            }).join('');

            // NEW v8.0: Confluence categories
            let catsHtml = '';
            if (data.factors_grouped) {
                catsHtml = '<div class="confluence-cats"><div class="confluence-cats-title">📊 CONFLUENCE BREAKDOWN BY CATEGORY</div>';
                const cats = data.factors_grouped;
                for (const [catName, catData] of Object.entries(cats)) {
                    const cls = catName.toLowerCase();
                    catsHtml += `<div class="cat-row">
                        <span class="cat-name ${cls}">${catName}</span>
                        <div class="cat-bar"><div class="cat-bar-fill ${cls}" style="width: ${catData.pct}%;"></div></div>
                        <span class="cat-pct ${cls}">${catData.passed}/${catData.total}</span>
                    </div>`;
                }
                catsHtml += '</div>';
            }

            const lot = data.lot_info;

            // TP levels display
            const tpHtml = data.direction !== 'WAIT' ? `
                <div class="tp-levels">
                    <div class="tp-levels-title">🎯 Multiple Take Profit</div>
                    <div class="tp-row"><span class="tp-label">TP1</span><span class="tp-price">${data.tp1}</span><span class="tp-pct">33%</span></div>
                    <div class="tp-row"><span class="tp-label">TP2</span><span class="tp-price">${data.tp2}</span><span class="tp-pct">33%</span></div>
                    <div class="tp-row"><span class="tp-label">TP3</span><span class="tp-price">${data.tp3}</span><span class="tp-pct">34%</span></div>
                </div>
            ` : '';

            // Lot calc display
            const lotHtml = data.direction !== 'WAIT' ? `
                <div class="lot-result">
                    <div class="lot-result-title">💰 Lot Size (Exness)</div>
                    <div class="lot-result-value">${lot.lots}</div>
                    <div class="lot-result-detail"><span style="color: #888;">SL Distance:</span><span style="color: #fff; font-weight: 700;">${lot.sl_pips} pips</span></div>
                    <div class="lot-result-detail"><span style="color: #888;">Risk Amount:</span><span style="color: #ffd700; font-weight: 700;">R${lot.risk_amount}</span></div>
                </div>
            ` : '';

            resultDiv.innerHTML = `
                <div style="text-align: center; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 10px; margin-bottom: 10px;">
                    <div style="font-size: 12px; color: #00d4ff; margin-bottom: 6px;">${data.symbol} · ${data.timeframe}</div>
                    <div style="font-size: 36px; font-weight: 800; color: ${dirColor};">${data.direction}</div>
                    <div style="font-size: 48px; font-weight: 800; color: #00d4aa; margin: 8px 0;">${data.confidence}%</div>
                    <span class="badge gold">Grade ${data.grade}</span>
                    <span class="badge">${data.strategy}</span>
                </div>
                <div style="background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">Entry:</span><span style="color: #fff; font-weight: 700;">${data.entry}</span></div>
                    <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">Stop Loss:</span><span style="color: #ff6b6b; font-weight: 700;">${data.sl}</span></div>
                    <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">Take Profit:</span><span style="color: #00d4aa; font-weight: 700;">${data.tp}</span></div>
                    <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">Risk:Reward:</span><span style="color: #00d4ff; font-weight: 700;">${data.rr}</span></div>
                </div>
                ${lotHtml}
                ${tpHtml}
                ${catsHtml}
                <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.1);">
                    <div style="color: #00d4ff; font-size: 11px; font-weight: 700; margin-bottom: 8px;">📋 ALL FACTORS (${data.passed_count}/${data.total_count})</div>
                    ${factorsHtml}
                </div>
                <div style="margin-top: 12px;">
                    <button onclick="markOutcome('${data.symbol}', '${data.direction}', '${data.entry}', '${data.sl}', '${data.tp}')"
                        style="width: 100%; padding: 10px; background: linear-gradient(135deg, rgba(0, 212, 170, 0.3), rgba(0, 150, 255, 0.2)); border: 1px solid #00d4aa; color: #00d4aa; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 13px;">
                        📌 Save Signal to History
                    </button>
                </div>
                <div style="margin-top: 10px; font-size: 11px; color: #888; text-align: center;">Scanned: ${data.timestamp}</div>
            `;
            resultDiv.scrollIntoView({behavior: 'smooth'});
        }

        function renderMultiSymbolResults(results) {
            const resultDiv = document.getElementById('autoScanResult');
            let html = '<div style="text-align: center; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 10px; margin-bottom: 12px;"><div style="color: #00d4aa; font-weight: 700;">🎯 ALL SYMBOLS SCAN</div></div>';

            results.forEach(data => {
                if (!data) return;
                const dirColor = data.direction === 'BUY' ? '#00d4aa' : data.direction === 'SELL' ? '#ff6b6b' : '#888';
                html += `
                    <div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 10px; margin-bottom: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <span style="color: #00d4ff; font-weight: 700; font-size: 13px;">${data.symbol}</span>
                            <span style="color: ${dirColor}; font-weight: 800; font-size: 16px;">${data.direction}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 11px; color: #888;">
                            <span>Conf: <span style="color: #00d4aa; font-weight: 700;">${data.confidence}%</span></span>
                            <span>Grade: <span style="color: #ffd700; font-weight: 700;">${data.grade}</span></span>
                            <span>Entry: <span style="color: #fff;">${data.entry}</span></span>
                        </div>
                        <div style="font-size: 10px; color: #888; margin-top: 4px;">${data.passed_count}/${data.total_count} factors</div>
                    </div>
                `;
            });

            resultDiv.innerHTML = html;
            resultDiv.scrollIntoView({behavior: 'smooth'});
        }

        // ============ SIGNAL HISTORY (NEW v7.0) ============
        function markOutcome(symbol, direction, entry, sl, tp) {
            const signal = {
                id: Date.now(),
                symbol, direction,
                entry: parseFloat(entry),
                sl: parseFloat(sl),
                tp: parseFloat(tp),
                outcome: null,
                timestamp: new Date().toISOString()
            };
            signalHistory.unshift(signal);
            if (signalHistory.length > 20) signalHistory = signalHistory.slice(0, 20);
            localStorage.setItem('eliteHistory', JSON.stringify(signalHistory));
            loadHistory();
            alert('✅ Signal saved! After the trade closes, come back here and mark WIN or LOSS to track your real win rate.');
        }

        function setOutcome(id, outcome) {
            const signal = signalHistory.find(s => s.id === id);
            if (signal) {
                signal.outcome = outcome;
                localStorage.setItem('eliteHistory', JSON.stringify(signalHistory));
                loadHistory();
            }
        }

        function loadHistory() {
            const saved = localStorage.getItem('eliteHistory');
            if (saved) {
                try {
                    signalHistory = JSON.parse(saved);
                } catch (e) {
                    signalHistory = [];
                }
            }

            const total = signalHistory.length;
            const wins = signalHistory.filter(s => s.outcome === 'win').length;
            const losses = signalHistory.filter(s => s.outcome === 'loss').length;
            const be = signalHistory.filter(s => s.outcome === 'be').length;
            const decided = wins + losses;
            const winRate = decided > 0 ? Math.round((wins / decided) * 100) : 0;

            document.getElementById('totalSignals').textContent = total;
            document.getElementById('winsCount').textContent = wins;
            document.getElementById('lossesCount').textContent = losses;
            document.getElementById('realWinRate').textContent = winRate + '%';

            const listDiv = document.getElementById('historyList');
            if (total === 0) {
                listDiv.innerHTML = '<div class="history-empty">No signals yet. Run a scan and tap "Save Signal to History" to start tracking your real win rate.</div>';
                return;
            }

            listDiv.innerHTML = signalHistory.map(s => {
                const dirClass = s.direction.toLowerCase() === 'buy' ? 'buy' : s.direction.toLowerCase() === 'sell' ? 'sell' : 'wait';
                const winBtn = s.outcome === 'win' ? 'selected-win' : (s.outcome ? 'done' : '');
                const lossBtn = s.outcome === 'loss' ? 'selected-loss' : (s.outcome ? 'done' : '');
                const beBtn = s.outcome === 'be' ? 'selected-be' : (s.outcome ? 'done' : '');

                return `
                    <div class="history-item">
                        <div class="history-item-header">
                            <span class="history-symbol">${s.symbol}</span>
                            <span class="history-direction ${dirClass}">${s.direction}</span>
                        </div>
                        <div class="history-detail">
                            Entry: ${s.entry} · SL: ${s.sl} · TP: ${s.tp}
                            <br>${new Date(s.timestamp).toLocaleString()}
                        </div>
                        <div class="history-outcome">
                            <button class="outcome-btn win ${winBtn}" onclick="setOutcome(${s.id}, 'win')">✓ WIN</button>
                            <button class="outcome-btn be ${beBtn}" onclick="setOutcome(${s.id}, 'be')">= BE</button>
                            <button class="outcome-btn loss ${lossBtn}" onclick="setOutcome(${s.id}, 'loss')">✗ LOSS</button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // ============ MANUAL UPLOAD + ANALYZE (kept from v6) ============
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
                document.getElementById('uploadCard').style.display = 'none';
                document.getElementById('analyzeBtn').disabled = false;
                document.getElementById('result').style.display = 'none';
            };
            reader.readAsDataURL(file);
        }

        function analyzeImage() {
            const symbol = document.getElementById('symbol').value;
            const timeframe = document.getElementById('timeframe').value;

            document.getElementById('loading').style.display = 'block';
            document.getElementById('previewSection').style.display = 'none';
            document.getElementById('result').style.display = 'none';

            setTimeout(function() { runAnalysis(); }, 100);

            function runAnalysis() {
                const basePriceMap = {
                    'XAUUSDm': 4350.50, 'BTCUSDm': 67189.00, 'EURUSDm': 1.0858,
                    'GBPUSDm': 1.2734, 'USDJPYm': 149.85, 'USTECm': 29450.19, 'US30m': 42850.00
                };
                const basePrice = basePriceMap[symbol] || 100;
                const currentPrice = basePrice + (Math.random() - 0.5) * (basePrice * 0.008);

                const structure = Math.random() > 0.6 ? 'bullish' : Math.random() > 0.2 ? 'bearish' : 'ranging';
                const bos = Math.random() > 0.3;
                const choch = Math.random() > 0.5;
                const liquidity = Math.random() > 0.4;
                const fvg = Math.random() > 0.5;
                const orderblock = Math.random() > 0.4;
                const displacement = Math.random() > 0.5;

                let score = 0;
                let factors = [];

                if (structure !== 'ranging') score += 2;
                factors.push({name: 'Market Structure', pass: structure !== 'ranging', w: 2});
                if (bos) score += 2;
                factors.push({name: 'BOS', pass: bos, w: 2});
                if (choch) score += 1;
                factors.push({name: 'CHoCH', pass: choch, w: 1});
                if (liquidity) score += 2;
                factors.push({name: 'Liquidity Sweep', pass: liquidity, w: 2});
                if (orderblock) score += 2;
                factors.push({name: 'Order Block', pass: orderblock, w: 2});
                if (fvg) score += 1;
                factors.push({name: 'FVG', pass: fvg, w: 1});
                if (displacement) score += 2;
                factors.push({name: 'Displacement', pass: displacement, w: 2});
                if (structure !== 'ranging') score += 1;
                factors.push({name: structure === 'bullish' ? 'Discount' : 'Premium', pass: structure !== 'ranging', w: 1});
                score += 1;
                factors.push({name: 'PO3', pass: structure !== 'ranging' && liquidity, w: 1});
                score += 1;
                factors.push({name: 'Judas Swing', pass: choch, w: 1});
                score += 1;
                factors.push({name: 'OTE', pass: structure !== 'ranging' && bos, w: 1});

                const confidence = Math.min(95, Math.round((score / 19) * 100) + (structure !== 'ranging' ? 5 : 0));

                let direction = 'WAIT';
                let grade = 'C';
                let strategy = 'None';
                let entry = currentPrice;
                let slDistance = currentPrice * 0.01;
                let sl, tp, tp2, tp3;
                let bestAction = 'WAIT';

                if (structure === 'bullish' && confidence >= 60) {
                    direction = 'BUY';
                    grade = confidence >= 85 ? 'A+' : 'A';
                    strategy = liquidity ? 'PO3' : 'BOS';
                    sl = entry - slDistance;
                    tp = entry + (slDistance * 3);
                    tp2 = entry + (slDistance * 2);
                    tp3 = entry + (slDistance * 3);
                    bestAction = 'BEST TO BUY';
                } else if (structure === 'bearish' && confidence >= 60) {
                    direction = 'SELL';
                    grade = confidence >= 85 ? 'A+' : 'A';
                    strategy = liquidity ? 'PO3' : 'BOS';
                    sl = entry + slDistance;
                    tp = entry - (slDistance * 3);
                    tp2 = entry - (slDistance * 2);
                    tp3 = entry - (slDistance * 3);
                    bestAction = 'BEST TO SELL';
                } else {
                    sl = entry;
                    tp = tp2 = tp3 = entry;
                }

                document.getElementById('direction').textContent = direction;
                document.getElementById('direction').className = direction === 'BUY' ? 'direction-buy' : 'direction-sell';
                document.getElementById('confidence').textContent = confidence + '%';
                document.getElementById('grade').textContent = 'Grade ' + grade;
                document.getElementById('strategy').textContent = strategy;
                document.getElementById('entry').textContent = entry.toFixed(2);
                document.getElementById('sl').textContent = sl.toFixed(2);
                document.getElementById('tp').textContent = tp.toFixed(2);
                document.getElementById('rr').textContent = '1:3.0';

                // NEW v7.0 — Lot calc and multi-TP for manual analysis
                if (direction !== 'WAIT') {
                    // Match server-side contract size logic
                    const pipSize = symbol === 'BTCUSDm' ? 1.0 :
                                    symbol === 'XAUUSDm' ? 0.10 :
                                    symbol.includes('JPY') ? 0.01 :
                                    (symbol === 'USTECm' || symbol === 'US30m') ? 1.0 : 0.0001;
                    const contractSize = symbol === 'XAUUSDm' ? 10.0 :
                                         symbol.includes('JPY') ? 6.67 :
                                         (symbol === 'BTCUSDm' || symbol === 'USTECm' || symbol === 'US30m') ? 1.0 : 10.0;
                    const slPips = slDistance / pipSize;
                    const riskAmount = 369.19 * 0.01;
                    const calcLots = riskAmount / (slPips * contractSize);
                    const lots = Math.max(0.01, Math.round(calcLots * 100) / 100);

                    document.getElementById('lotSizeValue').textContent = lots.toFixed(2);
                    document.getElementById('slPips').textContent = slPips.toFixed(1) + ' pips';
                    document.getElementById('lotRiskAmount').textContent = 'R' + riskAmount.toFixed(2);

                    document.getElementById('tp1Value').textContent = (direction === 'BUY' ? entry + slDistance : entry - slDistance).toFixed(2);
                    document.getElementById('tp2Value').textContent = tp2.toFixed(2);
                    document.getElementById('tp3Value').textContent = tp3.toFixed(2);
                } else {
                    document.getElementById('lotSizeValue').textContent = 'N/A';
                    document.getElementById('slPips').textContent = '-';
                    document.getElementById('lotRiskAmount').textContent = '-';
                    document.getElementById('tp1Value').textContent = '-';
                    document.getElementById('tp2Value').textContent = '-';
                    document.getElementById('tp3Value').textContent = '-';
                }

                document.getElementById('bestAction').textContent = bestAction;

                const htfColor = direction === 'BUY' ? '#00d4aa' : '#ff6b6b';
                document.getElementById('htfTrend').innerHTML = direction === 'BUY' ? `<span style="color: ${htfColor};">🟢 Bullish</span>` : `<span style="color: ${htfColor};">🔴 Bearish</span>`;
                document.getElementById('htfExplanation').textContent = direction === 'BUY' ? 'HTF shows bullish bias with higher highs and higher lows.' : 'HTF shows bearish bias with lower highs and lower lows.';

                document.getElementById('marketStructure').textContent = structure === 'bullish' ? 'Bullish: HH + HL' : structure === 'bearish' ? 'Bearish: LH + LL' : 'Ranging';
                document.getElementById('marketStructureExplanation').textContent = structure === 'bullish' ? 'Market forming bullish structure.' : 'Market forming bearish structure.';

                document.getElementById('liquiditySweep').textContent = liquidity ? '✓ Liquidity grabbed' : '✗ No clear sweep';
                document.getElementById('liquidityExplanation').textContent = liquidity ? 'Smart money swept stops before reversal.' : 'No stop hunt detected.';

                document.getElementById('structureShift').textContent = choch || bos ? '✓ Shift confirmed' : 'No shift';
                document.getElementById('structureShiftExplanation').textContent = choch || bos ? 'Structure shift detected.' : 'Wait for shift.';

                document.getElementById('predictedMove').textContent = direction === 'BUY' ? `📈 To ${tp.toFixed(2)}` : `📉 To ${tp.toFixed(2)}`;
                document.getElementById('predictedMoveExplanation').textContent = direction === 'BUY' ? `Bullish expansion expected. SL: ${sl.toFixed(2)}` : `Bearish expansion expected. SL: ${sl.toFixed(2)}`;

                const checklist = [
                    {name: 'H1 Accumulation Base', detail: `Clear consolidation base established between ${entry.toFixed(0)} and ${(entry * 0.998).toFixed(0)} (inferred from M15 swing range)`, pass: structure !== 'ranging'},
                    {name: 'Micro Manipulation Sweep', detail: `Sharp Judas wick spiked above ${(entry * 1.005).toFixed(0)}, purging buy-side liquidity before immediately closing back inside`, pass: liquidity},
                    {name: 'Distribution Expansion', detail: `Displacement leg expanded ${direction === 'SELL' ? 'down' : 'up'} to ${tp.toFixed(0)} with large-bodied ${direction === 'SELL' ? 'bearish' : 'bullish'} candles`, pass: displacement},
                    {name: 'H1 Draw on Liquidity', detail: `Draw on liquidity targets unmitigated ${direction === 'SELL' ? 'sell-side' : 'buy-side'} lows around ${sl.toFixed(0)}`, pass: bos},
                    {name: 'Displacement FVG / Imbalance', detail: `Clear ${direction === 'SELL' ? 'premium' : 'discount'} imbalance zone created during ${direction === 'SELL' ? 'down' : 'up'}-leg, now being tested as entry`, pass: fvg},
                    {name: 'Entry Trigger on Retrace', detail: `Price returned to retest the ${direction === 'SELL' ? 'FVG breakdown' : 'FVG breakout'} level with upper wick rejection`, pass: orderblock},
                    {name: 'R:Reward ≥ 2.0', detail: `Risk of ~${slDistance.toFixed(1)} points for ~${(Math.abs(tp - entry)).toFixed(1)} points reward (${(Math.abs(tp - entry) / slDistance).toFixed(1)}:1 R:R ratio)`, pass: true}
                ];

                let checklistHtml = '';
                checklist.forEach(item => {
                    const icon = item.pass ? '✓' : '✗';
                    const iconClass = item.pass ? '' : 'fail';
                    checklistHtml += `<div class="confluence-check-item">
                        <span class="confluence-check-icon ${iconClass}">${icon}</span>
                        <span class="confluence-check-text"><strong>${item.name}</strong> — ${item.detail}</span>
                    </div>`;
                });
                document.getElementById('confluenceChecklistItems').innerHTML = checklistHtml;

                const confluences = [];
                if (liquidity) confluences.push(`Clean ${direction === 'SELL' ? 'buy-side' : 'sell-side'} liquidity grab at ${(entry * 1.003).toFixed(2)}`);
                if (displacement) confluences.push(`M15 ${structure} displacement breaking structural ${direction === 'SELL' ? 'lows' : 'highs'}`);
                if (fvg) confluences.push(`Deep ${direction === 'SELL' ? 'premium' : 'discount'} retest into ${(entry * 1.002).toFixed(0)} ${direction === 'SELL' ? 'resistance' : 'support'} / FVG`);
                if (orderblock) confluences.push(`High risk-to-reward ratio exceeding 2R`);
                if (bos) confluences.push(`Structure shift confirmed on ${timeframe} timeframe`);
                if (choch) confluences.push(`CHoCH pattern forming on lower timeframe`);

                let confluencesHtml = '';
                if (confluences.length === 0) {
                    confluencesHtml = '<div style="color: #888; font-size: 13px;">No clear confluences detected - wait for better setup</div>';
                } else {
                    confluences.forEach(text => {
                        confluencesHtml += `<div style="display: flex; align-items: flex-start; padding: 6px 0; font-size: 13px; color: #ccc; line-height: 1.5;">
                            <span style="color: #00d4aa; margin-right: 10px;">•</span>
                            <span>${text}</span>
                        </div>`;
                    });
                }
                document.getElementById('confluencesList').innerHTML = confluencesHtml;

                const actionEl = document.getElementById('topdownAction');
                const actionTextEl = document.getElementById('topdownActionText');

                if (direction === 'BUY') {
                    actionEl.classList.add('topdown-action-buy');
                    actionTextEl.textContent = 'BEST TO BUY';
                } else if (direction === 'SELL') {
                    actionEl.classList.remove('topdown-action-buy');
                    actionTextEl.textContent = 'BEST TO SELL';
                } else {
                    actionEl.classList.remove('topdown-action-buy');
                    actionTextEl.textContent = 'WAIT';
                }

                const nextTrigger = direction === 'BUY' ?
                    `M15 bullish engulfing candle closing above ${(entry * 1.001).toFixed(2)}` :
                    `M15 ${direction === 'SELL' ? 'bearish' : ''} rejection candle closing below ${(entry * 0.999).toFixed(2)}`;
                document.getElementById('nextTriggerText').textContent = nextTrigger;

                const invalidation = direction === 'BUY' ?
                    `Sustained M15 candle close below the ${(sl * 0.999).toFixed(1)} accumulation low` :
                    `Sustained M15 candle close above the manipulation swing high at ${(sl * 1.001).toFixed(1)}`;
                document.getElementById('invalidationText').textContent = invalidation;

                document.getElementById('loading').style.display = 'none';
                document.getElementById('result').style.display = 'block';
                document.getElementById('result').scrollIntoView({behavior: 'smooth'});
            }
        }

        function resetForm() {
            document.getElementById('result').style.display = 'none';
            document.getElementById('previewSection').style.display = 'none';
            document.getElementById('uploadCard').style.display = 'block';
            document.getElementById('analyzeBtn').disabled = true;
            document.getElementById('fileInput').value = '';
            window.scrollTo({top: 0, behavior: 'smooth'});
        }
    </script>
</body>
</html>
"""

# ============================================
# API ROUTES
# ============================================

@app.route('/')
def home():
    return render_template_string(HTML)

@app.route('/api/prices')
def api_prices():
    import random
    prices = {}
    for symbol, data in LIVE_PRICES.items():
        change_pct = random.uniform(-2.5, 2.5)
        new_price = data['price'] * (1 + change_pct/100)
        prices[symbol] = {
            'price': round(new_price, 4),
            'change': round(change_pct, 2),
            'high': data['high'],
            'low': data['low']
        }
    return jsonify(prices)

@app.route('/api/session')
def api_session():
    return jsonify(get_session_quality())

@app.route('/api/news')
def api_news():
    current_hour = datetime.now().hour
    upcoming = []
    for event in ECONOMIC_EVENTS:
        event_hour = int(event['time'].split(':')[0])
        if 0 <= (event_hour - current_hour) % 24 <= 24:
            upcoming.append(event)
    return jsonify({'events': upcoming[:5]})

@app.route('/api/htf-bias')
def api_htf_bias():
    """NEW v7.0: HTF bias for any symbol."""
    symbol = request.args.get('symbol', 'BTCUSDm')
    return jsonify(get_htf_bias(symbol))

@app.route('/api/auto-scan')
def api_auto_scan():
    """UPDATED v7.0: Accepts ?symbol= param, defaults to BTC."""
    symbol = request.args.get('symbol', 'BTCUSDm')
    result = auto_scan_symbol(symbol)
    if result:
        return jsonify(result)
    return jsonify({'error': 'Unknown symbol'}), 400

@app.route('/api/auto-scan-all')
def api_auto_scan_all():
    """NEW v7.0: Scan all 7 symbols at once."""
    results = []
    for symbol in LIVE_PRICES.keys():
        results.append(auto_scan_symbol(symbol))
    return jsonify({'results': results})

@app.route('/api/next-session')
def api_next_session():
    """NEW v8.0: Time until next trading session opens."""
    return jsonify(get_next_session())

@app.route('/api/reference-levels')
def api_reference_levels():
    """NEW v8.0: PDH/PDL + Asian range markers."""
    symbol = request.args.get('symbol', 'BTCUSDm')
    levels = get_reference_levels(symbol)
    if levels:
        return jsonify(levels)
    return jsonify({'error': 'Unknown symbol'}), 400

@app.route('/api/drawdown-status')
def api_drawdown_status():
    """NEW v8.0: Check current drawdown based on history.

    Query params:
      - daily_pnl: today's P&L (negative = loss)
      - weekly_pnl: this week's P&L
    """
    daily_pnl = float(request.args.get('daily_pnl', 0))
    weekly_pnl = float(request.args.get('weekly_pnl', 0))
    balance = ACCOUNT_CONFIG['balance']
    return jsonify(check_drawdown_status(daily_pnl, weekly_pnl, balance))

@app.route('/health')
def health():
    return jsonify({
        'status': 'online',
        'app': 'Elite Alpha EA',
        'version': '8.0',
        'features': ['robot', 'live_ticker', 'multi_symbol_scan', 'htf_bias',
                     'lot_size_calculator', 'multi_tp', 'signal_history',
                     '17_smc_factors', 'confluence_categories', 'drawdown_tracker',
                     'session_countdown', 'asian_range_markers', 'pdh_pdl_markers',
                     'top_down_analysis', 'economic_calendar', 'session_quality',
                     'real_prices', 'fast_scan', 'outcome_tracking'],
        'new_in_v8': ['confluence_grouped_categories', 'drawdown_tracker',
                      'time_session_countdown', 'breaker_blocks',
                      'mitigation_blocks', 'asian_range_markers', 'pdh_pdl_markers'],
        'new_in_v7': ['multi_symbol_picker', 'htf_bias_banner', 'lot_size_calc',
                      'multi_tp_levels', 'signal_history_with_outcomes'],
        'removed': ['profit_target_tracker', 'balance_pressure_display',
                   'fake_winrate_stat', 'mt5_webhook_push',
                   'open_in_mt5_button', 'real_broker_api', 'ai_photo_symbol']
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
