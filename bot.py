import time
import pandas as pd
import requests
import os
from flask import Flask
from threading import Thread
from datetime import datetime

# --- CONFIG ---
TOKEN = "8748658608:AAEBzyCtNKERBZ69HVnoP6CpQP1hPWdJwAI"
CHAT_ID = "8166605026"
MISE_DE_BASE = 7 

ACTIFS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "DOGEUSDT", "SUIUSDT", "TIAUSDT", "OPUSDT", "ARBUSDT",
    "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FETUSDT", "NEARUSDT",
    "RNDRUSDT", "LINKUSDT", "AVAXUSDT", "INJUSDT", "STXUSDT"
]

app = Flask('')

@app.route('/')
def home(): return "⚡ SYSTEME OPERATIONNEL - SCAN 10m / VIE 5m"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def fetch_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
    try:
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=['ts','open','high','low','close','vol','ct','qv','nt','tb','tq','i'])
        df['close'] = df['close'].astype(float)
        return df
    except: return None

def calculate_adx(df):
    plus_dm = df['high'].diff(); minus_dm = df['low'].diff()
    plus_dm[plus_dm < 0] = 0; minus_dm[minus_dm > 0] = 0
    tr = pd.concat([df['high']-df['low'], abs(df['high']-df['close'].shift()), abs(df['low']-df['close'].shift())], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()
    plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
    minus_di = 100 * (abs(minus_dm).rolling(14).mean() / atr)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    return dx.rolling(14).mean()

# --- FONCTION SIGNE DE VIE (Toutes les 5 minutes) ---
def heartbeat():
    while True:
        now = datetime.now().strftime("%H:%M")
        # Un petit message discret pour dire que tout va bien
        send_telegram(f"💓 **SIGNE DE VIE** [{now}]\n_Analyse en cours, système stable._")
        time.sleep(300) # 5 minutes

def monitor():
    send_telegram("🛰 **CHARGEMENT DU SYSTÈME ÉLITE...**\n_Scan : 10 min | Heartbeat : 5 min_")
    last_signals = {}

    while True:
        for symbol in ACTIFS:
            df = fetch_data(symbol)
            if df is None or len(df) < 60: continue
            
            df['ema50'] = df['close'].ewm(span=50).mean()
            df['adx'] = calculate_adx(df)
            
            last = df.iloc[-1]
            prev = df.iloc[-2]
            price = last['close']
            adx_val = last['adx']
            now_ts = time.time()
            
            if symbol in last_signals and now_ts - last_signals[symbol] < 1800: continue

            if adx_val > 22:
                multiplicateur_profit = (adx_val / 1500) + 0.01 
                tp_percent = round(multiplicateur_profit * 100, 2)
                
                signal_type = None
                if prev['close'] < prev['ema50'] and price > last['ema50']:
                    signal_type = "🟢 ACHAT (LONG)"
                    tp, sl = round(price * (1 + multiplicateur_profit), 5), round(price * 0.993, 5)
                
                elif prev['close'] > prev['ema50'] and price < last['ema50']:
                    signal_type = "🔴 VENTE (SHORT)"
                    tp, sl = round(price * (1 - multiplicateur_profit), 5), round(price * 1.007, 5)

                if signal_type:
                    gain_simu = round(MISE_DE_BASE * multiplicateur_profit * 10, 2)
                    msg = (
                        f"⚠️ **SIGNAL ÉLITE (Cote : {tp_percent}%)**\n"
                        f"`━━━━━━━━━━━━━━━━━━`\n"
                        f"💎 **Actif :** `{symbol}`\n"
                        f"📊 **Puissance :** `{round(adx_val, 1)}` (ADX)\n"
                        f"`━━━━━━━━━━━━━━━━━━`\n"
                        f"💵 **Entrée :** `{price}`\n"
                        f"🎯 **TP Adapté :** `{tp}`\n"
                        f"🛡️ **SL Fixe :** `{sl}`\n"
                        f"`━━━━━━━━━━━━━━━━━━`\n"
                        f"💰 **PROFIT ESTIMÉ :** `+{gain_simu} USDT`"
                    )
                    send_telegram(msg)
                    last_signals[symbol] = now_ts

        time.sleep(600) # Scan toutes les 10 minutes

if __name__ == "__main__":
    # On lance le Signe de Vie dans un thread séparé
    Thread(target=heartbeat, daemon=True).start()
    # On lance le Monitoring
    Thread(target=monitor, daemon=True).start()
    
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 8080))

