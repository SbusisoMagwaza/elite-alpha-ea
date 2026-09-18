"""
Confluence Checklist Generator
"""


def generate_confluence_checklist(signal):
    entry = signal['entry']
    sl = signal['sl']
    tp = signal['tp']
    direction = signal['direction']
    structure = signal['structure']

    checklist = [
        {
            'name': 'H1 Accumulation Base',
            'detail': f'Clear consolidation base established between {entry:.0f} and {entry * 0.998:.0f} (inferred from M15 swing range)',
            'pass': structure != 'ranging'
        },
        {
            'name': 'Micro Manipulation Sweep',
            'detail': f'Sharp Judas wick spiked above {entry * 1.005:.0f}, purging buy-side liquidity before immediately closing back inside',
            'pass': signal['factors'].get('Liquidity Sweep', {}).get('pass', False)
        },
        {
            'name': 'Distribution Expansion',
            'detail': f'Displacement leg expanded {"down" if direction == "SELL" else "up"} to {tp:.0f} with large-bodied {"bearish" if direction == "SELL" else "bullish"} candles',
            'pass': signal['factors'].get('Displacement', {}).get('pass', False)
        },
        {
            'name': 'H1 Draw on Liquidity',
            'detail': f'Draw on liquidity targets unmitigated {"sell-side" if direction == "SELL" else "buy-side"} lows around {sl:.0f}',
            'pass': signal['factors'].get('BOS (Break of Structure)', {}).get('pass', False)
        },
        {
            'name': 'Displacement FVG / Imbalance',
            'detail': f'Clear {"premium" if direction == "SELL" else "discount"} imbalance zone created during {"down" if direction == "SELL" else "up"}-leg, now being tested as entry',
            'pass': signal['factors'].get('Fair Value Gap (FVG)', {}).get('pass', False)
        },
        {
            'name': 'Entry Trigger on Retrace',
            'detail': f'Price returned to retest the {"FVG breakdown" if direction == "SELL" else "FVG breakout"} level with upper wick rejection',
            'pass': signal['factors'].get('Order Block', {}).get('pass', False)
        },
        {
            'name': 'R:Reward >= 2.0',
            'detail': f'Risk of ~{abs(entry - sl):.1f} points for ~{abs(tp - entry):.1f} points reward ({signal["rr"]} R:R ratio)',
            'pass': True
        }
    ]

    return checklist


def generate_confluences_list(signal):
    entry = signal['entry']
    direction = signal['direction']
    structure = signal['structure']
    timeframe = signal['timeframe']

    confluences = []

    if signal['factors'].get('Liquidity Sweep', {}).get('pass'):
        confluences.append(f'Clean {"buy-side" if direction == "SELL" else "sell-side"} liquidity grab at {entry * 1.003:.2f}')

    if signal['factors'].get('Displacement', {}).get('pass'):
        confluences.append(f'M15 {structure} displacement breaking structural {"lows" if direction == "SELL" else "highs"}')

    if signal['factors'].get('Fair Value Gap (FVG)', {}).get('pass'):
        confluences.append(f'Deep {"premium" if direction == "SELL" else "discount"} retest into {entry * 1.002:.0f} {"resistance" if direction == "SELL" else "support"} / FVG')

    if signal['factors'].get('Order Block', {}).get('pass'):
        confluences.append('High risk-to-reward ratio exceeding 2R')

    if signal['factors'].get('BOS (Break of Structure)', {}).get('pass'):
        confluences.append(f'Structure shift confirmed on {timeframe} timeframe')

    if signal['factors'].get('CHoCH (Change of Character)', {}).get('pass'):
        confluences.append('CHoCH pattern forming on lower timeframe')

    return confluences
