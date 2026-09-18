"""
Top-Down Analysis Generator (Vertex Alpha Style)
"""


def generate_topdown_analysis(signal):
    entry = signal['entry']
    sl = signal['sl']
    direction = signal['direction']

    if direction == 'BUY':
        next_trigger = f'M15 bullish engulfing candle closing above {entry * 1.001:.2f}'
        invalidation = f'Sustained M15 candle close below the {sl * 0.999:.1f} accumulation low'
    else:
        next_trigger = f'M15 bearish rejection candle closing below {entry * 0.999:.2f}'
        invalidation = f'Sustained M15 candle close above the manipulation swing high at {sl * 1.001:.1f}'

    return {
        'best_action': f'BEST TO {"BUY" if direction == "BUY" else ("SELL" if direction == "SELL" else "WAIT")}',
        'next_trigger': next_trigger,
        'invalidation': invalidation
    }
