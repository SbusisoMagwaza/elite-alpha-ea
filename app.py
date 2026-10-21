"""
Elite Alpha EA v9.1.0 — exact Exness quotes + read-only MT5 OHLC transport.

Safety changes:
- No public proxy prices or static quote estimates are presented or scanned.
- Trade-direction scanners stay in WAIT until real MT5 candle history is available.
- Randomly generated market structure, bias, levels and scores have been removed.
- Economic calendar events are fetched from FinanceCalendar.com with visible attribution.
- News analysis is conditional scenario information, not a guaranteed prediction.
"""

from flask import Flask, request, jsonify, render_template_string
import json
import re
import os
import hmac
import time
import math
import base64
import io
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
    JOHANNESBURG_TZ = ZoneInfo('Africa/Johannesburg')
except Exception:
    JOHANNESBURG_TZ = None

def johannesburg_now():
    """Return app timestamps in the partner's Johannesburg timezone (UTC+2)."""
    return datetime.now(JOHANNESBURG_TZ) if JOHANNESBURG_TZ else datetime.now()

import urllib.request
import urllib.parse

app = Flask(__name__)

# ============================================
# v9.0: SYMBOL METADATA — NEVER USED AS A MARKET QUOTE
# Current prices can only come from a fresh MT5 bridge quote or an explicitly
# captured MT5 screenshot in the browser. There are no proxy/static prices.
# ============================================

SYMBOL_CONFIG = {
    'XAUUSDm': {'pip': 0.10, 'lot_value': 1.0},
    'BTCUSDm': {'pip': 1.0, 'lot_value': 1.0},
    'EURUSDm': {'pip': 0.0001, 'lot_value': 10.0},
    'GBPUSDm': {'pip': 0.0001, 'lot_value': 10.0},
    'USDJPYm': {'pip': 0.01, 'lot_value': 6.67},
    'USTECm':  {'pip': 1.0, 'lot_value': 1.0},
    'US30m':   {'pip': 1.0, 'lot_value': 1.0},
}

# v8.9.2: read-only quote bridge retained in v9.0. The EA sends bid/ask; it cannot trade.
MT5_BRIDGE_TOKEN = os.environ.get('MT5_BRIDGE_TOKEN', '')
MT5_QUOTES = {}
MT5_QUOTES_LAST_UPDATE = None
# Keyed by (symbol, timeframe); each record stores closed OHLC bars only.
MT5_CANDLES = {}
MT5_CANDLE_MAX_AGE_SECONDS = 180
MT5_TIMEFRAMES = ('M15', 'H1', 'H4', 'D1')
MT5_CANDLE_MIN_COUNTS = {'M15': 40, 'H1': 40, 'H4': 30, 'D1': 30}
MT5_CANDLE_MAX_PER_SERIES = 120

def get_mt5_quote(symbol, max_age_seconds=10):
    """Return a fresh quote pushed by the user's MT5 terminal, if available."""
    quote = MT5_QUOTES.get(symbol)
    if not quote:
        return None
    if time.time() - quote.get('received_at', 0) > max_age_seconds:
        return None
    return quote

def get_mt5_candle_status(symbol):
    """Describe which fresh, closed candle series have reached Render."""
    now = time.time()
    frames = {}
    for timeframe in MT5_TIMEFRAMES:
        record = MT5_CANDLES.get((symbol, timeframe))
        age = round(now - record.get('received_at', 0), 1) if record else None
        candles = record.get('candles', []) if record else []
        fresh = bool(record and age is not None and age <= MT5_CANDLE_MAX_AGE_SECONDS)
        minimum = MT5_CANDLE_MIN_COUNTS[timeframe]
        frames[timeframe] = {
            'available': fresh,
            'bars': len(candles) if fresh else 0,
            'minimum_bars': minimum,
            'age_seconds': age,
            'latest_bar_time': candles[-1]['time'] if fresh and candles else None,
            'ready': bool(fresh and len(candles) >= minimum),
        }
    return {
        'symbol': symbol,
        'timeframes': frames,
        'ready': all(frames[tf]['ready'] for tf in MT5_TIMEFRAMES),
        'max_age_seconds': MT5_CANDLE_MAX_AGE_SECONDS,
    }

# ============================================
# v9.0: LIVE ECONOMIC CALENDAR
# FinanceCalendar API is keyless for this usage; the UI includes the required
# visible source attribution. Cache for 5 minutes to keep requests low.
# ============================================

FINANCE_CALENDAR_API = 'https://www.financecalendar.com/wp-json/fc/v1/calendar'
FINANCE_CALENDAR_ATTRIBUTION = 'https://www.financecalendar.com'
ECONOMIC_CALENDAR_CACHE = {'events': [], 'fetched_at': 0.0, 'status': 'empty'}
ECONOMIC_CALENDAR_TTL_SECONDS = 300
ECONOMIC_CALENDAR_COUNTRIES = 'US,GB,EU,JP,CN'


def _calendar_datetime_utc(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def get_economic_calendar_data(force_refresh=False):
    """Fetch real upcoming medium/high-impact macro events; never substitute fixtures."""
    global ECONOMIC_CALENDAR_CACHE
    now_epoch = time.time()
    if (not force_refresh and ECONOMIC_CALENDAR_CACHE.get('fetched_at')
            and now_epoch - ECONOMIC_CALENDAR_CACHE['fetched_at'] < ECONOMIC_CALENDAR_TTL_SECONDS):
        return dict(ECONOMIC_CALENDAR_CACHE)

    local_now = johannesburg_now()
    if local_now.tzinfo is None:
        local_now = local_now.replace(tzinfo=timezone.utc).astimezone(JOHANNESBURG_TZ or timezone.utc)
    now_utc = local_now.astimezone(timezone.utc)
    from_date = local_now.date()
    to_date = from_date + timedelta(days=7)
    params = urllib.parse.urlencode({
        'from': from_date.isoformat(),
        'to': to_date.isoformat(),
        'country': ECONOMIC_CALENDAR_COUNTRIES,
        'tz': 'Africa/Johannesburg',
        'limit': 100,
    })
    url = FINANCE_CALENDAR_API + '?' + params
    req = urllib.request.Request(url, headers={
        'User-Agent': 'EliteAlphaEA/9.0 (economic calendar; visible attribution in app)',
        'Accept': 'application/json',
    })

    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            raw = json.loads(response.read().decode('utf-8'))
        source_events = raw.get('events', []) if isinstance(raw, dict) else raw
        if not isinstance(source_events, list):
            raise ValueError('Calendar provider returned an unexpected response shape')

        normalized = []
        for item in source_events:
            if not isinstance(item, dict):
                continue
            impact = str(item.get('impact') or '').strip().lower()
            if impact not in ('high', 'medium'):
                continue
            title = str(item.get('title') or item.get('name') or item.get('event') or '').strip()
            if not title:
                continue
            country = str(item.get('country') or '').strip()
            release_raw = item.get('release_at_utc') or item.get('time_utc')
            release_dt = _calendar_datetime_utc(release_raw)
            if release_dt:
                # Keep upcoming events and just-released events while their actual
                # values may still be populating. Exclude stale past placeholders.
                if release_dt < now_utc - timedelta(minutes=90):
                    continue
                if release_dt > now_utc + timedelta(days=8):
                    continue
                local_release = release_dt.astimezone(JOHANNESBURG_TZ or timezone.utc)
                local_date = local_release.strftime('%Y-%m-%d')
                local_time = item.get('time_local') or local_release.strftime('%H:%M')
            else:
                local_date = str(item.get('date') or '')[:10]
                local_time = str(item.get('time_local') or 'Time TBC')

            slug_source = str(item.get('id') or item.get('series_code') or title).lower()
            slug = re.sub(r'[^a-z0-9]+', '-', slug_source).strip('-')[:60]
            event_id = f'{slug}-{local_date or "date-tbc"}'
            currency = str(item.get('currency') or {
                'US': 'USD', 'GB': 'GBP', 'UK': 'GBP', 'EU': 'EUR',
                'JP': 'JPY', 'CN': 'CNY'
            }.get(country.upper(), '')).upper()
            normalized.append({
                'id': event_id,
                'title': title,
                'country': country,
                'currency': currency,
                'category': str(item.get('category') or ''),
                'impact': impact.upper(),
                'date_local': local_date,
                'time_local': str(local_time),
                'release_at_utc': release_dt.isoformat() if release_dt else str(release_raw or ''),
                'status': str(item.get('status') or ('released' if item.get('actual') is not None else 'scheduled')),
                'consensus': (item.get('consensus', item.get('forecast')) if str(item.get('consensus', item.get('forecast')) or '').strip() else None),
                'prior': (item.get('prior', item.get('previous')) if str(item.get('prior', item.get('previous')) or '').strip() else None),
                'actual': (item.get('actual') if str(item.get('actual') or '').strip() else None),
                'unit': str(item.get('unit') or ''),
                'source_name': str(item.get('source_name') or ''),
                'source_url': (str(item.get('source_url') or '') if str(item.get('source_url') or '').startswith('https://') else ''),
                'url': (str(item.get('url') or FINANCE_CALENDAR_ATTRIBUTION) if str(item.get('url') or FINANCE_CALENDAR_ATTRIBUTION).startswith('https://') else FINANCE_CALENDAR_ATTRIBUTION),
            })

        normalized.sort(key=lambda e: e.get('release_at_utc') or '9999')
        ECONOMIC_CALENDAR_CACHE = {
            'events': normalized,
            'fetched_at': now_epoch,
            'updated_at': local_now.strftime('%Y-%m-%d %H:%M:%S SAST'),
            'status': 'live',
            'message': '',
        }
        return dict(ECONOMIC_CALENDAR_CACHE)
    except Exception as exc:
        if ECONOMIC_CALENDAR_CACHE.get('events'):
            stale = dict(ECONOMIC_CALENDAR_CACHE)
            stale['status'] = 'stale'
            stale['message'] = 'Calendar refresh failed; showing cached events. Verify event times before use.'
            return stale
        return {
            'events': [], 'fetched_at': 0, 'updated_at': None,
            'status': 'unavailable',
            'message': 'Live calendar could not be reached. No placeholder events are shown.',
            'error': str(exc)[:180],
        }


def _macro_number(value):
    if value is None:
        return None
    text = str(value).replace(',', '')
    match = re.search(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)', text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _event_family(event):
    text = (str(event.get('title', '')) + ' ' + str(event.get('category', ''))).lower()
    if re.search(r'\b(cpi|ppi|pce|inflation|producer price|consumer price|price index)\b', text):
        return 'inflation'
    if re.search(r'\b(payroll|employment|unemployment|jobless|claims|wage|labor market|labour market|nonfarm|non-farm)\b', text):
        return 'labor'
    if re.search(r'\b(fomc|rate decision|interest rate|central bank|monetary policy|bank of england|ecb|boj|boe)\b', text):
        return 'central_bank'
    if re.search(r'\b(gdp|retail sales|industrial production|pmi|ism|growth)\b', text):
        return 'growth'
    return 'other'


def _asset_effect_for_currency(symbol, currency, stance):
    """Qualitative conditional mapping, not a trade signal or probability."""
    if not stance or stance == 'mixed':
        return 'Mixed/unclear reaction is possible; wait for the release and price confirmation.'
    firm = stance == 'firm'
    if currency == 'USD':
        if symbol == 'XAUUSDm':
            return 'A firmer USD/yield outlook can pressure gold lower.' if firm else 'A softer USD/yield outlook can support gold.'
        if symbol in ('EURUSDm', 'GBPUSDm'):
            return 'USD support can pressure this pair lower.' if firm else 'USD softness can support this pair higher.'
        if symbol == 'USDJPYm':
            return 'USD support can lift this pair.' if firm else 'USD softness can weigh on this pair.'
        if symbol in ('USTECm', 'US30m'):
            return 'Higher-yield expectations can pressure index valuations; the reaction can reverse.' if firm else 'Lower-yield expectations can support valuations; the reaction can reverse.'
        if symbol == 'BTCUSDm':
            return 'Potential USD/liquidity pressure, but crypto response is mixed and not one-directional.'
    if currency == 'GBP' and symbol == 'GBPUSDm':
        return 'Stronger GBP fundamentals can support this pair.' if firm else 'Weaker GBP fundamentals can pressure this pair.'
    if currency == 'EUR' and symbol == 'EURUSDm':
        return 'Stronger EUR fundamentals can support this pair.' if firm else 'Weaker EUR fundamentals can pressure this pair.'
    if currency == 'JPY' and symbol == 'USDJPYm':
        return 'A firmer JPY can weigh on USDJPY.' if firm else 'A softer JPY can support USDJPY.'
    return 'This event may have an indirect or mixed effect on this symbol; no one-way call is justified.'


def _stance_from_surprise(event, family, comparison):
    if family == 'central_bank':
        return 'firm' if comparison == 'above' else 'soft' if comparison == 'below' else 'mixed'
    if family in ('inflation', 'growth'):
        return 'firm' if comparison == 'above' else 'soft' if comparison == 'below' else 'mixed'
    if family == 'labor':
        text = (str(event.get('title', '')) + ' ' + str(event.get('category', ''))).lower()
        higher_is_weaker = bool(re.search(r'\b(unemployment|jobless|claims)\b', text))
        stronger = (comparison == 'below') if higher_is_weaker else (comparison == 'above')
        if comparison == 'inline':
            return 'mixed'
        return 'firm' if stronger else 'soft'
    return 'mixed'


def build_news_scenario(event, symbol):
    family = _event_family(event)
    currency = str(event.get('currency') or '').upper()
    actual = _macro_number(event.get('actual'))
    consensus = _macro_number(event.get('consensus'))
    prior = event.get('prior')
    actual_vs_consensus = None
    released_note = None

    if actual is not None and consensus is not None:
        tolerance = max(abs(consensus) * 0.002, 0.01)
        if actual > consensus + tolerance:
            comparison = 'above'
            comparison_label = 'above consensus'
        elif actual < consensus - tolerance:
            comparison = 'below'
            comparison_label = 'below consensus'
        else:
            comparison = 'inline'
            comparison_label = 'roughly in line with consensus'
        stance = _stance_from_surprise(event, family, comparison)
        effect = _asset_effect_for_currency(symbol, currency, stance)
        actual_vs_consensus = {
            'actual': str(event.get('actual')),
            'consensus': str(event.get('consensus')),
            'label': comparison_label,
        }
        released_note = f"Actual was {comparison_label}. {effect}"

    if family == 'central_bank':
        scenarios = [
            {'label': 'More hawkish than expected', 'text': _asset_effect_for_currency(symbol, currency, 'firm')},
            {'label': 'More dovish than expected', 'text': _asset_effect_for_currency(symbol, currency, 'soft')},
            {'label': 'In line / mixed statement', 'text': _asset_effect_for_currency(symbol, currency, 'mixed')},
        ]
    elif family in ('inflation', 'labor', 'growth'):
        higher_stance = _stance_from_surprise(event, family, 'above')
        lower_stance = _stance_from_surprise(event, family, 'below')
        high_label = 'Actual higher / hotter than consensus' if family == 'inflation' else 'Actual above consensus'
        low_label = 'Actual lower / cooler than consensus' if family == 'inflation' else 'Actual below consensus'
        scenarios = [
            {'label': high_label, 'text': _asset_effect_for_currency(symbol, currency, higher_stance)},
            {'label': low_label, 'text': _asset_effect_for_currency(symbol, currency, lower_stance)},
            {'label': 'Near consensus / mixed details', 'text': _asset_effect_for_currency(symbol, currency, 'mixed')},
        ]
    else:
        scenarios = [
            {'label': 'Before release', 'text': 'The event title alone does not support a defensible BUY/SELL direction.'},
            {'label': 'After release', 'text': 'Compare actual with consensus, then wait for the Exness chart to confirm a reaction.'},
        ]

    phase = 'POST-RELEASE' if event.get('actual') is not None else 'PRE-RELEASE / WAITING FOR DATA'
    if event.get('consensus') is None:
        summary = 'No consensus value is currently published by the calendar source. The app will not invent a pre-event direction.'
    else:
        summary = 'This is a conditional scenario map, not a prediction. Markets can price consensus in beforehand and can reverse after the release.'
    if released_note:
        summary = released_note + ' The first reaction can still reverse; this is not a trade instruction.'

    return {
        'event': event.get('title', 'Economic event'),
        'symbol': symbol,
        'phase': phase,
        'family': family,
        'summary': summary,
        'consensus': event.get('consensus'),
        'prior': prior,
        'actual': event.get('actual'),
        'actual_vs_consensus': actual_vs_consensus,
        'scenarios': scenarios,
        'caution': 'Do not enter solely because of a calendar scenario. News can cause slippage, spread widening, whipsaws and reversals. Wait for a verified Exness price and price-action confirmation.',
        'source_url': event.get('url') or FINANCE_CALENDAR_ATTRIBUTION,
    }

# ============================================
# ACCOUNT CONFIG (Settings only — not displayed on Home)
# ============================================

ACCOUNT_CONFIG = {
    'balance': 369.19,        # R-amount, used for risk calc
    'risk_pct': 1.0,          # 1% per trade
    'min_confidence': 75,     # Minimum signal confidence for a directional result
}

# v8.9 FIX: This used to be hard-coded to 80 inside auto_scan_symbol(), while
# Settings showed 75%. A scan showing 77% therefore always became WAIT. Keep
# one clear gate so the displayed setting and the actual scanner agree.
SIGNAL_MIN_CONFIDENCE = ACCOUNT_CONFIG['min_confidence']

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
    """HTF bias is unavailable until real MT5 candle bars are connected."""
    if symbol not in SYMBOL_CONFIG:
        return None
    return {
        'symbol': symbol,
        'daily': 'UNAVAILABLE',
        'h4': 'UNAVAILABLE',
        'alignment': 'Waiting for MT5 candle history',
        'alignment_color': '#888888',
        'available': False,
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
        'current_time_johannesburg': johannesburg_now().strftime('%H:%M'),
    }

# ============================================
# v8.0 NEW: ASIAN RANGE + PDH/PDL MARKERS
# Simulates previous day high/low and Asian range
# ============================================

def get_reference_levels(symbol):
    """Return an explicit unavailable state; no synthetic levels are generated."""
    if symbol not in SYMBOL_CONFIG:
        return None
    return {
        'symbol': symbol,
        'available': False,
        'reason': 'Verified MT5 OHLC candle history is not connected yet.',
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

    info = SYMBOL_CONFIG.get(symbol, {})
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

def auto_scan_symbol(symbol, custom_price=None, min_confidence=None):
    """Safe placeholder: quote alone is not candle/structure data.

    No BUY/SELL is generated until a real MT5 OHLC history feed is connected.
    custom_price is accepted only as an explicitly labelled MT5 screenshot value.
    """
    if symbol not in SYMBOL_CONFIG:
        return None
    try:
        signal_gate = int(min_confidence) if min_confidence is not None else SIGNAL_MIN_CONFIDENCE
    except (TypeError, ValueError):
        signal_gate = SIGNAL_MIN_CONFIDENCE
    signal_gate = max(50, min(95, signal_gate))

    quote = get_mt5_quote(symbol)
    if quote and float(quote.get('price', 0) or 0) > 0:
        current_price = float(quote['price'])
        price_source = 'MT5 live bridge'
    else:
        try:
            screenshot_price = float(custom_price) if custom_price is not None else None
        except (TypeError, ValueError):
            screenshot_price = None
        if screenshot_price is not None and screenshot_price > 0:
            current_price = screenshot_price
            price_source = 'MT5 screenshot'
        else:
            current_price = None
            price_source = 'unavailable'

    candle_status = get_mt5_candle_status(symbol)
    if current_price is None:
        reason = 'WAIT: no fresh exact Exness price. Connect the MT5 bridge or upload a current MT5 chart.'
    elif not candle_status['ready']:
        missing = [tf for tf, info in candle_status['timeframes'].items() if not info['ready']]
        reason = 'WAIT: exact price is live; waiting for enough fresh closed MT5 candles on ' + ', '.join(missing) + '. Keep MT5 open while history loads.'
    else:
        reason = 'WAIT: fresh MT5 candles are received, but the deterministic strategy is still disabled pending validation/backtesting. No trade levels are fabricated.'

    return {
        'symbol': symbol,
        'timeframe': 'H1',
        'price': round(current_price, 5) if current_price is not None else None,
        'price_source': price_source,
        'direction': 'WAIT',
        'confidence': None,
        'grade': '—',
        'strategy': 'No fabricated setup',
        'entry': None,
        'sl': None,
        'tp': None,
        'tp1': None,
        'tp2': None,
        'tp3': None,
        'rr': '—',
        'structure': 'UNAVAILABLE',
        'factors': {},
        'factors_grouped': {},
        'passed_count': 0,
        'total_count': 0,
        'lot_info': None,
        'signal_min_confidence': signal_gate,
        'signal_reason': reason,
        'signal_available': False,
        'candle_status': candle_status,
        'timestamp': johannesburg_now().strftime('%Y-%m-%d %H:%M:%S %Z'),
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
    <!-- v8.3 OCR: Tesseract.js library for reading chart prices -->
    <script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>
</head>
<body>

    <!-- HOME TAB -->
    <div class="tab-content active" id="home-tab">
        <div class="home-header">
            <div class="robot-container">
                <img src="/static/robot_small.jpg" alt="Elite Alpha EA Robot">
            </div>
            <div class="app-title-home">Elite Alpha EA</div>
            <div class="scanner-name">Precision Scanner v9.0.0</div>
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
                <div style="font-size: 10px; color: #888;" id="countdownActive">-- SAST</div>
            </div>
        </div>

        <!-- HTF BIAS BANNER (NEW v7.0) -->
        <div class="htf-banner" id="htfBanner" style="display: none;">
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
            <div class="drawdown-title" style="color: #ffd700;" id="drawdownTitle">🛡️ Risk Tracker (not synced to MT5)</div>
            <div class="drawdown-message" id="drawdownMessage" style="color: #ffd700;">MT5 account history is not connected; these values are not live account risk.</div>
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
            <div class="auto-scan-sub">Exact MT5 quotes and closed candles only. Signals stay WAIT until rules are validated.</div>

            <!-- v9.0: verified MT5 price banner; no public proxy -->
            <div id="livePricePreview" style="background: rgba(0, 212, 170, 0.1); border: 1px solid rgba(0, 212, 170, 0.4); border-radius: 8px; padding: 10px; margin-bottom: 12px; text-align: center;">
                <div style="font-size: 10px; color: #00d4aa; font-weight: 700; letter-spacing: 1px; margin-bottom: 4px;">📡 VERIFIED EXNESS PRICE (MT5 ONLY)</div>
                <div style="font-size: 22px; color: #00d4aa; font-weight: 800;" id="livePriceValue">—</div>
                <div style="font-size: 10px; color: #888; margin-top: 2px;" id="livePriceSource">Loading...</div>
                <div style="font-size: 10px; color: #ffd700; margin-top: 6px;">Only fresh MT5 quotes or a recent MT5 screenshot are shown; stale/missing data stays blank.</div>
            </div>

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

            <button class="auto-scan-btn" id="autoScanBtn" onclick="runAutoScan()">🎯 SCAN <span id="scanBtnSymbol">BTC</span></button>
            <div class="auto-scan-result" id="autoScanResult"></div>
        </div>

        <!-- v8.0 NEW: REFERENCE LEVELS -->
        <div class="ref-levels" id="refLevels" style="display: none;">
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

        <!-- LIVE ECONOMIC CALENDAR + CONDITIONAL SCENARIOS -->
        <div class="news-panel">
            <div class="news-title">📰 Live Economic Calendar · SAST</div>
            <div id="newsStatus" style="font-size:11px;color:#aaa;margin:0 0 8px;">Loading live calendar…</div>
            <div id="newsList"></div>
            <div style="font-size:10px;color:#777;margin-top:8px;">Calendar source: <a href="https://www.financecalendar.com" target="_blank" rel="noopener" style="color:#00d4aa;">FinanceCalendar.com</a></div>
            <div id="newsScenarioPanel" style="display:none;margin-top:12px;padding:12px;background:rgba(0,0,0,.32);border:1px solid rgba(0,212,170,.25);border-radius:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
                    <strong style="color:#00d4aa;font-size:12px;">CONDITIONAL EVENT OUTLOOK</strong>
                    <button onclick="closeNewsScenario()" aria-label="Close" style="border:0;background:transparent;color:#aaa;font-size:18px;">×</button>
                </div>
                <label for="newsAssetSelect" style="display:block;margin-top:8px;font-size:11px;color:#aaa;">View scenario for</label>
                <select id="newsAssetSelect" onchange="refreshNewsScenarioAsset()" style="width:100%;margin:5px 0 8px;padding:8px;background:#071318;color:#fff;border:1px solid #24534b;border-radius:7px;">
                    <option value="XAUUSDm">XAUUSDm · Gold</option><option value="BTCUSDm">BTCUSDm · Bitcoin</option><option value="EURUSDm">EURUSDm</option><option value="GBPUSDm">GBPUSDm</option><option value="USDJPYm">USDJPYm</option><option value="USTECm">USTECm</option><option value="US30m">US30m</option>
                </select>
                <div id="newsScenarioContent" style="font-size:12px;color:#ddd;line-height:1.5;">Choose an event to view conditional scenarios.</div>
            </div>
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

    <!-- SCAN TAB (OCR v8.3) -->
    <div class="tab-content" id="scan-tab">
        <div class="card-title" style="padding: 10px 0;">📊 MT5 Chart Upload (symbol/price OCR)</div>

        <!-- v8.9 FIX: Same live-price theme as Home, now also on the scanner -->
        <div id="scanLivePricePreview" style="background: rgba(0, 212, 170, 0.1); border: 1px solid rgba(0, 212, 170, 0.4); border-radius: 8px; padding: 10px; margin-bottom: 12px; text-align: center;">
            <div style="font-size: 10px; color: #00d4aa; font-weight: 700; letter-spacing: 1px; margin-bottom: 4px;">📡 VERIFIED EXNESS PRICE USED FOR SCAN</div>
            <div style="font-size: 22px; color: #00d4aa; font-weight: 800;" id="scanLivePriceValue">—</div>
            <div style="font-size: 10px; color: #888; margin-top: 2px;" id="scanLivePriceSource">Loading...</div>
        </div>

        <!-- v8.9 FIX: Symbol-only OCR; price always comes from the live feed -->
        <div style="background: linear-gradient(135deg, rgba(0, 212, 170, 0.15), rgba(0, 150, 255, 0.1)); border: 2px solid rgba(0, 212, 170, 0.4); border-radius: 12px; padding: 14px; margin-bottom: 15px;">
            <div style="font-size: 13px; font-weight: 800; color: #00d4aa; margin-bottom: 6px;">📸 SMART CHART UPLOAD</div>
            <div style="font-size: 12px; color: #ccc; line-height: 1.5;">
                Upload your MT5 chart. The app identifies the <strong style="color: #00d4aa;">symbol</strong> and reads the highlighted current-price box automatically. No price picker and no typing while the market moves.
            </div>
        </div>

        <!-- v8.3 NEW: Upload area -->
        <div class="upload-card" id="uploadCard">
            <span class="upload-icon">📸</span>
            <div class="upload-text">Choose Chart Photo</div>
            <div class="upload-hint">Tap below to take photo or pick from gallery</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 14px;">
                <button onclick="openCamera()" style="padding: 12px 8px; background: linear-gradient(135deg, rgba(0, 212, 170, 0.2), rgba(0, 150, 255, 0.1)); border: 2px solid #00d4aa; color: #00d4aa; border-radius: 10px; font-size: 13px; font-weight: 700; cursor: pointer;">
                    📷 Camera
                </button>
                <button onclick="openGallery()" style="padding: 12px 8px; background: linear-gradient(135deg, rgba(0, 150, 255, 0.2), rgba(0, 212, 170, 0.1)); border: 2px solid #0096ff; color: #0096ff; border-radius: 10px; font-size: 13px; font-weight: 700; cursor: pointer;">
                    🖼️ Gallery
                </button>
            </div>
            <input type="file" id="fileInput" accept="image/*" onchange="handleFile(event)" style="position: absolute; left: -9999px;">
        </div>

        <div class="preview-section" id="previewSection">
            <img id="previewImage" src="" alt="Chart">
            <div id="ocrStatus" style="margin-top: 10px; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 8px; font-size: 13px; color: #ccc; text-align: center;">📷 Waiting for image...</div>
            <div id="ocrResult" style="margin-top: 8px;"></div>
            <button class="change-btn" onclick="openGallery()">📸 Take Another Photo</button>
        </div>

        <div class="card">
            <div class="card-title">📊 Chart Details</div>

            <div class="form-group">
                <label>💱 Symbol</label>
                <select id="symbol" onchange="updateScanLivePricePreview(); useLivePrice();">
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

            <div class="form-group">
                <label>💲 Verified MT5 price only</label>
                <input type="text" id="currentPrice" value="" readonly placeholder="Waiting for live price..." style="color: #00d4aa; font-weight: 700;">
                <div style="font-size: 11px; color: #888; margin-top: 5px;">No public proxy or estimate is used. Without exact price and candle history, the result remains WAIT.</div>
            </div>

            <div class="form-group">
                <label>📈 Visible Trend (from your chart)</label>
                <select id="visibleTrend">
                    <option value="auto">🤖 Auto-detect from HTF bias</option>
                    <option value="bullish">🟢 Bullish (Higher highs/lows)</option>
                    <option value="bearish">🔴 Bearish (Lower highs/lows)</option>
                    <option value="ranging">🟡 Ranging / Choppy</option>
                </select>
            </div>

            <button class="analyze-btn" id="analyzeBtn" onclick="analyzeImage()">🤖 Check MT5 Price / Scan Status</button>
        </div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="color: #00d4aa; font-weight: 600;">Checking MT5 data…</p>
            <p style="color: #888; font-size: 12px; margin-top: 8px;">Reading the chart price; real candle analysis is not connected yet</p>
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

            <div class="best-action" id="bestAction" style="display: none;">BEST TO BUY</div>

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
                    <span class="topdown-action-text" id="topdownActionText">WAIT — candle feed required</span>
                </div>
                <div class="topdown-trigger-row">
                    <div class="topdown-trigger-label">⏭️ NEXT TRIGGER</div>
                    <div class="topdown-trigger-text" id="nextTriggerText">No verified candle trigger is available yet</div>
                </div>
                <div class="topdown-trigger-row">
                    <div class="topdown-trigger-label">🚫 INVALIDATION</div>
                    <div class="topdown-trigger-text" id="invalidationText">No verified invalidation level is available yet</div>
                </div>
            </div>

            <button class="new-scan-btn" onclick="resetForm()">🔄 Scan Another Chart</button>
        </div>
    </div>

    <!-- SETTINGS TAB v8.1 — CLEANED UP -->
    <div class="tab-content" id="settings-tab">
        <div class="card-title" style="padding: 10px 0;">⚙️ Settings</div>

        <!-- MT5 Push Notifications Setup -->
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
            <p style="margin-top: 10px;">Pair MT5 with this app to get push alerts. Setup takes 2 min.</p>
        </div>

        <!-- v8.1 NEW: Editable Account Settings -->
        <div class="setup-instructions">
            <h4>💼 Account & Risk Settings</h4>
            <p style="font-size: 11px; color: #888; margin-bottom: 12px;">Used for lot size calculation. Saved on this device.</p>

            <div style="margin-bottom: 14px;">
                <label style="display: block; color: #888; font-size: 11px; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px;">💰 Account Balance (R)</label>
                <input type="number" id="settingsBalanceInput" value="369.19" min="100" step="0.01"
                    style="width: 100%; padding: 12px; background: rgba(0,0,0,0.3); border: 1px solid rgba(0,150,255,0.3); color: #00d4aa; border-radius: 8px; font-size: 16px; font-weight: 700;">
            </div>

            <div style="margin-bottom: 14px;">
                <label style="display: block; color: #888; font-size: 11px; font-weight: 600; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;">📊 Risk per Trade</label>
                <div id="riskButtons" style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 6px;">
                    <button class="risk-btn" data-risk="0.5" onclick="setRisk(0.5, this)" style="padding: 10px 4px; background: rgba(0,150,255,0.1); border: 1px solid rgba(0,150,255,0.3); color: #ccc; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer;">0.5%</button>
                    <button class="risk-btn active" data-risk="1.0" onclick="setRisk(1.0, this)" style="padding: 10px 4px; background: rgba(0,212,170,0.2); border: 1px solid #00d4aa; color: #00d4aa; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer; box-shadow: 0 0 10px rgba(0,212,170,0.3);">1%</button>
                    <button class="risk-btn" data-risk="1.5" onclick="setRisk(1.5, this)" style="padding: 10px 4px; background: rgba(0,150,255,0.1); border: 1px solid rgba(0,150,255,0.3); color: #ccc; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer;">1.5%</button>
                    <button class="risk-btn" data-risk="2.0" onclick="setRisk(2.0, this)" style="padding: 10px 4px; background: rgba(0,150,255,0.1); border: 1px solid rgba(0,150,255,0.3); color: #ccc; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer;">2%</button>
                </div>
            </div>

            <div style="margin-bottom: 14px;">
                <label style="display: block; color: #888; font-size: 11px; font-weight: 600; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 1px;">🎯 Min Confidence</label>
                <div id="confButtons" style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px;">
                    <button class="conf-btn" data-conf="65" onclick="setConfidence(65, this)" style="padding: 10px 4px; background: rgba(0,150,255,0.1); border: 1px solid rgba(0,150,255,0.3); color: #ccc; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer;">Aggressive<br><span style="font-size: 9px; font-weight: 400; opacity: 0.7;">65%</span></button>
                    <button class="conf-btn active" data-conf="75" onclick="setConfidence(75, this)" style="padding: 10px 4px; background: rgba(0,212,170,0.2); border: 1px solid #00d4aa; color: #00d4aa; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer; box-shadow: 0 0 10px rgba(0,212,170,0.3);">Balanced<br><span style="font-size: 9px; font-weight: 400; opacity: 0.7;">75%</span></button>
                    <button class="conf-btn" data-conf="85" onclick="setConfidence(85, this)" style="padding: 10px 4px; background: rgba(0,150,255,0.1); border: 1px solid rgba(0,150,255,0.3); color: #ccc; border-radius: 8px; font-size: 12px; font-weight: 700; cursor: pointer;">Conservative<br><span style="font-size: 9px; font-weight: 400; opacity: 0.7;">85%</span></button>
                </div>
            </div>

            <!-- Live risk preview -->
            <div style="background: rgba(0,0,0,0.3); border-radius: 8px; padding: 12px; margin-top: 14px;">
                <div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px;">
                    <span style="color: #888;">Risk Amount:</span>
                    <span id="liveRiskAmount" style="color: #ffd700; font-weight: 700;">R3.69</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px;">
                    <span style="color: #888;">Max Daily Loss (5%):</span>
                    <span id="liveMaxDaily" style="color: #ff6b6b; font-weight: 700;">R18.46</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px;">
                    <span style="color: #888;">Max Weekly Loss (10%):</span>
                    <span id="liveMaxWeekly" style="color: #ff6b6b; font-weight: 700;">R36.92</span>
                </div>
            </div>

            <button onclick="saveSettings()" style="width: 100%; margin-top: 14px; padding: 12px; background: linear-gradient(135deg, #00d4aa, #0096ff); color: #000; border: none; border-radius: 10px; font-size: 14px; font-weight: 700; cursor: pointer;">
                💾 Save Settings
            </button>
            <div id="saveConfirm" style="display: none; text-align: center; margin-top: 10px; color: #00d4aa; font-size: 12px; font-weight: 700;">
                ✅ Saved!
            </div>
        </div>

        <!-- v8.1 NEW: Signal History Stats + Clear -->
        <div class="setup-instructions">
            <h4>📜 Signal History</h4>
            <div style="background: rgba(0,0,0,0.3); border-radius: 8px; padding: 12px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px;">
                    <span style="color: #888;">Total Signals:</span>
                    <span id="historyTotal" style="color: #00d4ff; font-weight: 700;">0</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px;">
                    <span style="color: #888;">Wins:</span>
                    <span id="historyWins" style="color: #00d4aa; font-weight: 700;">0</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px;">
                    <span style="color: #888;">Losses:</span>
                    <span id="historyLosses" style="color: #ff6b6b; font-weight: 700;">0</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px;">
                    <span style="color: #888;">Breakeven:</span>
                    <span id="historyBE" style="color: #ffd700; font-weight: 700;">0</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding: 8px 0 4px; margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.1); font-size: 13px;">
                    <span style="color: #fff; font-weight: 700;">Win Rate:</span>
                    <span id="historyWinRate" style="color: #ffd700; font-weight: 800; font-size: 16px;">0%</span>
                </div>
            </div>
            <button onclick="clearHistory()" style="width: 100%; padding: 10px; background: rgba(255,107,107,0.1); border: 1px solid rgba(255,107,107,0.4); color: #ff6b6b; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer;">
                🗑️ Clear All History
            </button>
        </div>

        <!-- App Info (simplified) -->
        <div class="setup-instructions">
            <h4>📱 About Elite Alpha EA</h4>
            <div class="info-row"><span class="label">Version:</span><span class="value" style="color: #00d4aa;">v9.0.0</span></div>
            <div class="info-row"><span class="label">Account:</span><span class="value">Sbusiso</span></div>
            <div class="info-row"><span class="label">Broker:</span><span class="value">Exness</span></div>
            <div class="info-row"><span class="label">Account #:</span><span class="value">134644333</span></div>
            <div class="info-row"><span class="label">SMC Factors:</span><span class="value">20</span></div>
            <div class="info-row"><span class="label">Symbols:</span><span class="value">7 pairs</span></div>
            <p style="margin-top: 12px; font-size: 11px; color: #888; text-align: center;">
                Precision Trading, Zero Emotion
            </p>
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
        let livePricesCache = {}; // fresh MT5 quotes only
        let economicEventsCache = [];
        let activeNewsEventIndex = -1;

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
            loadSettings(); // v8.1 NEW: Load saved settings
            updateLivePricePreview(); // v8.9 NEW: Show live price banner
            updateScanLivePricePreview(); // v8.9 NEW: same live price on Scan tab
            // Refresh drawdown and countdown every 60 seconds
            setInterval(() => {
                loadNextSession();
                loadDrawdown();
                updateLivePricePreview(); // v8.9 NEW
                updateScanLivePricePreview(); // v8.9 NEW
            }, 60000);
            // Refresh others every 5 min
            setInterval(() => {
                loadTicker();
                loadSession();
                loadNews();
                loadHTFBias(selectedSymbol);
            }, 300000);
            // v8.1 NEW: Update risk calc when balance changes
            setInterval(() => {
                const balanceInput = document.getElementById('settingsBalanceInput');
                if (balanceInput && document.activeElement !== balanceInput) {
                    updateLiveRiskCalc();
                }
            }, 2000);
        };

        // ============ v8.9 NEW: Live price preview banner ============
        function updateLivePricePreview() {
            fetch('/api/prices')
                .then(r => r.json())
                .then(data => {
                    livePricesCache = data;
                    const info = data[selectedSymbol];
                    const priceEl = document.getElementById('livePriceValue');
                    const sourceEl = document.getElementById('livePriceSource');
                    if (!priceEl || !sourceEl) return;
                    const captured = getRecentMt5ScreenshotPrice(selectedSymbol);
                    if (info && info.source === 'mt5' && Number(info.price) > 0) {
                        priceEl.textContent = formatPriceForSymbol(selectedSymbol, info.price);
                        sourceEl.textContent = '🟢 EXACT MT5 / Exness bridge · updated ' + (info.age_seconds ?? 0) + 's ago · ' + selectedSymbol;
                    } else if (captured) {
                        priceEl.textContent = formatPriceForSymbol(selectedSymbol, captured.price);
                        const ageMin = Math.max(0, Math.round((Date.now() - captured.capturedAt) / 60000));
                        sourceEl.textContent = '📸 MT5 screenshot price · captured ' + ageMin + 'm ago · ' + selectedSymbol;
                    } else {
                        priceEl.textContent = '—';
                        sourceEl.textContent = selectedSymbol === 'ALL'
                            ? 'Select one symbol to view its exact Exness price.'
                            : '🔴 No exact Exness quote. Keep MT5 bridge connected or upload a current MT5 chart.';
                    }
                })
                .catch(() => {
                    document.getElementById('livePriceValue').textContent = '—';
                    document.getElementById('livePriceSource').textContent = '🔴 Exact Exness price unavailable';
                });
        }

        // Format only exact MT5 bridge or OCR-captured prices.
        function formatPriceForSymbol(symbol, value) {
            const n = Number(value);
            if (!Number.isFinite(n)) return '—';
            if (symbol === 'BTCUSDm') return '$' + n.toLocaleString('en-US', {maximumFractionDigits: 0});
            if (symbol === 'XAUUSDm') return '$' + n.toFixed(2);
            if (symbol === 'USDJPYm') return n.toFixed(2);
            if (symbol === 'EURUSDm' || symbol === 'GBPUSDm') return n.toFixed(5);
            return n.toFixed(2);
        }

        function saveMt5ScreenshotPrice(symbol, price) {
            try {
                const saved = JSON.parse(localStorage.getItem('eliteMt5Prices') || '{}');
                saved[symbol] = {price: Number(price), capturedAt: Date.now()};
                localStorage.setItem('eliteMt5Prices', JSON.stringify(saved));
            } catch (e) { /* private browsing/localStorage unavailable */ }
        }

        function getRecentMt5ScreenshotPrice(symbol, maxAgeMs = 3 * 60 * 1000) {
            try {
                const saved = JSON.parse(localStorage.getItem('eliteMt5Prices') || '{}');
                const item = saved[symbol];
                if (item && Number(item.price) > 0 && Date.now() - Number(item.capturedAt) <= maxAgeMs) {
                    return item;
                }
            } catch (e) { /* ignore */ }
            return null;
        }

        function setScanPriceDisplay(symbol, price, sourceText) {
            const priceEl = document.getElementById('scanLivePriceValue');
            const sourceEl = document.getElementById('scanLivePriceSource');
            const input = document.getElementById('currentPrice');
            if (priceEl) priceEl.textContent = formatPriceForSymbol(symbol, price);
            if (sourceEl) sourceEl.textContent = sourceText + ' · ' + symbol;
            if (input) input.value = Number(price);
        }

        // Detect the large teal/green current-price box on MT5 screenshots.
        // This avoids reading the older price-axis labels above it.
        async function findCurrentPriceFromChartImage(imageDataUrl) {
            return new Promise((resolve) => {
                const img = new Image();
                img.onload = async function() {
                    try {
                        const maxWidth = 1600;
                        const scale = Math.min(1, maxWidth / img.naturalWidth);
                        const canvas = document.createElement('canvas');
                        canvas.width = Math.max(1, Math.round(img.naturalWidth * scale));
                        canvas.height = Math.max(1, Math.round(img.naturalHeight * scale));
                        const ctx = canvas.getContext('2d', {willReadFrequently: true});
                        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                        const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
                        const pixels = image.data;
                        const w = canvas.width, h = canvas.height;
                        let best = null;

                        // Search horizontal background runs in the right half of the chart.
                        // The highlighted current label is a wide teal rectangle; candles
                        // and grid lines are narrow and therefore score much lower.
                        for (let y = Math.floor(h * 0.10); y < Math.floor(h * 0.85); y++) {
                            let x = Math.floor(w * 0.55);
                            while (x < w) {
                                const i = (y * w + x) * 4;
                                const r = pixels[i], g = pixels[i + 1], b = pixels[i + 2];
                                const isTeal = g > 105 && g > r * 1.25 && g >= b * 0.98 && r < 175;
                                if (!isTeal) { x++; continue; }
                                const start = x;
                                while (x < w) {
                                    const j = (y * w + x) * 4;
                                    const rr = pixels[j], gg = pixels[j + 1], bb = pixels[j + 2];
                                    if (!(gg > 105 && gg > rr * 1.25 && gg >= bb * 0.98 && rr < 175)) break;
                                    x++;
                                }
                                const length = x - start;
                                const minRun = Math.max(70, Math.floor(w * 0.055));
                                if (length >= minRun && start > w * 0.65) {
                                    const score = length * (1 + start / w);
                                    if (!best || score > best.score) best = {x: start, y, length, score};
                                }
                            }
                        }

                        if (!best) { resolve(null); return; }

                        // Include the full label and a little margin around the white digits.
                        const cropX = Math.min(w - 1, Math.floor(best.x + 2));
                        const cropY = Math.min(h - 1, Math.floor(best.y + 1));
                        const cropRight = Math.min(w, Math.floor(best.x + best.length + w * 0.025));
                        const cropBottom = Math.min(h, Math.floor(best.y + h * 0.019));
                        const crop = document.createElement('canvas');
                        crop.width = Math.max(1, cropRight - cropX);
                        crop.height = Math.max(1, cropBottom - cropY);
                        const cropCtx = crop.getContext('2d', {willReadFrequently: true});
                        cropCtx.drawImage(canvas, cropX, cropY, crop.width, crop.height, 0, 0, crop.width, crop.height);

                        // High-contrast pass: white MT5 digits become black text on
                        // white, while the teal label background becomes white.
                        const cropImage = cropCtx.getImageData(0, 0, crop.width, crop.height);
                        for (let p = 0; p < cropImage.data.length; p += 4) {
                            const rr = cropImage.data[p], gg = cropImage.data[p + 1], bb = cropImage.data[p + 2];
                            const brightText = rr > 175 && gg > 175 && bb > 175;
                            const value = brightText ? 0 : 255;
                            cropImage.data[p] = value;
                            cropImage.data[p + 1] = value;
                            cropImage.data[p + 2] = value;
                            cropImage.data[p + 3] = 255;
                        }
                        cropCtx.putImageData(cropImage, 0, 0);
                        const cropUrl = crop.toDataURL('image/png');

                        const ocr = await Tesseract.recognize(cropUrl, 'eng', {
                            logger: m => {
                                if (m.status === 'recognizing text') {
                                    const pct = Math.round(m.progress * 100);
                                    const status = document.getElementById('ocrStatus');
                                    if (status) status.innerHTML = `🔍 Reading highlighted MT5 price... ${pct}%`;
                                }
                            },
                            tessedit_pageseg_mode: 7
                        });
                        const text = ocr.data.text || '';
                        const matches = text.match(/\\b\\d{2,6}(?:[.,]\\d{1,5})?\\b/g) || [];
                        const prices = matches.map(v => parseFloat(v.replace(',', '.'))).filter(v => v > 1 && v < 100000);
                        if (prices.length) {
                            // The crop is only the highlighted current-price box, so the
                            // first valid decimal is the intended price.
                            resolve(prices.find(v => String(v).includes('.')) || prices[0]);
                        } else {
                            resolve(null);
                        }
                    } catch (e) {
                        console.warn('Current-price box detection failed:', e);
                        resolve(null);
                    }
                };
                img.onerror = () => resolve(null);
                img.src = imageDataUrl;
            });
        }

        // Scan preview uses only fresh MT5 quotes or recent screenshot OCR.
        function updateScanLivePricePreview() {
            const symbolEl = document.getElementById('symbol');
            const symbol = symbolEl ? symbolEl.value : selectedSymbol;
            const priceEl = document.getElementById('scanLivePriceValue');
            const sourceEl = document.getElementById('scanLivePriceSource');
            const input = document.getElementById('currentPrice');
            if (!priceEl || !sourceEl || !symbol) return;

            fetch('/api/prices')
                .then(r => r.json())
                .then(data => {
                    livePricesCache = data;
                    const info = data[symbol];
                    const captured = getRecentMt5ScreenshotPrice(symbol);
                    if (info && info.source === 'mt5' && Number(info.price) > 0) {
                        setScanPriceDisplay(symbol, info.price, '🟢 EXACT MT5 / Exness bridge · updated ' + (info.age_seconds ?? 0) + 's ago');
                    } else if (captured) {
                        setScanPriceDisplay(symbol, captured.price, '📸 MT5 screenshot price');
                    } else {
                        priceEl.textContent = '—';
                        sourceEl.textContent = '🔴 No exact Exness quote. Connect the MT5 bridge or upload a current MT5 chart.';
                        if (input) input.value = '';
                    }
                })
                .catch(() => {
                    priceEl.textContent = '—';
                    sourceEl.textContent = '🔴 Exact Exness price unavailable';
                    if (input) input.value = '';
                });
        }

        // ============ TAB SWITCH (FIXED from v6) ============
        function switchTab(tab, btn) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.nav-btn, .scan-nav-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tab + '-tab').classList.add('active');
            if (btn) btn.classList.add('active');
            if (tab === 'scan') updateScanLivePricePreview();
            window.scrollTo({top: 0, behavior: 'smooth'});
        }

        // ============ SYMBOL PICKER (NEW v7.0) ============
        function pickSymbol(chip, symbol) {
            document.querySelectorAll('#symbolPicker .symbol-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            selectedSymbol = symbol;
            const scanSymbolEl = document.getElementById('symbol');
            if (scanSymbolEl && symbol !== 'ALL') scanSymbolEl.value = symbol;
            loadHTFBias(symbol);
            if (symbol !== 'ALL') loadReferenceLevels(symbol);
            updateLivePricePreview(); // v8.9 NEW: refresh live price banner when symbol changes
            // v8.6: Update scan button to show which symbol will be scanned
            const scanBtnLabel = document.getElementById('scanBtnSymbol');
            if (scanBtnLabel) {
                scanBtnLabel.textContent = symbol === 'ALL' ? 'ALL' : symbol.replace('USD', '').replace('m', '');
            }
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
                        document.getElementById('countdownActive').textContent = 'Right now (SAST ' + data.current_time_johannesburg + ' / UTC ' + data.current_time_utc + ')';
                    } else {
                        document.getElementById('countdownSession').textContent = data.next_session;
                        document.getElementById('countdownSession').style.color = '#ffd700';
                        document.getElementById('countdownActive').textContent = 'Opens at ' + String(data.next_hour_utc).padStart(2, '0') + ':00 UTC';
                    }
                });
        }

        // Account trade history is not connected to this app. Do not label hidden
        // zero defaults as live 'safe' risk status; keep the panel explicitly manual.
        function loadDrawdown() {
            const message = document.getElementById('drawdownMessage');
            if (message) {
                message.textContent = 'Not synced to MT5. Daily/weekly figures are not live account risk.';
                message.style.color = '#ffd700';
            }
            const title = document.getElementById('drawdownTitle');
            if (title) title.textContent = '🛡️ Risk Tracker (manual only)';
            const daily = document.getElementById('dailyValue');
            const weekly = document.getElementById('weeklyValue');
            if (daily) daily.textContent = 'Not synced to MT5';
            if (weekly) weekly.textContent = 'Not synced to MT5';
            const dailyBar = document.getElementById('dailyBar');
            const weeklyBar = document.getElementById('weeklyBar');
            if (dailyBar) dailyBar.style.width = '0%';
            if (weeklyBar) weeklyBar.style.width = '0%';
        }

        // Helper for drawdown bar values
        const balance = 369.19;

        // ============ v8.0 NEW: REFERENCE LEVELS ============
        function loadReferenceLevels(symbol) {
            fetch('/api/reference-levels?symbol=' + encodeURIComponent(symbol))
                .then(r => r.json())
                .then(data => {
                    const panel = document.getElementById('refLevels');
                    if (panel) panel.style.display = data.available ? 'block' : 'none';
                })
                .catch(() => {
                    const panel = document.getElementById('refLevels');
                    if (panel) panel.style.display = 'none';
                });
        }

        function loadHTFBias(symbol) {
            const panel = document.getElementById('htfBanner');
            if (panel) panel.style.display = 'none';
        }

        // ============ TICKER (unchanged) ============
        function loadTicker() {
            fetch('/api/prices')
                .then(r => r.json())
                .then(data => {
                    livePricesCache = data;
                    const symbols = ['XAUUSDm', 'BTCUSDm', 'EURUSDm', 'GBPUSDm', 'USDJPYm', 'USTECm', 'US30m'];
                    let html = '';
                    symbols.forEach(symbol => {
                        const info = data[symbol] || {};
                        const exact = info.source === 'mt5' && Number(info.price) > 0;
                        const priceStr = exact ? formatPriceForSymbol(symbol, info.price) : '—';
                        const label = exact ? 'EXNESS' : 'NO MT5 QUOTE';
                        html += `<div class="ticker-item">
                            <span class="ticker-symbol">${symbol}</span>
                            <span class="ticker-price">${priceStr}</span>
                            <span style="color:${exact ? '#00d4aa' : '#ff6b6b'};font-size:10px;">${label}</span>
                        </div>`;
                    });
                    document.getElementById('tickerContent').innerHTML = html + html;
                })
                .catch(() => {
                    document.getElementById('tickerContent').innerHTML = '<div class="ticker-item"><span style="color:#ff6b6b">Exact MT5 prices unavailable</span></div>';
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

        // ============ LIVE ECONOMIC CALENDAR + CONDITIONAL EVENT SCENARIOS ============
        function escapeHtml(value) {
            return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
        }

        function loadNews() {
            fetch('/api/news')
                .then(r => r.json())
                .then(data => {
                    economicEventsCache = Array.isArray(data.events) ? data.events : [];
                    const status = document.getElementById('newsStatus');
                    const list = document.getElementById('newsList');
                    if (status) {
                        status.textContent = data.status === 'live'
                            ? 'Live calendar · updated ' + (data.updated_at || 'just now')
                            : data.status === 'stale'
                                ? '⚠️ ' + (data.message || 'Showing cached calendar data; verify before use.')
                                : '⚠️ ' + (data.message || 'Live calendar unavailable; no placeholder events shown.');
                        status.style.color = data.status === 'live' ? '#8fc7bb' : '#ffd700';
                    }
                    if (!list) return;
                    if (economicEventsCache.length === 0) {
                        list.innerHTML = `<div style="color:#aaa;font-size:12px;line-height:1.5;">${escapeHtml(data.status === 'unavailable' ? (data.message || 'Calendar unavailable.') : 'No medium/high-impact events listed in the next 7 days. This does not mean trading is risk-free.')}</div>`;
                        return;
                    }
                    list.innerHTML = economicEventsCache.map((event, index) => {
                        const impact = String(event.impact || 'MEDIUM').toUpperCase();
                        const cls = impact === 'HIGH' ? 'news-impact-high' : 'news-impact-medium';
                        const dateLabel = event.date_local || '';
                        const timeLabel = event.time_local || 'Time TBC';
                        const title = event.title || 'Economic event';
                        return `<button class="news-item" type="button" onclick="showNewsScenario(${index})" style="width:100%;text-align:left;background:transparent;color:#ddd;border:0;border-bottom:1px solid rgba(255,255,255,.06);cursor:pointer;">
                            <span><strong>${escapeHtml(dateLabel)} ${escapeHtml(timeLabel)}</strong> · ${escapeHtml(event.country || event.currency || '')} · ${escapeHtml(title)}<small style="display:block;color:#888;margin-top:2px;">Tap for conditional scenarios · consensus: ${escapeHtml(event.consensus ?? 'not published')}</small></span>
                            <span class="${cls}">${escapeHtml(impact)}</span>
                        </button>`;
                    }).join('');
                })
                .catch(() => {
                    const status = document.getElementById('newsStatus');
                    const list = document.getElementById('newsList');
                    if (status) status.textContent = '⚠️ Live calendar unavailable.';
                    if (list) list.innerHTML = '<div style="color:#aaa;font-size:12px;">No placeholder events are shown while the feed is unavailable.</div>';
                });
        }

        function showNewsScenario(index) {
            if (index < 0 || index >= economicEventsCache.length) return;
            activeNewsEventIndex = index;
            const panel = document.getElementById('newsScenarioPanel');
            const asset = document.getElementById('newsAssetSelect');
            if (panel) panel.style.display = 'block';
            if (asset && !asset.dataset.userSelected) asset.value = 'XAUUSDm';
            refreshNewsScenarioAsset();
        }

        function closeNewsScenario() {
            const panel = document.getElementById('newsScenarioPanel');
            if (panel) panel.style.display = 'none';
            activeNewsEventIndex = -1;
        }

        function refreshNewsScenarioAsset() {
            if (activeNewsEventIndex < 0 || !economicEventsCache[activeNewsEventIndex]) return;
            const asset = document.getElementById('newsAssetSelect');
            const symbol = asset ? asset.value : 'XAUUSDm';
            if (asset) asset.dataset.userSelected = 'true';
            const event = economicEventsCache[activeNewsEventIndex];
            const content = document.getElementById('newsScenarioContent');
            if (content) content.innerHTML = '<div style="color:#aaa">Preparing conditional scenarios…</div>';
            fetch('/api/news-scenario?event_id=' + encodeURIComponent(event.id) + '&symbol=' + encodeURIComponent(symbol))
                .then(r => r.json())
                .then(data => {
                    if (!content) return;
                    if (data.error) {
                        content.textContent = data.error;
                        return;
                    }
                    const scenarios = (data.scenarios || []).map(item => `<div style="margin:8px 0;padding:8px;border-radius:7px;background:rgba(255,255,255,.04);"><strong style="color:#00d4aa;">${escapeHtml(item.label)}</strong><div style="color:#ccc;margin-top:3px;">${escapeHtml(item.text)}</div></div>`).join('');
                    const metrics = `<div style="color:#aaa;margin:5px 0 8px;">Consensus: ${escapeHtml(data.consensus ?? 'not published')} · Previous: ${escapeHtml(data.prior ?? '—')} · Actual: ${escapeHtml(data.actual ?? 'not released')}</div>`;
                    const source = data.source_url ? `<div style="margin-top:7px;"><a href="${escapeHtml(data.source_url)}" target="_blank" rel="noopener" style="color:#00d4aa;">Event source / details</a></div>` : '';
                    content.innerHTML = `<div style="font-weight:700;color:#ffd700;">${escapeHtml(data.phase)} · ${escapeHtml(data.symbol)}</div><div style="margin:6px 0;color:#ddd;">${escapeHtml(data.event)}</div><div style="color:#ccc;">${escapeHtml(data.summary)}</div>${metrics}${scenarios}<div style="margin-top:8px;color:#ffcc80;font-size:11px;">⚠️ ${escapeHtml(data.caution)}</div>${source}`;
                })
                .catch(() => { if (content) content.textContent = 'Could not load the event scenario. Try again.'; });
        }

        // Every symbol requires an exact Exness price. A quote is not candle history,
        // so the app will not invent a BUY/SELL direction from it.
        function needsExactMt5Price(symbol) { return true; }

        function hasMt5BridgeQuote(symbol) {
            return !!(livePricesCache[symbol] && livePricesCache[symbol].source === 'mt5' && Number(livePricesCache[symbol].price) > 0);
        }

        function showSafeScanWait(symbol, price, source, message) {
            const resultDiv = document.getElementById('autoScanResult');
            const priceLine = Number(price) > 0
                ? `<div style="margin:8px 0;color:#00d4aa;">Verified price: ${formatPriceForSymbol(symbol, price)} · ${escapeHtml(source)}</div>`
                : '<div style="margin:8px 0;color:#ff6b6b;">Verified Exness price: unavailable</div>';
            resultDiv.innerHTML = `<div style="text-align:center;padding:18px;color:#ddd;background:rgba(0,0,0,.28);border-radius:10px;">
                <div style="font-size:30px;color:#ffd700;font-weight:800;">WAIT</div>${priceLine}
                <div style="font-size:12px;line-height:1.55;margin-top:8px;">${escapeHtml(message)}</div>
                <div style="font-size:11px;color:#ffcc80;margin-top:10px;">No fabricated confidence, entry, stop-loss or take-profit is shown.</div>
            </div>`;
        }

        function describeCandleStatus(data) {
            const frames = data && data.timeframes ? data.timeframes : {};
            const parts = Object.entries(frames).map(([tf, info]) =>
                `${tf}: ${info.bars || 0}/${info.minimum_bars || 0}${info.ready ? ' ready' : ' waiting'}`
            );
            return parts.length ? parts.join(' · ') : 'No candle status received';
        }

        function runAutoScan() {
            const resultDiv = document.getElementById('autoScanResult');
            resultDiv.style.display = 'block';
            if (selectedSymbol === 'ALL') {
                const symbols = ['XAUUSDm','BTCUSDm','EURUSDm','GBPUSDm','USDJPYm','USTECm','US30m'];
                const missing = symbols.filter(s => !hasMt5BridgeQuote(s));
                if (missing.length) {
                    showSafeScanWait('ALL', null, 'unavailable', 'Waiting for fresh exact MT5 quotes for: ' + missing.join(', ') + '.');
                    return;
                }
                showSafeScanWait('ALL', null, 'unavailable', 'All seven exact prices are live. Check individual symbol scans for the M15/H1/H4/D1 candle-feed counts. Trade signals remain paused until the candle strategy is validated.');
                return;
            }
            const screenshot = getRecentMt5ScreenshotPrice(selectedSymbol);
            const bridge = livePricesCache[selectedSymbol];
            const quote = hasMt5BridgeQuote(selectedSymbol) ? bridge : null;
            const price = quote ? quote.price : screenshot ? screenshot.price : null;
            const source = quote ? 'MT5 live bridge' : screenshot ? 'MT5 screenshot' : 'unavailable';
            if (!price) {
                showSafeScanWait(selectedSymbol, null, source, 'Connect the MT5 bridge or upload a current MT5 chart. No public proxy or estimated quote is used.');
                return;
            }
            showSafeScanWait(selectedSymbol, price, source, 'Checking fresh closed MT5 candle history…');
            fetch('/api/mt5/candles/status?symbol=' + encodeURIComponent(selectedSymbol))
                .then(r => r.json())
                .then(data => {
                    const statusLine = 'MT5 candle feed: ' + describeCandleStatus(data) + '.';
                    const message = data.ready
                        ? statusLine + ' The bars are arriving, but trade signals remain paused until the rule set is validated on historical data. No confidence, Entry, SL or TP is generated yet.'
                        : statusLine + ' The scanner needs fresh closed candles before it can test structure. Keep MT5 open and let the history feed load.';
                    showSafeScanWait(selectedSymbol, price, source, message);
                })
                .catch(() => showSafeScanWait(selectedSymbol, price, source, 'Exact price is live, but the candle-status check failed. The app will stay WAIT rather than invent a setup.'));
        }

        function renderSingleResult(data) {
            const resultDiv = document.getElementById('autoScanResult');
            if (data && data.signal_available === false) {
                showSafeScanWait(data.symbol || selectedSymbol, data.price, data.price_source || 'unavailable', data.signal_reason || 'Verified candle history is required.');
                return;
            }
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
                    <div style="margin-top: 8px; font-size: 10px; color: ${(data.price_source === 'MT5 screenshot' || data.price_source === 'MT5 live bridge') ? '#00d4aa' : '#ffd700'};">Price source: ${data.price_source || 'unknown'}</div>
                </div>
                <div style="margin-bottom: 10px; padding: 9px; background: ${data.direction === 'WAIT' ? 'rgba(255,215,0,0.08)' : 'rgba(0,212,170,0.08)'}; border: 1px solid ${data.direction === 'WAIT' ? 'rgba(255,215,0,0.25)' : 'rgba(0,212,170,0.25)'}; border-radius: 8px; color: ${data.direction === 'WAIT' ? '#ffd700' : '#00d4aa'}; font-size: 11px; text-align: center;">${data.signal_reason || (data.direction === 'WAIT' ? 'No trade: setup did not pass the scanner gate.' : 'Directional setup passed the scanner gate.')}</div>
                <div style="background: rgba(0,0,0,0.2); padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                    <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">Entry:</span><span style="color: ${data.direction === 'WAIT' ? '#666' : '#fff'}; font-weight: 700;">${data.direction === 'WAIT' ? '— (no trade)' : data.entry}</span></div>
                    <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">Stop Loss:</span><span style="color: ${data.direction === 'WAIT' ? '#666' : '#ff6b6b'}; font-weight: 700;">${data.direction === 'WAIT' ? '— (no trade)' : data.sl}</span></div>
                    <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">Take Profit:</span><span style="color: ${data.direction === 'WAIT' ? '#666' : '#00d4aa'}; font-weight: 700;">${data.direction === 'WAIT' ? '— (no trade)' : data.tp}</span></div>
                    <div style="display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px;"><span style="color: #888;">Risk:Reward:</span><span style="color: ${data.direction === 'WAIT' ? '#666' : '#00d4ff'}; font-weight: 700;">${data.direction === 'WAIT' ? '—' : data.rr}</span></div>
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
                        style="width: 100%; padding: 10px; background: ${data.direction === 'WAIT' ? 'rgba(100,100,100,0.2)' : 'linear-gradient(135deg, rgba(0, 212, 170, 0.3), rgba(0, 150, 255, 0.2))'}; border: 1px solid ${data.direction === 'WAIT' ? '#666' : '#00d4aa'}; color: ${data.direction === 'WAIT' ? '#888' : '#00d4aa'}; border-radius: 8px; font-weight: 700; cursor: ${data.direction === 'WAIT' ? 'not-allowed' : 'pointer'}; font-size: 13px; ${data.direction === 'WAIT' ? 'display:none;' : ''}">
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

            // Update Home tab stats
            const totalEl = document.getElementById('totalSignals');
            if (totalEl) totalEl.textContent = total;
            const winsEl = document.getElementById('winsCount');
            if (winsEl) winsEl.textContent = wins;
            const lossesEl = document.getElementById('lossesCount');
            if (lossesEl) lossesEl.textContent = losses;
            const wrEl = document.getElementById('realWinRate');
            if (wrEl) wrEl.textContent = winRate + '%';

            // v8.1 NEW: Update Settings tab stats (if elements exist)
            const histTotal = document.getElementById('historyTotal');
            if (histTotal) histTotal.textContent = total;
            const histWins = document.getElementById('historyWins');
            if (histWins) histWins.textContent = wins;
            const histLosses = document.getElementById('historyLosses');
            if (histLosses) histLosses.textContent = losses;
            const histBE = document.getElementById('historyBE');
            if (histBE) histBE.textContent = be;
            const histWR = document.getElementById('historyWinRate');
            if (histWR) histWR.textContent = winRate + '%';

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

        // v8.1 NEW: Clear signal history
        function clearHistory() {
            if (!confirm('Clear ALL signal history? This cannot be undone.')) return;
            signalHistory = [];
            localStorage.removeItem('eliteHistory');
            loadHistory();
            alert('✅ History cleared.');
        }

        // v8.1 NEW: Settings save/load
        function saveSettings() {
            const balance = parseFloat(document.getElementById('settingsBalanceInput').value) || 369.19;
            const risk = parseFloat(document.querySelector('.risk-btn.active').dataset.risk);
            const conf = parseFloat(document.querySelector('.conf-btn.active').dataset.conf);
            const settings = { balance, risk, conf };
            localStorage.setItem('eliteSettings', JSON.stringify(settings));
            updateLiveRiskCalc();
            const cf = document.getElementById('saveConfirm');
            cf.style.display = 'block';
            setTimeout(() => { cf.style.display = 'none'; }, 2000);
        }

        function loadSettings() {
            const saved = localStorage.getItem('eliteSettings');
            if (saved) {
                try {
                    const s = JSON.parse(saved);
                    if (s.balance) document.getElementById('settingsBalanceInput').value = s.balance;
                    if (s.risk) {
                        document.querySelectorAll('.risk-btn').forEach(b => {
                            if (parseFloat(b.dataset.risk) === s.risk) {
                                setRisk(s.risk, b);
                            }
                        });
                    }
                    if (s.conf) {
                        document.querySelectorAll('.conf-btn').forEach(b => {
                            if (parseFloat(b.dataset.conf) === s.conf) {
                                setConfidence(s.conf, b);
                            }
                        });
                    }
                } catch (e) { /* ignore */ }
            }
            updateLiveRiskCalc();
        }

        function setRisk(value, btn) {
            document.querySelectorAll('.risk-btn').forEach(b => {
                b.classList.remove('active');
                b.style.background = 'rgba(0,150,255,0.1)';
                b.style.border = '1px solid rgba(0,150,255,0.3)';
                b.style.color = '#ccc';
                b.style.boxShadow = 'none';
            });
            if (btn) {
                btn.classList.add('active');
                btn.style.background = 'rgba(0,212,170,0.2)';
                btn.style.border = '1px solid #00d4aa';
                btn.style.color = '#00d4aa';
                btn.style.boxShadow = '0 0 10px rgba(0,212,170,0.3)';
            }
            updateLiveRiskCalc();
        }

        function setConfidence(value, btn) {
            document.querySelectorAll('.conf-btn').forEach(b => {
                b.classList.remove('active');
                b.style.background = 'rgba(0,150,255,0.1)';
                b.style.border = '1px solid rgba(0,150,255,0.3)';
                b.style.color = '#ccc';
                b.style.boxShadow = 'none';
            });
            if (btn) {
                btn.classList.add('active');
                btn.style.background = 'rgba(0,212,170,0.2)';
                btn.style.border = '1px solid #00d4aa';
                btn.style.color = '#00d4aa';
                btn.style.boxShadow = '0 0 10px rgba(0,212,170,0.3)';
            }
        }

        function updateLiveRiskCalc() {
            const balance = parseFloat(document.getElementById('settingsBalanceInput').value) || 369.19;
            const riskBtn = document.querySelector('.risk-btn.active');
            const riskPct = riskBtn ? parseFloat(riskBtn.dataset.risk) : 1.0;
            const riskAmount = (balance * riskPct / 100).toFixed(2);
            const maxDaily = (balance * 0.05).toFixed(2);
            const maxWeekly = (balance * 0.10).toFixed(2);
            const ra = document.getElementById('liveRiskAmount');
            if (ra) ra.textContent = 'R' + riskAmount;
            const md = document.getElementById('liveMaxDaily');
            if (md) md.textContent = 'R' + maxDaily;
            const mw = document.getElementById('liveMaxWeekly');
            if (mw) mw.textContent = 'R' + maxWeekly;
        }

        // ============ MANUAL UPLOAD + ANALYZE (v8.3 OCR) ============
        function openGallery() {
            const input = document.getElementById('fileInput');
            // v8.4: iPhone fix - explicitly remove capture first, then click
            // User can choose: Take Photo or Choose from Library
            input.removeAttribute('capture');
            // iOS Safari needs a small delay sometimes
            setTimeout(() => {
                input.click();
            }, 100);
        }

        function openCamera() {
            const input = document.getElementById('fileInput');
            input.setAttribute('capture', 'environment');
            setTimeout(() => {
                input.click();
            }, 100);
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
                // v8.3 NEW: Trigger OCR after image loads
                runOCR(e.target.result);
            };
            reader.readAsDataURL(file);
        }

        // v8.9.1 FIX: Read the highlighted current MT5 price, not the old axis labels.
        async function runOCR(imageDataUrl) {
            const statusEl = document.getElementById("ocrStatus");
            const resultEl = document.getElementById("ocrResult");
            const selectedBeforeScan = document.getElementById("symbol").value || "BTCUSDm";
            statusEl.innerHTML = "🔍 Finding the highlighted MT5 price...";
            statusEl.style.color = "#ffd700";
            resultEl.innerHTML = "";

            // Read the symbol separately. If the symbol is not printed in the image,
            // keep the symbol the user selected instead of guessing from price size.
            let text = "";
            try {
                const result = await Tesseract.recognize(imageDataUrl, "eng", {
                    logger: m => {
                        if (m.status === "recognizing text") {
                            statusEl.innerHTML = `🔍 Reading chart... ${Math.round(m.progress * 100)}%`;
                        }
                    }
                });
                text = result.data.text || "";
                console.log("OCR text:", text);
            } catch (err) {
                console.warn("Full-chart OCR failed; trying the price box anyway:", err);
            }

            const compact = text.toUpperCase().replace(/[^A-Z0-9]/g, "");
            const symbolRules = [
                {symbol: "US30m", tokens: ["US30M", "US30", "DJI", "DOWJONES", "DOW"]},
                {symbol: "USTECm", tokens: ["USTECM", "USTEC", "USTECH100", "USTECH", "NAS100", "NASDAQ", "NQF"]},
                {symbol: "XAUUSDm", tokens: ["XAUUSDM", "XAUUSD", "GOLD"]},
                {symbol: "BTCUSDm", tokens: ["BTCUSDM", "BTCUSD", "BITCOIN"]},
                {symbol: "EURUSDm", tokens: ["EURUSDM", "EURUSD"]},
                {symbol: "GBPUSDm", tokens: ["GBPUSDM", "GBPUSD"]},
                {symbol: "USDJPYm", tokens: ["USDJPYM", "USDJPY"]}
            ];

            let detectedSymbol = null;
            for (const rule of symbolRules) {
                if (rule.tokens.some(token => compact.includes(token))) {
                    detectedSymbol = rule.symbol;
                    break;
                }
            }
            if (detectedSymbol) document.getElementById("symbol").value = detectedSymbol;
            else detectedSymbol = selectedBeforeScan;

            const screenshotPrice = await findCurrentPriceFromChartImage(imageDataUrl);
            if (screenshotPrice && Number(screenshotPrice) > 0) {
                saveMt5ScreenshotPrice(detectedSymbol, screenshotPrice);
                setScanPriceDisplay(detectedSymbol, screenshotPrice, "🟢 MT5 screenshot price");
                statusEl.innerHTML = "✅ Read MT5 current price: " + formatPriceForSymbol(detectedSymbol, screenshotPrice) + " for " + detectedSymbol + ". This price will be used.";
                statusEl.style.color = "#00d4aa";
                resultEl.innerHTML = `<div style="padding: 9px; background: rgba(0,212,170,0.08); border: 1px solid rgba(0,212,170,0.25); border-radius: 7px; color: #00d4aa; font-size: 11px; text-align: center;">📸 Exact highlighted MT5 price captured and saved for this symbol.</div>`;
            } else {
                // Do not show a proxy or estimated price when OCR fails.
                updateScanLivePricePreview();
                statusEl.innerHTML = "⚠️ I could not isolate the highlighted MT5 price. Confirm the symbol. No proxy price is available or used.";
                statusEl.style.color = "#ffd700";
                resultEl.innerHTML = `<div style="padding: 9px; background: rgba(255,215,0,0.08); border: 1px solid rgba(255,215,0,0.25); border-radius: 7px; color: #ffd700; font-size: 11px; text-align: center;">⚠️ No exact MT5 price captured. No verified Exness price was captured; wait for a fresh MT5 price.</div>`;
            }
        }

        function analyzeImage() {
            const symbol = document.getElementById('symbol').value;
            const timeframe = document.getElementById('timeframe').value;
            const screenshot = getRecentMt5ScreenshotPrice(symbol);
            const info = livePricesCache[symbol];
            const bridge = info && info.source === 'mt5' && Number(info.price) > 0 ? info : null;
            const price = bridge ? Number(bridge.price) : screenshot ? Number(screenshot.price) : null;
            const source = bridge ? 'MT5 live bridge' : screenshot ? 'MT5 screenshot' : 'unavailable';
            document.getElementById('loading').style.display = 'none';
            document.getElementById('previewSection').style.display = 'none';
            const result = document.getElementById('result');
            result.style.display = 'block';
            const priceHtml = price
                ? `<div style="color:#00d4aa;margin:10px 0;">Verified MT5 price: ${formatPriceForSymbol(symbol, price)} · ${escapeHtml(source)}</div>`
                : '<div style="color:#ff6b6b;margin:10px 0;">No exact Exness price is available. Proxy and estimated prices are disabled.</div>';
            result.innerHTML = `<div style="text-align:center;padding:18px;background:rgba(0,0,0,.25);border:1px solid rgba(255,215,0,.25);border-radius:12px;">
                <div style="font-size:12px;color:#00d4ff;">${escapeHtml(symbol)} · ${escapeHtml(timeframe)}</div>
                <div style="font-size:36px;font-weight:800;color:#ffd700;margin:8px 0;">WAIT</div>${priceHtml}
                <div style="font-size:13px;color:#ddd;line-height:1.6;">Chart upload can identify the symbol and read the highlighted price. The app checks the MT5 candle feed before any setup can be considered. Until the bars and strategy are validated, it will not invent SMC patterns or a BUY/SELL direction.</div>
                <div style="font-size:12px;color:#ffcc80;margin-top:10px;">Next step: confirm fresh closed MT5 bars and validate the scanner with historical tests before enabling trade levels.</div>
                <button class="new-scan-btn" onclick="resetForm()" style="margin-top:14px;">🔄 Scan Another Chart</button>
            </div>`;
            result.scrollIntoView({behavior:'smooth'});
        }

        // v9.0: Load exact MT5 quotes only.
        function useLivePrice() {
            const symbol = document.getElementById('symbol').value;
            fetch('/api/prices')
                .then(r => r.json())
                .then(data => {
                    livePricesCache = data;
                    const info = data[symbol];
                    const input = document.getElementById('currentPrice');
                    if (input && info && info.source === 'mt5' && Number(info.price) > 0) input.value = info.price;
                    else if (input) input.value = '';
                    updateScanLivePricePreview();
                })
                .catch(() => {
                    const input = document.getElementById('currentPrice');
                    if (input) input.value = '';
                });
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

@app.route('/api/mt5/quotes', methods=['POST'])
def api_mt5_quotes():
    """Receive read-only ticks and optional closed MT5 OHLC bars from the bridge EA."""
    global MT5_QUOTES, MT5_QUOTES_LAST_UPDATE, MT5_CANDLES
    if not MT5_BRIDGE_TOKEN:
        return jsonify({'error': 'MT5 bridge is not configured on the server'}), 503

    supplied = request.headers.get('X-Bridge-Token', '')
    if not supplied or not hmac.compare_digest(supplied, MT5_BRIDGE_TOKEN):
        return jsonify({'error': 'Unauthorized bridge token'}), 401

    raw_body = request.get_data(cache=False)
    raw_body = raw_body.rstrip(b'\x00')
    try:
        payload = json.loads(raw_body.decode('utf-8')) if raw_body else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return jsonify({'error': 'Invalid JSON quote/candle payload'}), 400
    if not isinstance(payload, dict):
        return jsonify({'error': 'JSON body must be an object'}), 400

    quotes = payload.get('quotes', [])
    series = payload.get('series', [])
    if not isinstance(quotes, list):
        return jsonify({'error': 'quotes must be a list'}), 400
    if not isinstance(series, list):
        return jsonify({'error': 'series must be a list'}), 400
    if not quotes and not series:
        return jsonify({'error': 'payload must contain quotes or candle series'}), 400

    now = time.time()
    accepted_quotes = 0
    for item in quotes:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get('symbol', ''))
        if symbol not in SYMBOL_CONFIG:
            continue
        try:
            bid = float(item.get('bid', 0) or 0)
            ask = float(item.get('ask', 0) or 0)
            price = (bid + ask) / 2.0 if bid > 0 and ask > 0 else (bid if bid > 0 else ask)
            if not all(math.isfinite(x) for x in (bid, ask, price)) or price <= 0:
                continue
        except (TypeError, ValueError):
            continue
        MT5_QUOTES[symbol] = {
            'price': round(price, 5),
            'bid': round(bid, 5),
            'ask': round(ask, 5),
            'tick_time_sec': item.get('time_sec'),
            'received_at': now,
            'server': str(payload.get('server', '')),
            'account': str(payload.get('account', '')),
        }
        accepted_quotes += 1

    accepted_series = 0
    accepted_candles = 0
    for item in series[:len(SYMBOL_CONFIG) * len(MT5_TIMEFRAMES)]:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get('symbol', ''))
        timeframe = str(item.get('timeframe', '')).upper()
        raw_candles = item.get('candles', [])
        if symbol not in SYMBOL_CONFIG or timeframe not in MT5_TIMEFRAMES or not isinstance(raw_candles, list):
            continue

        by_time = {}
        for candle in raw_candles[-MT5_CANDLE_MAX_PER_SERIES:]:
            if not isinstance(candle, dict):
                continue
            try:
                stamp = int(candle.get('time', 0))
                o = float(candle.get('open'))
                h = float(candle.get('high'))
                low = float(candle.get('low'))
                close = float(candle.get('close'))
            except (TypeError, ValueError):
                continue
            if stamp <= 0 or not all(math.isfinite(x) for x in (o, h, low, close)):
                continue
            if min(o, h, low, close) <= 0 or h < max(o, low, close) or low > min(o, h, close):
                continue
            by_time[stamp] = {'time': stamp, 'open': o, 'high': h, 'low': low, 'close': close}

        candles = [by_time[t] for t in sorted(by_time)][-MT5_CANDLE_MAX_PER_SERIES:]
        if not candles:
            continue
        MT5_CANDLES[(symbol, timeframe)] = {
            'candles': candles,
            'received_at': now,
            'server': str(payload.get('server', '')),
            'account': str(payload.get('account', '')),
        }
        accepted_series += 1
        accepted_candles += len(candles)

    if accepted_quotes:
        MT5_QUOTES_LAST_UPDATE = now
    if not accepted_quotes and not accepted_series:
        return jsonify({'error': 'No valid quote or candle data accepted'}), 422

    return jsonify({
        'status': 'ok',
        'accepted': accepted_quotes,
        'accepted_series': accepted_series,
        'accepted_candles': accepted_candles,
        'received_at': now,
    })

@app.route('/api/mt5/status')
def api_mt5_status():
    fresh = {}
    for symbol in SYMBOL_CONFIG:
        quote = get_mt5_quote(symbol)
        if quote:
            fresh[symbol] = {
                'price': quote['price'],
                'bid': quote['bid'],
                'ask': quote['ask'],
                'server': quote.get('server', ''),
                'age_seconds': round(time.time() - quote.get('received_at', time.time()), 1),
            }
    candle_status = {symbol: get_mt5_candle_status(symbol) for symbol in SYMBOL_CONFIG}
    candles_ready = all(info['ready'] for info in candle_status.values())
    return jsonify({
        'configured': bool(MT5_BRIDGE_TOKEN),
        'connected': bool(fresh),
        'quotes': fresh,
        'candles_connected': any(any(tf['available'] for tf in item['timeframes'].values()) for item in candle_status.values()),
        'candles_ready_all_symbols': candles_ready,
        'candles': candle_status,
    })

@app.route('/api/mt5/candles/status')
def api_mt5_candles_status():
    symbol = request.args.get('symbol')
    if symbol:
        if symbol not in SYMBOL_CONFIG:
            return jsonify({'error': 'Unknown symbol'}), 400
        return jsonify(get_mt5_candle_status(symbol))
    return jsonify({
        'candles': {item: get_mt5_candle_status(item) for item in SYMBOL_CONFIG},
        'required_timeframes': list(MT5_TIMEFRAMES),
        'max_age_seconds': MT5_CANDLE_MAX_AGE_SECONDS,
    })

@app.route('/api/prices')
def api_prices():
    """Return exact MT5 prices only. No external proxy or static-price fallback."""
    prices = {}
    for symbol in SYMBOL_CONFIG:
        quote = get_mt5_quote(symbol)
        if quote:
            prices[symbol] = {
                'price': quote['price'],
                'bid': quote['bid'],
                'ask': quote['ask'],
                'change': None,
                'source': 'mt5',
                'age_seconds': round(time.time() - quote.get('received_at', time.time()), 1),
                'server': quote.get('server', ''),
            }
        else:
            prices[symbol] = {
                'price': None, 'bid': None, 'ask': None, 'change': None,
                'source': 'unavailable', 'age_seconds': None, 'server': '',
            }
    return jsonify(prices)

@app.route('/api/session')
def api_session():
    return jsonify(get_session_quality())

@app.route('/api/news')
def api_news():
    """Live calendar data only; never claim an empty feed means trading is safe."""
    data = get_economic_calendar_data()
    return jsonify({
        'events': data.get('events', []),
        'status': data.get('status', 'unavailable'),
        'message': data.get('message', ''),
        'updated_at': data.get('updated_at'),
        'source': 'FinanceCalendar.com',
        'attribution_url': FINANCE_CALENDAR_ATTRIBUTION,
    })

@app.route('/api/news-scenario')
def api_news_scenario():
    event_id = request.args.get('event_id', '')
    symbol = request.args.get('symbol', 'XAUUSDm')
    if symbol not in SYMBOL_CONFIG:
        return jsonify({'error': 'Unknown symbol'}), 400
    calendar_data = get_economic_calendar_data()
    event = next((e for e in calendar_data.get('events', []) if e.get('id') == event_id), None)
    if not event:
        return jsonify({'error': 'Event is no longer in the live calendar. Refresh the event list.'}), 404
    result = build_news_scenario(event, symbol)
    result['calendar_status'] = calendar_data.get('status')
    return jsonify(result)

@app.route('/api/htf-bias')
def api_htf_bias():
    symbol = request.args.get('symbol', 'BTCUSDm')
    result = get_htf_bias(symbol)
    if result:
        return jsonify(result)
    return jsonify({'error': 'Unknown symbol'}), 400

@app.route('/api/auto-scan')
def api_auto_scan():
    """UPDATED v8.7: Accepts ?symbol= and ?price= params.
    price param: optional real price from user's MT5 (more accurate than placeholder).
    """
    symbol = request.args.get('symbol', 'BTCUSDm')
    custom_price = request.args.get('price')
    min_confidence = request.args.get('min_confidence')
    try:
        parsed_price = float(custom_price) if custom_price else None
        parsed_confidence = int(min_confidence) if min_confidence else None
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid price or confidence parameter'}), 400
    result = auto_scan_symbol(symbol, custom_price=parsed_price, min_confidence=parsed_confidence)
    if result:
        return jsonify(result)
    return jsonify({'error': 'Unknown symbol'}), 400

@app.route('/api/auto-scan-all')
def api_auto_scan_all():
    """NEW v7.0: Scan all 7 symbols at once."""
    min_confidence = request.args.get('min_confidence')
    try:
        gate = int(min_confidence) if min_confidence else None
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid confidence parameter'}), 400
    results = []
    for symbol in SYMBOL_CONFIG.keys():
        results.append(auto_scan_symbol(symbol, min_confidence=gate))
    return jsonify({'results': results})

@app.route('/api/next-session')
def api_next_session():
    """NEW v8.0: Time until next trading session opens."""
    return jsonify(get_next_session())

@app.route('/api/reference-levels')
def api_reference_levels():
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
        'version': '9.1.0',
        'features': ['read_only_mt5_bridge', 'exact_prices_only', 'conditional_news_scenarios', 'read_only_mt5_ohlc_candles',
                     'lot_size_calculator', 'signal_history', 'session_countdown',
                     'economic_calendar_live_attributed', 'manual_risk_tracker_not_mt5_synced',
                     'exact_mt5_prices_only', 'conditional_news_scenarios', 'ohlc_candle_feed_diagnostics',
                     'editable_balance', 'editable_risk_pct', 'editable_min_confidence',
                     'manual_chart_v8_2_safe'],
        'new_in_v9_1': ['mt5_closed_ohlc_candle_transport', 'candle_feed_status_per_symbol_timeframe', 'removed_manual_price_input', 'highlighted_mt5_price_ocr', 'auto_live_price_preview', 'live_price_preview_on_scan_tab', 'confidence_gate_matches_settings', 'removed_yahoo_proxy_and_static_prices', 'mt5_read_only_quote_bridge', 'm15_h1_h4_d1_ohlc_feed_pending_strategy_validation'],
        'new_in_v8_4': ['iphone_upload_two_buttons', 'camera_gallery_split',
                        'best_action_hidden_when_wait', 'best_action_color_dynamic'],
        'new_in_v8_3': ['tesseract_ocr_engine', 'auto_price_from_photo',
                        'auto_symbol_from_photo', 'camera_capture_environment',
                        'ocr_progress_indicator'],
        'new_in_v8_2': ['demo_warning_banner', 'manual_price_input',
                        'use_live_price_button', 'trend_selector_dropdown',
                        'fixed_random_entry_bug'],
        'new_in_v8_1': ['editable_account_balance', 'editable_risk_pct_buttons',
                        'editable_min_confidence_buttons', 'live_risk_preview',
                        'history_stats_in_settings', 'clear_history_button',
                        'save_settings_button'],
        'removed_in_v8_1': ['dark_mode_toggle', 'push_notifications_toggle',
                            'fake_scan_interval', 'confusing_lot_calc_label'],
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
