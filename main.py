import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

# === 설정값 (v6 전략) ===
TICKER = "QQQ"
FAST_MA = 50
SLOW_MA = 150
BUFFER_PCT = 0.03
RSI_PERIOD = 14
RSI_LIMIT = 75

# 텔레그램 설정 (GitHub Secrets에서 가져옴)
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def calculate_indicators():
    # 데이터 다운로드 (최근 300일)
    df = yf.download(TICKER, period="2y", interval="1d", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df = df.xs('Close', axis=1, level=0).iloc[:, 0].to_frame(name='Close')
    else:
        df = df[['Close']]

    # 이평선 계산
    df['SMA_50'] = df['Close'].rolling(window=FAST_MA).mean()
    df['SMA_150'] = df['Close'].rolling(window=SLOW_MA).mean()
    
    # RSI 계산 (TQQQ용 - 여기선 QQQ로 대략 계산하거나 TQQQ 데이터 별도 호출 가능)
    # 편의상 QQQ로 상태 판단만 먼저 구현
    
    return df.iloc[-1] # 가장 최근 데이터

def determine_state(row):
    price = row['Close']
    sma_50 = row['SMA_50']
    sma_150 = row['SMA_150']
    buffer_line = sma_50 * (1 - BUFFER_PCT)
    
    state = ""
    action = ""
    
    # v6 로직
    if price > buffer_line:
        if price > sma_150:
            state = "🟢 공격 (ATTACK)"
            action = "매수 / 홀딩 (TQQQ 100%)"
        else:
            state = "🟡 방어 (DEFENSE - 역배열 반등)"
            action = "절반 매수 (TQQQ 50%)"
    elif price > sma_150:
        state = "🟡 방어 (DEFENSE - 버퍼 붕괴)"
        action = "절반 확보 (현금 50%)"
    else:
        state = "🔴 도피 (ESCAPE)"
        action = "전량 매도 (현금 100%)"
        
    return state, action, price, sma_50, sma_150, buffer_line

if __name__ == "__main__":
    try:
        data = calculate_indicators()
        state, action, price, ma50, ma150, buffer = determine_state(data)
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        msg = f"📊 *[TQQQ v6 전략 알리미]*\n"
        msg += f"📅 날짜: {today}\n\n"
        msg += f"🚦 *현재 상태: {state}*\n"
        msg += f"📢 *행동 지침: {action}*\n\n"
        msg += f"--- 상세 데이터 ---\n"
        msg += f"📈 QQQ 종가: ${price:.2f}\n"
        msg += f"🛡️ 버퍼라인(-3%): ${buffer:.2f}\n"
        msg += f"🟦 50일선: ${ma50:.2f}\n"
        msg += f"🟥 150일선: ${ma150:.2f}\n"
        
        if price < ma150:
            msg += "\n🚨 *경고: 150일선 아래입니다!*"
        
        print(msg)
        send_telegram_message(msg)
        
    except Exception as e:
        send_telegram_message(f"❌ 에러 발생: {str(e)}")
