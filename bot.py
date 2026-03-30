import time
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime
from flask import Flask
from threading import Thread

# --- CONFIGURATION (Tes IDs directs) ---
TOKEN = "8748658608:AAEBzyCtNKERBZ69HVnoP6CpQP1hPWdJwAI"
CHAT_ID = "8166605026"

ACTIFS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "PEPEUSDT", "WIFUSDT", "BONKUSDT", "DOGEUSDT", "SUIUSDT",
    "TIAUSDT", "OPUSDT", "ARBUSDT", "PYTHUSDT", "FETUSDT"
]

COOLDOWN = 1800 
RUN_TIME = 7 * 24 * 60 * 60

last_signal_time = {}
daily_signals = {}
total_signals = 0
last_day = ""

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ BOT V3 OPERATIONNEL - EN ATTENTE DE SIGNAL"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Erreur Telegram: {e}")

def fetch_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=200"
    try:
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=['ts','open','high','low','close','vol','ct','qv','nt','tb','tq','i'])
        df['close'] = df['close'].astype(float)
        return df
    except:
        return None

def add_indicators(df):
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    df['macd_sig'] = df['macd'].ewm(span=9).mean()
    df['momentum'] = df['close'].pct_change(5)
    df.dropna(inplace=True)
    return df

def get_signal(df):
    if len(df) < 20: return None
    last = df.iloc[-1]
    s_buy, s_sell = 0, 0
    if last['ema50'] > last['ema200']: s_buy += 2
    else: s_sell += 2
    if last['rsi'] < 45: s_buy += 1
    elif last['rsi'] > 55: s_sell += 1
    if last['macd'] > last['macd_sig']: s_buy += 1
    else: s_sell += 1
    if last['momentum'] > 0: s_buy += 1
    else: s_sell += 1

    if s_buy >= 4: return "🟢 BUY"
    if s_sell >= 4: return "🔴 SELL"
    return None

def monitor():
    global total_signals, last_day
    # Attente pour laisser Flask démarrer
    time.sleep(10)
    send_telegram("⚡ **CONNEXION ÉTABLIE**\nLe scan des 15 marchés commence maintenant.")
    
    while True:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if today not in daily_signals: daily_signals[today] = 0
        
        signals = []
        now = time.time()

        for symbol in ACTIFS:
            df = fetch_data(symbol)
            if df is None: continue
            df = add_indicators(df)
            signal = get_signal(df)
            if signal:
                l_time = last_signal_time.get(symbol, 0)
                if now - l_time >= COOLDOWN:
                    last_signal_time[symbol] = now
                    daily_signals[today] += 1
                    total_signals += 1
                    signals.append((symbol, signal, df['close'].iloc[-1]))

        if signals:
            msg = "🔥 **SIGNAL DÉTECTÉ**\n\n"
            for s in signals:
                msg += f"💎 `{s[0]}` → *{s[1]}*\nPrix: `{s[2]}`\n\n"
            send_telegram(msg)
        
        time.sleep(900) # 15 minutes

if __name__ == "__main__":
    # Lancement du thread de scan en mode Daemon
    t = Thread(target=monitor)
    t.daemon = True
    t.start()
    
    # Lancement de Flask
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
