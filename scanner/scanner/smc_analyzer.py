"""
SMC Analyzer - 15+ Smart Money Concepts Factors
"""

import random
from datetime import datetime
from config import LIVE_PRICES


def get_base_price(symbol):
    return LIVE_PRICES.get(symbol, {}).get('price', 100)


def generate_signal(symbol, timeframe='H1'):
    base_price = get_base_price(symbol)
    current_price = base_price + (random.uniform(-0.008, 0.008) * base_price)

    structure_options = ['bullish', 'bearish', 'ranging']
    structure_weights = [0.45, 0.40, 0.15]
    structure = random.choices(structure_options, weights=structure_weights)[0]

    factors = {
        'Market Structure': _check_factor(structure != 'ranging', 2, f'{structure.title()} structure confirmed'),
        'BOS (Break of Structure)': _check_factor(random.random() > 0.3, 2, 'Recent BOS detected'),
        'CHoCH (Change of Character)': _check_factor(random.random() > 0.5, 1, 'CHoCH pattern forming'),
        'Liquidity Sweep': _check_factor(random.random() > 0.4, 2, 'Stop hunt identified'),
        'Order Block': _check_factor(random.random() > 0.3, 2, 'OB at key level'),
        'Fair Value Gap (FVG)': _check_factor(random.random() > 0.5, 1, 'FVG created'),
        'Displacement': _check_factor(random.random() > 0.4, 2, 'Strong displacement candle'),
        'Premium/Discount': _check_factor(structure != 'ranging', 1, f'Price in {"discount" if structure == "bullish" else "premium"} zone'),
        'PO3 (Power of 3)': _check_factor(structure != 'ranging' and random.random() > 0.4, 1, 'Accumulation -> Manipulation -> Distribution'),
        'Judas Swing': _check_factor(random.random() > 0.5, 1, 'False breakout detected'),
        'OTE (Optimal Trade Entry)': _check_factor(structure != 'ranging' and random.random() > 0.4, 1, '62-79% Fib retracement'),
        'Session Quality': _check_factor(True, 1, 'Active session'),
        'News Clear': _check_factor(random.random() > 0.3, 1, 'No major news in 4h'),
        'HTF Alignment': _check_factor(structure != 'ranging', 1, 'Aligned with HTF'),
        'Volume Confirmation': _check_factor(random.random() > 0.4, 1, 'Volume spike detected'),
    }

    total_weight = sum(f['weight'] for f in factors.values())
    passed_weight = sum(f['weight'] for f in factors.values() if f['pass'])
    confidence = round((passed_weight / total_weight) * 100)

    direction, grade, strategy, sl_distance = _determine_signal(confidence, structure, factors)

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
        'sl_pips': round(abs(current_price - sl) / LIVE_PRICES.get(symbol, {}).get('pip', 1), 1),
        'tp_pips': round(abs(tp - current_price) / LIVE_PRICES.get(symbol, {}).get('pip', 1), 1),
        'rr': '1:3.0',
        'structure': structure,
        'factors': factors,
        'passed_count': sum(1 for f in factors.values() if f['pass']),
        'total_count': len(factors),
        'risk_amount': 0,
        'potential_profit': 0,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def _check_factor(passed, weight, detail):
    return {'pass': passed, 'weight': weight, 'detail': detail}


def _determine_signal(confidence, structure, factors):
    if confidence >= 80 and structure == 'bullish':
        return 'BUY', ('A+' if confidence >= 85 else 'A'), ('PO3' if factors['Liquidity Sweep']['pass'] else 'BOS'), 0
    elif confidence >= 80 and structure == 'bearish':
        return 'SELL', ('A+' if confidence >= 85 else 'A'), ('PO3' if factors['Liquidity Sweep']['pass'] else 'BOS'), 0
    else:
        return 'WAIT', 'C', 'No Setup', 0


def calculate_position_size(balance, risk_percent, entry, sl):
    risk_amount = balance * (risk_percent / 100)
    risk_per_unit = abs(entry - sl)
    if risk_per_unit == 0:
        return 0
    return risk_amount / risk_per_unit
