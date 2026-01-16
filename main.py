import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime
import numpy as np

# === 설정값 (v6 전략) ===
QQQ_TICKER = "QQQ"
TQQQ_TICKER = "TQQQ"
FAST_MA = 50
SLOW_MA = 150
BUFFER_PCT = 0.03
RSI_LIMIT = 70

# 텔레그램 설정 (GitHub Secrets)
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def get_data_and_rsi():
    # 1. QQQ 데이터 (추세 판단용)
    qqq = yf.download(QQQ_TICKER, period="2y", interval="1d", progress=False, auto_adjust=True)
    if isinstance(qqq.columns, pd.MultiIndex):
        qqq = qqq.xs('Close', axis=1, level=0).iloc[:, 0].to_frame(name='Close')
    else:
        qqq = qqq[['Close']]

    # 이평선 계산
    qqq['SMA_50'] = qqq['Close'].rolling(window=FAST_MA).mean()
    qqq['SMA_150'] = qqq['Close'].rolling(window=SLOW_MA).mean()
    
    # 2. TQQQ 데이터 (RSI 계산용)
    tqqq = yf.download(TQQQ_TICKER, period="2y", interval="1d", progress=False, auto_adjust=True)
    if isinstance(tqqq.columns, pd.MultiIndex):
        tqqq_close = tqqq.xs('Close', axis=1, level=0).iloc[:, 0]
    else:
        tqqq_close = tqqq['Close']

    # TQQQ 주봉 RSI 계산 (Wilder's Smoothing)
    # 주봉으로 변환 (금요일 기준)
    tqqq_weekly = tqqq_close.resample('W-FRI').last().to_frame()
    delta = tqqq_weekly.iloc[:, 0].diff()
    
    # Wilder's Smoothing Logic
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    tqqq_weekly['RSI'] = 100 - (100 / (1 + rs))
    
    # 가장 최근 데이터 리턴
    last_qqq = qqq.iloc[-1]
    last_rsi = tqqq_weekly['RSI'].iloc[-1]
    
    return last_qqq, last_rsi

def determine_state(row):
    price = row['Close']
    sma_50 = row['SMA_50']
    sma_150 = row['SMA_150']
    buffer_line = sma_50 * (1 - BUFFER_PCT)
    
    state = ""
    action = ""
    
    # v6 로직 (헌법)
    # 지키고 있는 선의 개수 체크
    # 버퍼선 위인가?
    is_above_buffer = price > buffer_line
    # 150일선 위인가?
    is_above_150 = price > sma_150
    
    if is_above_buffer and is_above_150:
        state = "🟢 공격 (ATTACK)"
        action = "매수 / 홀딩 (비중 100%)"
    elif not is_above_buffer and not is_above_150:
        state = "🔴 도피 (ESCAPE)"
        action = "전량 매도 (현금 100%)"
    else:
        # 둘 중 하나만 위 (버퍼만 위 or 150일만 위)
        state = "🟡 방어 (DEFENSE)"
        action = "절반 매수/매도 (비중 50%)"
        
    return state, action, price, sma_50, sma_150, buffer_line

if __name__ == "__main__":
    try:
        # 데이터 계산
        qqq_row, tqqq_rsi = get_data_and_rsi()
        state, action, price, ma50, ma150, buffer = determine_state(qqq_row)
        
        # 날짜 및 요일 확인 (UTC 기준)
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        weekday = now.weekday() # 0:월, 4:금
        
        # 메시지 작성
        msg = f"📊 *[TQQQ v6 전략 알리미]*\n"
        msg += f"📅 날짜: {today_str}\n\n"
        
        msg += f"🚦 *현재 상태: {state}*\n"
        msg += f"📢 *행동 지침: {action}*\n"
        
        # --- RSI 수확 알람 (헌법 적용) ---
        harvest_msg = ""
        # GitHub Actions가 한국시간 토요일 아침(금요일 장 마감 후)에 돌면
        # UTC 기준으로는 금요일 밤(weekday=4)입니다.
        if weekday == 4: 
            if tqqq_rsi >= RSI_LIMIT:
                harvest_msg = f"\n💰 *[RSI 수확 신호 발생!]*\n"
                harvest_msg += f"👉 TQQQ 주봉 RSI가 *{tqqq_rsi:.1f}*입니다.\n"
                harvest_msg += f"👉 *보유량의 10%를 익절하고 SGOV를 매수하세요.*"
            else:
                harvest_msg = f"\n💤 RSI 수확 없음 (현재: {tqqq_rsi:.1f})"
        else:
            harvest_msg = f"\n💤 오늘은 금요일이 아님 (RSI: {tqqq_rsi:.1f})"
            
        msg += harvest_msg + "\n\n"
        
        msg += f"--- 상세 데이터 ---\n"
        msg += f"📈 QQQ 종가: ${price:.2f}\n"
        msg += f"🛡️ 버퍼라인(-3%): ${buffer:.2f}\n"
        msg += f"🟦 50일선: ${ma50:.2f}\n"
        msg += f"🟥 150일선: ${ma150:.2f}\n"
        
        # 경고 메시지
        if price < ma150:
            msg += "\n🚨 *주의: 150일선 아래입니다!*"
        
        print(msg)
        send_telegram_message(msg)
        
    except Exception as e:
        error_msg = f"❌ 에러 발생: {str(e)}"
        print(error_msg)
        send_telegram_message(error_msg)
