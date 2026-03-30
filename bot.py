import time
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from flask import Flask
from threading import Thread

# --- CONFIGURATION DIRECTE ---
TOKEN = "8748658608:AAEBzyCtNKERBZ69HVnoP6CpQP1hPWdJwAI"
CHAT_ID = "8166605026"

ACTIFS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "PEPEUSDT", "WIFUSDT", "BONKUSDT", "DOGEUSDT", "SUIUSDT",
    "TIAUSDT", "OPUSDT", "ARBUSDT", "PYTHUSDT", "FETUSDT"
]

COOLDOWN = 1800  # 30 min entre deux signaux pour le même actif
RUN_TIME = 7 * 24 * 60 * 60  # Actif pendant 7 jours

last_signal_time = {}
daily_signals = {}
total_signals = 0
last_day = ""

app = Flask('')

@app.route('/')
def home():
    return "✅ BOT V3 FINAL - OPÉRATIONNEL"

# --- FONCTION ENVOI ---
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }, timeout=10)
    except:
        pass

# --- RÉCUPÉRATION DONNÉES ---
def fetch_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=200"
    try:
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=['ts','open','high','low','close','vol','ct','qv','nt','tb','tq','i'])
        df['close'] = df['close'].astype(float)
        return df
    except:
        return None

# --- CALCUL INDICATEURS ---
def add_indicators(df):
    # EMA 50 et 200 pour la tendance
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()

    # RSI pour la force du prix
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))

    # MACD pour l'impulsion
    ema12 = df['close'].ewm(span=12).mean()
    ema26 = df['close'].ewm(span=26).mean()
    df['macd'] = ema12 - ema26
    df['macd_sig'] = df['macd'].ewm(span=9).mean()

    # Momentum (vitesse sur 5 bougies)
    df['momentum'] = df['close'].pct_change(5)
    
    df.dropna(inplace=True)
    return df

# --- SYSTÈME DE SCORING ---
def get_signal(df):
    if len(df) < 10: return None
    last = df.iloc[-1]
    s_buy, s_sell = 0, 0

    # Tendance (Poids lourd : 2 pts)
    if last['ema50'] > last['ema200']: s_buy += 2
    else: s_sell += 2

    # RSI (1 pt)
    if last['rsi'] < 45: s_buy += 1
    elif last['rsi'] > 55: s_sell += 1

    # MACD (1 pt)
    if last['macd'] > last['macd_sig']: s_buy += 1
    else: s_sell += 1

    # Momentum (1 pt)
    if last['momentum'] > 0: s_buy += 1
    else: s_sell += 1

    if s_buy >= 4: return "🟢 BUY"
    if s_sell >= 4: return "🔴 SELL"
    return None

# --- BOUCLE PRINCIPALE ---
def monitor():
    global total_signals, last_day
    time.sleep(15)
    send_telegram("🚀 **BOT V3 DÉPLOYÉ**\nScoring 4/5 actif sur 15 marchés.\n_Prêt pour une session de 7 jours._")
    
    start_time = time.time()

    while time.time() - start_time < RUN_TIME:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if today not in daily_signals: daily_signals[today] = 0

        # Bilan de la journée précédente
        if last_day != "" and today != last_day:
            send_telegram(f"📊 **BILAN {last_day}**\nOpportunités détectées : {daily_signals[last_day]}")
        
        last_day = today
        signals = []
        now = time.time()

        for symbol in ACTIFS:
            df = fetch_data(symbol)
            if df is None: continue
            
            df = add_indicators(df)
            signal = get_signal(df)
            price = df['close'].iloc[-1]

            if signal:
                l_time = last_signal_time.get(symbol, 0)
                if now - l_time >= COOLDOWN:
                    last_signal_time[symbol] = now
                    total_signals += 1
                    daily_signals[today] += 1
                    signals.append((symbol, signal, price))

        if signals:
            msg = "🔥 **SIGNAL DÉTECTÉ**\n\n"
            for s in signals:
                msg += f"💎 `{s[0]}` → *{s[1]}*\nPrix: `{s[2]}`\n\n"
            send_telegram(msg)
        else:
            # Petit signal de vie toutes les 15 min
            send_telegram(f"🛰 **Scan OK** ({today})\nAucun signal 4/5 détecté.")

        time.sleep(900) # Attente 15 minutes

if __name__ == "__main__":
    t = Thread(target=monitor)
    t.start()
    app.run(host='0.0.0.0', port=8080)
