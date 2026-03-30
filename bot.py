import time
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
TOKEN = "8748658608:AAEBzyCtNKERBZ69HVnoP6CpQP1hPWdJwAI"
CHAT_ID = "8166605026"

ACTIFS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "PEPEUSDT", "WIFUSDT", "BONKUSDT", "DOGEUSDT", "SUIUSDT",
    "TIAUSDT", "OPUSDT", "ARBUSDT", "PYTHUSDT", "FETUSDT"
]

COOLDOWN = 1800 
app = Flask(__name__)

# --- TEST ET ENVOI ---
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Erreur Telegram: {e}")

# --- ANALYSE ---
def fetch_data(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=200"
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=['ts','open','high','low','close','vol','ct','qv','nt','tb','tq','i'])
        df['close'] = df['close'].astype(float)
        return df
    except: return None

def get_signal(df):
    df['ema50'] = df['close'].ewm(span=50).mean()
    df['ema200'] = df['close'].ewm(span=200).mean()
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / loss)))
    last = df.iloc[-1]
    
    # Stratégie simplifiée pour déclencher rapidement
    if last['ema50'] > last['ema200'] and last['rsi'] < 45: return "🟢 BUY"
    if last['ema50'] < last['ema200'] and last['rsi'] > 55: return "🔴 SELL"
    return None

def monitor():
    send_telegram("🚀 **BOT V3 LANCÉ ET CONNECTÉ**")
    while True:
        for symbol in ACTIFS:
            df = fetch_data(symbol)
            if df is not None:
                signal = get_signal(df)
                if signal:
                    send_telegram(f"💎 `{symbol}` → *{signal}*")
                    time.sleep(COOLDOWN)
        time.sleep(900)

@app.route('/')
def home():
    return "✅ BOT ACTIF ET SCANNING..."

if __name__ == "__main__":
    # Lancement immédiat
    Thread(target=monitor, daemon=True).start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
