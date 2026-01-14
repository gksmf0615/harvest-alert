import yfinance as yf
import pandas as pd
import os
import asyncio
from telegram import Bot

async def check_strategy():
    # 1. 데이터 가져오기 (충분한 분석을 위해 250일치)
    tickers = ['QQQ', 'QLD', 'TQQQ', 'USDKRW=X']
    data = yf.download(tickers, period='250d', auto_adjust=True)['Close']
    
    # 최신 값 추출
    q = data['QQQ'].iloc[-1]
    qld = data['QLD'].iloc[-1]
    tq = data['TQQQ'].iloc[-1]
    fx = data['USDKRW=X'].iloc[-1]
    
    # 지표 계산
    ma150 = data['QQQ'].rolling(window=150).mean().iloc[-1]
    ma50 = data['QQQ'].rolling(window=50).mean().iloc[-1]
    ath = data['QQQ'].max()
    mdd = (q - ath) / ath
    
    # 2. 전략 판단 로직
    # (1) 기본 상태
    status = "📈 [PEACE] 150일선 위" if q > ma150 else "📉 [STACKING] 150일선 아래"
    
    # (2) 행동 지침 (Stacking & Switching)
    if q < ma150:
        action = "📢 오늘 적립일이면? [TQQQ] 매수!\n"
        if mdd <= -0.35: action += "⚠️ [SWITCH] QQQ 100% -> QLD 전환 시점!"
        elif mdd <= -0.25: action += "⚠️ [SWITCH] QQQ 50% -> QLD 전환 시점!"
        elif mdd <= -0.15: action += "⚠️ [SWITCH] QQQ 20% -> QLD 전환 시점!"
    else:
        action = "📢 오늘 적립일이면? [QQQ] 매수!\n"

    # (3) 수확 및 대피 신호 (Harvest)
    harvest_signal = ""
    if q >= ath * 1.10:
        harvest_signal = "💰 [HARVEST] 신고가 +10% 달성! 레버리지 절반 수익실현 하세요!"
    elif q < ma50 and q > ma150: # 신고가 경신 후 50일선 이탈 시 (간략화)
        harvest_signal = "🛡️ [EVACUATE] 50일선 이탈! 레버리지 전량 QQQ로 대피하세요!"

    # 3. 메시지 조립
    msg = f"📜 [하베스트&스택] 정밀 보고\n\n"
    msg += f"현 재 가: ${q:.2f} (환율: {fx:.1f}원)\n"
    msg += f"상    태: {status}\n"
    msg += f"현재 MDD: {mdd*100:.2f}%\n"
    msg += f"------------------------\n"
    msg += f"{action}\n"
    if harvest_signal:
        msg += f"------------------------\n"
        msg += f"{harvest_signal}\n"

    # 4. 텔레그램 발송
    token = os.environ.get('TELEGRAM_TOKEN', '').strip()
    chat_id = os.environ.get('CHAT_ID', '').strip()
    await Bot(token=token).send_message(chat_id=chat_id, text=msg)

if __name__ == "__main__":
    asyncio.run(check_strategy())
