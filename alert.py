import yfinance as yf
import pandas as pd
import os
import asyncio
from telegram import Bot

async def check_strategy():
    # 1. 데이터 가져오기 (나스닥 100 지수 추종 QQQ)
    qqq = yf.download('QQQ', period='200d', auto_adjust=True)['Close']
    today_p = float(qqq.iloc[-1])
    ma150 = float(qqq.rolling(window=150).mean().iloc[-1])
    ma50 = float(qqq.rolling(window=50).mean().iloc[-1])
    ath = float(qqq.max())
    mdd = (today_p - ath) / ath

    # 2. 메시지 조립
    status = "📈 150일선 위 (평화)" if today_p > ma150 else "📉 150일선 아래 (축적)"
    msg = f"📜 [하베스트&스택] 전략 보고\n\n현재가: ${today_p:.2f} ({status})\nMDD: {mdd*100:.1f}%\n"

    if today_p < ma150:
        msg += "📢 오늘 적립일이면? [TQQQ]를 사세요! (Stacking)"
        if mdd <= -0.15: msg += "\n⚠️ 스위칭 신호: QQQ 일부를 QLD로 옮기세요!"
    else:
        msg += "📢 오늘 적립일이면? [QQQ]를 사세요! (Peace)"
        if today_p < ma50: msg += "\n🛡️ 주의: 50일선 이탈! 레버리지는 QQQ로 대피!"

    # 3. 텔레그램 발송 (금고에서 열쇠를 꺼내옵니다)
    token = os.environ['TELEGRAM_TOKEN']
    chat_id = os.environ['CHAT_ID']
    await Bot(token=token).send_message(chat_id=chat_id, text=msg)

if __name__ == "__main__":
    asyncio.run(check_strategy())
