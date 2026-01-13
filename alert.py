import yfinance as yf
import pandas as pd
import os
import asyncio
from telegram import Bot

async def check_strategy():
    # 1. 데이터 가져오기 (경고 방지용 .item() 추가)
    qqq_data = yf.download('QQQ', period='250d', auto_adjust=True)['Close']
    
    today_p = qqq_data.iloc[-1].item()
    ma150 = qqq_data.rolling(window=150).mean().iloc[-1].item()
    ma50 = qqq_data.rolling(window=50).mean().iloc[-1].item()
    ath = qqq_data.max().item()
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

    # 3. 텔레그램 발송
    token = os.environ.get('TELEGRAM_TOKEN', '').strip()
    chat_id = os.environ.get('CHAT_ID', '').strip()
    
    if not token or not chat_id:
        print("에러: 토큰이나 ID가 설정되지 않았습니다.")
        return

    await Bot(token=token).send_message(chat_id=chat_id, text=msg)

if __name__ == "__main__":
    asyncio.run(check_strategy())
