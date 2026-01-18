import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime
import numpy as np

# ==========================================
# ⚙️ [소장님의 투자 헌법] 설정값
# ==========================================
QQQ_TICKER = "QQQ"
TQQQ_TICKER = "TQQQ"
FAST_MA = 50
SLOW_MA = 150
BUFFER_PCT = 0.03

# 다이내믹 수확 기준 (금요일 종가)
RSI_LEVEL_1 = 75  # 주의: 10% 매도
RSI_LEVEL_2 = 80  # 과열: 20% 매도
RSI_LEVEL_3 = 85  # 광기: 30% 매도

# 텔레그램 설정
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
        requests.post(url, json=payload)
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

def get_market_data():
    # 1. QQQ 데이터 (추세 판단용 - 일봉)
    qqq = yf.download(QQQ_TICKER, period="2y", interval="1d", progress=False, auto_adjust=True)
    if isinstance(qqq.columns, pd.MultiIndex):
        qqq_close = qqq.xs('Close', axis=1, level=0).iloc[:, 0]
    else:
        qqq_close = qqq['Close']

    sma_50 = qqq_close.rolling(window=FAST_MA).mean().iloc[-1]
    sma_150 = qqq_close.rolling(window=SLOW_MA).mean().iloc[-1]
    current_qqq = qqq_close.iloc[-1]

    # 2. TQQQ 데이터 (RSI 및 MDD 계산용)
    tqqq = yf.download(TQQQ_TICKER, period="2y", interval="1d", progress=False, auto_adjust=True)
    if isinstance(tqqq.columns, pd.MultiIndex):
        tqqq_close = tqqq.xs('Close', axis=1, level=0).iloc[:, 0]
    else:
        tqqq_close = tqqq['Close']

    # RSI (주봉)
    tqqq_weekly = tqqq_close.resample('W-FRI').last().to_frame()
    delta = tqqq_weekly.iloc[:, 0].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    tqqq_weekly['RSI'] = 100 - (100 / (1 + rs))
    current_rsi = tqqq_weekly['RSI'].iloc[-1]

    # MDD (고점 대비 하락률 - 정보 제공용)
    # 최근 1년(252일) 최고점 대비 현재가 확인
    rolling_max = tqqq_close.rolling(window=252, min_periods=1).max().iloc[-1]
    current_tqqq = tqqq_close.iloc[-1]
    current_mdd = (current_tqqq / rolling_max) - 1
    
    return current_qqq, sma_50, sma_150, current_rsi, current_mdd

def determine_strategy(price, ma50, ma150, rsi, mdd):
    buffer_line = ma50 * (1 - BUFFER_PCT)
    now = datetime.now()
    weekday = now.weekday() # 4: Friday
    month = now.month
    day = now.day
    
    # 1. v6 상태 판단
    is_above_buffer = price > buffer_line
    is_above_150 = price > ma150
    
    state = ""
    action = ""
    state_icon = ""

    if is_above_buffer and is_above_150:
        state = "ATTACK (공격)"
        state_icon = "🟢"
        action = "전량 보유 / 적립금 100% 투입"
    elif not is_above_buffer and not is_above_150:
        state = "ESCAPE (도피)"
        state_icon = "🔴"
        action = "전량 매도 -> 현금(SGOV) 대피"
    else:
        state = "DEFENSE (방어)"
        state_icon = "🟡"
        action = "보유량 50% 유지 (절반 매도/매수)"

    # 2. 다이내믹 수확 판단 (금요일만)
    harvest_msg = ""
    if weekday == 4:
        if rsi >= RSI_LEVEL_3:
            harvest_msg = f"\n🔥 *[광기 경보! RSI {rsi:.1f}]*\n👉 *30% 익절* 후 현금 확보하세요."
        elif rsi >= RSI_LEVEL_2:
            harvest_msg = f"\n🔥 *[과열 경보! RSI {rsi:.1f}]*\n👉 *20% 익절* 후 현금 확보하세요."
        elif rsi >= RSI_LEVEL_1:
            harvest_msg = f"\n💰 *[수확 신호! RSI {rsi:.1f}]*\n👉 *10% 익절*하여 리스크 관리하세요."
        else:
            harvest_msg = f"\n💤 수확 없음 (RSI {rsi:.1f})"
    else:
        harvest_msg = f"\n💤 평일 모드 (RSI {rsi:.1f})"

    # 3. MDD 정보 (소장님 판단용)
    mdd_msg = f"\n📉 TQQQ 고점대비: *{mdd*100:.1f}%*"
    if mdd < -0.20:
        mdd_msg += " (⚡세일 중)"
    if mdd < -0.40:
        mdd_msg += " (💎대바겐세일)"

    # 4. 연말 세금 공제 알림
    tax_msg = ""
    if month == 12 and day >= 15:
        tax_msg = "\n\n🎅 *[연말정산 꿀팁]*\n"
        tax_msg += "수익 250만원 미만이면 *'팔고 즉시 재매수'* 하세요.\n"

    # 메시지 조합
    msg = f"📊 *[TQQQ 졸업 전략 봇]*\n"
    msg += f"📅 {now.strftime('%Y-%m-%d')}\n\n"
    msg += f"{state_icon} *상태: {state}*\n"
    msg += f"📢 *지침: {action}*\n"
    msg += harvest_msg
    msg += mdd_msg 
    msg += tax_msg
    msg += "\n\n"
    msg += f"--- 상세 지표 ---\n"
    msg += f"📈 QQQ 종가: ${price:.2f}\n"
    msg += f"🛡️ 버퍼라인: ${buffer_line:.2f}\n"
    msg += f"🟥 150일선: ${ma150:.2f}\n"
    
    if price < ma150:
        msg += "\n🚨 *150일선 붕괴 주의*"

    return msg

if __name__ == "__main__":
    try:
        current_qqq, sma50, sma150, current_rsi, current_mdd = get_market_data()
        final_msg = determine_strategy(current_qqq, sma50, sma150, current_rsi, current_mdd)
        print(final_msg)
        send_telegram_message(final_msg)
        
    except Exception as e:
        error_msg = f"❌ 봇 실행 중 에러 발생: {str(e)}"
        print(error_msg)
        send_telegram_message(error_msg)
