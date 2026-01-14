import yfinance as yf
import pandas as pd
import os
import asyncio
from telegram import Bot

async def check_strategy():
    # 1. 데이터 가져오기 (충분한 분석을 위해 250일치)
    # 환율 정보를 함께 가져와서 원화 환산 가격도 참고할 수 있게 했습니다.
    tickers = ['QQQ', 'USDKRW=X']
    data = yf.download(tickers, period='250d', auto_adjust=True)['Close']
    
    today_p = data['QQQ'].iloc[-1].item()
    fx = data['USDKRW=X'].iloc[-1].item()
    
    # 지표 계산
    ma150 = data['QQQ'].rolling(window=150).mean().iloc[-1].item()
    ma50 = data['QQQ'].rolling(window=50).mean().iloc[-1].item()
    ath = data['QQQ'].max().item()
    mdd = (today_p - ath) / ath

    # 2. 메시지 조립 (상태 및 가격)
    status = "📈 150일선 위 (평화)" if today_p > ma150 else "📉 150일선 아래 (축적)"
    msg = f"📜 [하베스트&스택] 정밀 보고\n\n"
    msg += f"현재가: ${today_p:.2f} (환율: {fx:.1f}원)\n"
    msg += f"상  태: {status}\n"
    msg += f"MDD: {mdd*100:.2f}%\n"
    msg += f"------------------------\n"

    # 3. [Stacking & Switching] 행동 지침
    if today_p < ma150:
        msg += "📢 오늘 적립일이면? [TQQQ]를 사세요! (Stacking)\n"
        if mdd <= -0.35: msg += "⚠️ [SWITCH] QQQ 100% -> QLD 전환 시점!\n"
        elif mdd <= -0.25: msg += "⚠️ [SWITCH] QQQ 50% -> QLD 전환 시점!\n"
        elif mdd <= -0.15: msg += "⚠️ [SWITCH] QQQ 20% -> QLD 전환 시점!\n"
    else:
        msg += "📢 오늘 적립일이면? [QQQ]를 사세요! (Peace)\n"

    # 4. [Harvest] 수확 및 대피 신호 추가
    # 신고가 돌파 여부 확인용
    harvest_msg = ""
    if today_p >= ath * 1.10:
        harvest_msg = "💰 [HARVEST] 신고가 대비 +10% 달성!\n레버리지(QLD/TQQQ) 절반을 수익실현하여 QQQ로 옮기세요!"
    elif today_p < ma50 and today_p > ma150:
        harvest_msg = "🛡️ [EVACUATE] 50일선 이탈!\n레버리지 물량을 전량 QQQ로 안전하게 대피시키세요!"

    if harvest_msg:
        msg += f"------------------------\n"
        msg += f"{harvest_msg}\n"

    # 5. 텔레그램 발송
    token = os.environ.get('TELEGRAM_TOKEN', '').strip()
    chat_id = os.environ.get('CHAT_ID', '').strip()
    
    if not token or not chat_id:
        print("에러: 토큰이나 ID가 설정되지 않았습니다.")
        return

    await Bot(token=token).send_message(chat_id=chat_id, text=msg)

if __name__ == "__main__":
    asyncio.run(check_strategy())
