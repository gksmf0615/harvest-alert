import yfinance as yf
import pandas as pd
import os
import asyncio
from telegram import Bot

async def check_strategy():
    # 1. 데이터 가져오기 (각각 따로 가져오는 것이 가장 안전합니다)
    qqq_ticker = yf.Ticker("QQQ")
    data = qqq_ticker.history(period="250d")
    
    # 환율 데이터
    fx_data = yf.Ticker("USDKRW=X").history(period="5d")
    
    # 데이터 추출 (NaN 방지를 위해 마지막 유효값 사용)
    today_p = data['Close'].iloc[-1]
    fx = fx_data['Close'].iloc[-1]
    
    # 지표 계산
    ma150 = data['Close'].rolling(window=150).mean().iloc[-1]
    ma50 = data['Close'].rolling(window=50).mean().iloc[-1]
    ath = data['Close'].max()
    mdd = (today_p - ath) / ath

    # 2. 메시지 조립
    status = "📈 150일선 위 (평화)" if today_p > ma150 else "📉 150일선 아래 (축적)"
    msg = f"📜 [하베스트&스택] 정밀 보고\n\n"
    msg += f"현재가: ${today_p:.2f} (환율: {fx:.1f}원)\n"
    msg += f"상  태: {status}\n"
    msg += f"MDD: {mdd*100:.2f}%\n"
    msg += f"------------------------\n"

    # 3. [Stacking & Switching] 지침
    if today_p < ma150:
        msg += "📢 오늘 적립일이면? [TQQQ]를 사세요!\n"
        if mdd <= -0.35: msg += "⚠️ [SWITCH] QQQ 100% -> QLD 전환!\n"
        elif mdd <= -0.25: msg += "⚠️ [SWITCH] QQQ 50% -> QLD 전환!\n"
        elif mdd <= -0.15: msg += "⚠️ [SWITCH] QQQ 20% -> QLD 전환!\n"
    else:
        msg += "📢 오늘 적립일이면? [QQQ]를 사세요!\n"

    # 4. [Harvest] 수확 및 대피
    harvest_msg = ""
    if today_p >= ath * 1.10:
        harvest_msg = "💰 [HARVEST] 신고가 대비 +10% 달성!\n레버리지 절반 수익실현 후 QQQ로!"
    elif today_p < ma50 and today_p > ma150:
        harvest_msg = "🛡️ [EVACUATE] 50일선 이탈!\n레버리지 전량 QQQ로 대피하세요!"

    if harvest_msg:
        msg += f"------------------------\n"
        msg += f"{harvest_msg}\n"

    # 5. 텔레그램 발송
    token = os.environ.get('TELEGRAM_TOKEN', '').strip()
    chat_id = os.environ.get('CHAT_ID', '').strip()
    
    if not token or not chat_id: return

    await Bot(token=token).send_message(chat_id=chat_id, text=msg)

if __name__ == "__main__":
    asyncio.run(check_strategy())
