"""Deterministic MT5-candle factor calculations for Elite Alpha EA.

All checks are explicit rule conditions, not probabilities. Factors report
available=False when their input is absent or insufficient.
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SAST = ZoneInfo('Africa/Johannesburg')
LONDON = ZoneInfo('Europe/London')


def factor(available, passed=None, detail=''):
    return {'available': bool(available), 'pass': bool(passed) if available else None, 'detail': str(detail)}


def ema(values, period):
    if len(values) < period: return None
    value = sum(values[:period]) / period
    alpha = 2.0 / (period + 1.0)
    for x in values[period:]: value = alpha * x + (1.0 - alpha) * value
    return value


def atr(bars, period=14):
    if len(bars) < period + 1: return None
    tr=[]
    for i in range(1,len(bars)):
        b=bars[i]; pc=bars[i-1]['close']
        tr.append(max(b['high']-b['low'],abs(b['high']-pc),abs(b['low']-pc)))
    return sum(tr[-period:])/period


def pivots(bars, wing=2):
    hi=[]; lo=[]
    for i in range(wing,len(bars)-wing):
        if all(bars[i]['high']>bars[j]['high'] for j in range(i-wing,i)) and all(bars[i]['high']>=bars[j]['high'] for j in range(i+1,i+wing+1)):
            hi.append((i,bars[i]['high']))
        if all(bars[i]['low']<bars[j]['low'] for j in range(i-wing,i)) and all(bars[i]['low']<=bars[j]['low'] for j in range(i+1,i+wing+1)):
            lo.append((i,bars[i]['low']))
    return hi,lo


def swing_bias(bars):
    if len(bars)<20: return 'unavailable',[],[]
    hi,lo=pivots(bars[-100:])
    if len(hi)<2 or len(lo)<2: return 'neutral',hi,lo
    if hi[-1][1]>hi[-2][1] and lo[-1][1]>lo[-2][1]: return 'bullish',hi,lo
    if hi[-1][1]<hi[-2][1] and lo[-1][1]<lo[-2][1]: return 'bearish',hi,lo
    return 'neutral',hi,lo


def candle_utc(bar):
    stamp=bar.get('time_utc')
    if stamp is None: return None
    try: return datetime.fromtimestamp(int(stamp),timezone.utc)
    except (TypeError,ValueError,OSError): return None


def asian_session(m15):
    sessions={}
    for b in m15:
        dt=candle_utc(b)
        if not dt: continue
        local=dt.astimezone(SAST)
        if 0<=local.hour<7: sessions.setdefault(local.date().isoformat(),[]).append((b,local))
    if not sessions: return None
    day=max(sessions)
    return {'date':day,'bars':[x[0] for x in sessions[day]],'local':sessions[day][-1][1]}


def sweep_bos(m15):
    if len(m15)<32: return None
    found=[]
    for i in range(max(20,len(m15)-8),len(m15)-1):
        base=m15[max(0,i-20):i]; local=m15[max(0,i-5):i]
        if len(base)<10 or not local: continue
        rh=max(x['high'] for x in base); rl=min(x['low'] for x in base); b=m15[i]
        if b['low']<rl and b['close']>rl:
            level=max(x['high'] for x in local)
            for j in range(i+1,len(m15)):
                if m15[j]['close']>level:
                    found.append({'direction':'BUY','sweep':i,'confirm':j,'extreme':b['low'],'level':level,'range':rl}); break
        if b['high']>rh and b['close']<rh:
            level=min(x['low'] for x in local)
            for j in range(i+1,len(m15)):
                if m15[j]['close']<level:
                    found.append({'direction':'SELL','sweep':i,'confirm':j,'extreme':b['high'],'level':level,'range':rh}); break
    return max(found,key=lambda x:x['confirm']) if found else None


def evaluate_smc_factors(symbol, price, candles, calendar, calendar_status, now_sast, trigger_timeframe='M15'):
    m15=candles.get('M15',[]); trigger_timeframe=str(trigger_timeframe or 'M15').upper()
    if trigger_timeframe not in ('M15','H1','H4','D1'): trigger_timeframe='M15'
    trigger=candles.get(trigger_timeframe,[]); h1=candles.get('H1',[]); h4=candles.get('H4',[]); d1=candles.get('D1',[])
    f={name:factor(False,detail='Required closed-bar input unavailable') for name in [
        'Market Structure','BOS','CHoCH','Breaker Block','Mitigation Block','Liquidity Sweep',
        'Equal Highs/Lows','Order Block','Fair Value Gap','Displacement','Premium/Discount',
        'PO3','Judas Swing','OTE','Session Quality','News Clear','HTF Alignment',
        'Volume Confirmation','Asian Range Position','PDH/PDL Distance']}
    if len(trigger)<32:
        return {'factors':f,'bias':'neutral','pattern':None,'atr':None,'candidate':False,'score':0,'available':0,'reason':f'Need at least 32 closed {trigger_timeframe} bars.'}

    bias_m15,sh,sl=swing_bias(trigger)
    f['Market Structure']=factor(bias_m15!='unavailable',bias_m15 in ('bullish','bearish'),f'{trigger_timeframe} swing structure: {bias_m15}')
    h1e=ema([x['close'] for x in h1],20); h1s=ema([x['close'] for x in h1],50)
    h4e=ema([x['close'] for x in h4],20); h4s=ema([x['close'] for x in h4],50)
    d1e=ema([x['close'] for x in d1],20); d1s=ema([x['close'] for x in d1],50)
    hb='bullish' if h1e is not None and h1s is not None and h4e is not None and h4s is not None and h1e>h1s and h4e>h4s else 'bearish' if h1e is not None and h1s is not None and h4e is not None and h4s is not None and h1e<h1s and h4e<h4s else 'neutral'
    db='bullish' if d1e is not None and d1s is not None and d1e>d1s else 'bearish' if d1e is not None and d1s is not None and d1e<d1s else 'neutral'
    htf_avail=all(x is not None for x in (h1e,h1s,h4e,h4s,d1e,d1s))
    htf_pass=hb in ('bullish','bearish') and db in (hb,'neutral')
    d1_ok=htf_pass
    f['HTF Alignment']=factor(htf_avail,htf_pass,f'H1/H4={hb}; D1={db}')
    direction=hb if htf_pass else None

    pattern=sweep_bos(trigger)
    aligned=bool(pattern and direction and pattern['direction']==('BUY' if direction=='bullish' else 'SELL'))
    f['Liquidity Sweep']=factor(True,aligned,f'{pattern["direction"]} wick sweep aligned to HTF' if aligned else 'No aligned sweep of the prior 20-bar range')
    f['BOS']=factor(True,aligned,'Closed M15 bar broke local structure after sweep' if aligned else 'No aligned close beyond local structure')
    f['CHoCH']=factor(bias_m15!='unavailable',bool(aligned and bias_m15 not in (direction,'neutral')),'Counter-trend structure shift after sweep' if aligned else 'No counter-trend shift confirmed')

    disp_index=pattern['confirm'] if pattern else len(trigger)-1
    disp_bars=trigger[:disp_index+1]
    a=atr(disp_bars,14); last=trigger[disp_index]; body=abs(last['close']-last['open'])
    displacement=bool(a and a>0 and body>=.6*a)
    f['Displacement']=factor(a is not None,displacement,f'Break candle body/ATR={body/a:.2f}; required >=0.60' if a else 'ATR unavailable')
    fvg=any(trigger[i]['low']>trigger[i-2]['high'] or trigger[i]['high']<trigger[i-2]['low'] for i in range(max(2,len(trigger)-8),len(trigger)))
    f['Fair Value Gap']=factor(True,fvg,'Recent three-candle gap found' if fvg else 'No recent three-candle gap')

    # Equal highs/lows: two confirmed swing levels within 0.15 ATR.
    if a and len(sh)>=2 and len(sl)>=2:
        hs=[x[1] for x in sh[-8:]]; ls=[x[1] for x in sl[-8:]]; tol=max(.15*a,1e-8)
        equal=any(abs(hs[i]-hs[j])<=tol for i in range(len(hs)) for j in range(i+1,len(hs))) or any(abs(ls[i]-ls[j])<=tol for i in range(len(ls)) for j in range(i+1,len(ls)))
        f['Equal Highs/Lows']=factor(True,equal,'Swing levels cluster within 0.15 ATR' if equal else 'No clustered swing levels')
    else: f['Equal Highs/Lows']=factor(False,detail='Need two confirmed swing highs and lows')

    ob=None
    if pattern:
        for i in range(pattern['sweep']-1,max(-1,pattern['sweep']-21),-1):
            b=trigger[i]
            if (pattern['direction']=='BUY' and b['close']<b['open']) or (pattern['direction']=='SELL' and b['close']>b['open']): ob=b; break
    f['Order Block']=factor(pattern is not None,ob is not None,'Last opposing candle before sweep/BOS found' if ob else 'No qualifying opposing candle')
    if ob and pattern:
        post=trigger[pattern['confirm']+1:]
        retest=any(x['high']>=ob['low'] and x['low']<=ob['high'] for x in post)
        broken=(pattern['direction']=='BUY' and any(x['close']<ob['low'] for x in post)) or (pattern['direction']=='SELL' and any(x['close']>ob['high'] for x in post))
        f['Mitigation Block']=factor(True,retest,'Price revisited the order-block zone' if retest else 'No retest of the order-block zone')
        f['Breaker Block']=factor(True,broken,'Order block invalidated; breaker condition found' if broken else 'No invalidated order block')
    else:
        f['Mitigation Block']=factor(False,detail='No order block to assess')
        f['Breaker Block']=factor(False,detail='No order block to assess')

    prior=trigger[-51:-1] if len(trigger)>=51 else trigger[:-1]
    if prior and direction:
        hi=max(x['high'] for x in prior); lo=min(x['low'] for x in prior); mid=(hi+lo)/2
        f['Premium/Discount']=factor(True,(price<mid if direction=='bullish' else price>mid),f'Price vs {trigger_timeframe} dealing-range midpoint {mid:.5f}')
    else: f['Premium/Discount']=factor(False,detail='Need a directional bias and recent trigger-timeframe range')

    # OTE zone, measured on the most recent impulse swing.
    if direction and sh and sl:
        high=sh[-1][1]; low=sl[-1][1]
        retr=((high-price)/(high-low) if direction=='bullish' else (price-low)/(high-low)) if high>low else -1
        f['OTE']=factor(True,.618<=retr<=.786,f'Retracement={retr:.3f}; target band 0.618-0.786')
    else: f['OTE']=factor(False,detail='No aligned impulse swing')

    # Daily previous-day levels.
    if len(d1)>=2 and a:
        pdh=d1[-1]['high']; pdl=d1[-1]['low']; dist=min(abs(price-pdh),abs(price-pdl)); near=dist<=.5*a
        f['PDH/PDL Distance']=factor(True,near,f'Nearest previous-day level distance={dist:.5f}; threshold=0.5 ATR')
    else: f['PDH/PDL Distance']=factor(False,detail='Need D1 bars and M15 ATR')

    # Tick-volume confirmation requires bridge v1.06.
    vols=[x.get('tick_volume') for x in trigger[-21:]]
    if len(vols)==21 and all(v is not None for v in vols):
        avg=sum(float(v) for v in vols[:-1])/20; ratio=float(vols[-1])/avg if avg else 0
        f['Volume Confirmation']=factor(avg>0,ratio>=1.2,f'Latest volume / prior-20 average={ratio:.2f}x; threshold 1.20x')
    else: f['Volume Confirmation']=factor(False,detail='Install bridge v1.06 to send tick_volume')

    # Time/session factors require the broker-to-UTC offset from bridge v1.06.
    asia=asian_session(m15); time_known=bool(asia and all(b.get('time_utc') for b in m15[-10:]))
    if time_known:
        abars=asia['bars']; ah=max(b['high'] for b in abars); al=min(b['low'] for b in abars); rng=max(ah-al,1e-9)
        near_edge=price<=al+.25*rng or price>=ah-.25*rng
        f['Asian Range Position']=factor(True,near_edge,f'Price vs Asia range {al:.5f}-{ah:.5f}')
        later=[b for b in m15 if candle_utc(b) and candle_utc(b).astimezone(SAST).date().isoformat()==asia['date'] and candle_utc(b).astimezone(SAST).hour>=7]
        avg_range=sum(b['high']-b['low'] for b in abars)/max(1,len(abars))
        sweep_after=any(b['high']>ah or b['low']<al for b in later)
        expansion=any(b['high']-b['low']>1.5*avg_range for b in later)
        f['PO3']=factor(len(abars)>=8,bool(sweep_after and expansion),'Asia accumulation followed by later sweep and expansion' if sweep_after and expansion else 'No complete Asia → manipulation → expansion sequence')
        london_fake=any((b['high']>ah and b['close']<ah) or (b['low']<al and b['close']>al) for b in later if candle_utc(b).astimezone(LONDON).hour<11)
        f['Judas Swing']=factor(True,london_fake,'London false-break of Asia range' if london_fake else 'No London false-break detected')
        active=(7<=now_sast.hour<12) or (14<=now_sast.hour<18)
        f['Session Quality']=factor(True,active,'Active London/NY SAST window' if active else 'Outside defined London/NY window')
    else:
        for n in ('PO3','Judas Swing','Session Quality','Asian Range Position'):
            f[n]=factor(False,detail='Install bridge v1.06 for broker time normalization')

    # News filter uses the live calendar.
    if calendar_status in ('live','stale'):
        rel={'XAUUSDm':['US'],'USTECm':['US'],'US30m':['US'],'BTCUSDm':['US'],'EURUSDm':['US','EU'],'GBPUSDm':['US','GB'],'USDJPYm':['US','JP']}[symbol]
        nearby=[]
        now_utc=now_sast.astimezone(timezone.utc)
        for ev in calendar:
            if ev.get('impact')!='HIGH' or ev.get('country') not in rel: continue
            dt=ev.get('_dt_utc')
            if dt and abs((dt-now_utc).total_seconds())<=1800: nearby.append(ev.get('title','high-impact event'))
        f['News Clear']=factor(True,not nearby,'No related high-impact event within ±30 min' if not nearby else 'Nearby event: '+', '.join(nearby))
    else: f['News Clear']=factor(False,detail='Live calendar unavailable')

    available=sum(1 for x in f.values() if x['available']); passed=sum(1 for x in f.values() if x['available'] and x['pass'])
    return {'factors':f,'direction':direction,'pattern':pattern,'atr':a,'trigger_timeframe':trigger_timeframe,'candidate':bool(direction and d1_ok and pattern and pattern['direction']==('BUY' if direction=='bullish' else 'SELL') and f['Displacement']['pass'] and f['News Clear']['pass']), 'score':passed,'available':available}
