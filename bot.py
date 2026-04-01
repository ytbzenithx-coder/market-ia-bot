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
URL_APP = "https://market-ia-bot-1.onrender.com" # Ton URL exacte

ACTIFS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "PEPEUSDT", "FETUSDT", "NEARUSDT", "AVAXUSDT"]

app = Flask('')

@app.route('/')
def home():
    return f"✅ BOT ACTIF - DERNIER CHECK: {datetime.now().strftime('%H:%M:%S')}"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: print("❌ Erreur envoi Telegram")

# --- FONCTION ANTI-SOMMEIL (SELF-PING) ---
def self_ping():
    print("🚀 Démarrage du système Anti-Sommeil...")
    while True:
        try:
            requests.get(URL_APP, timeout=10)
            print(f"💓 Ping réussi à {datetime.now().strftime('%H:%M')}")
        except Exception as e:
            print(f"⚠️ Ping échoué: {e}")
        time.sleep(600) # Toutes les 10 minutes

def fetch_data(symbol):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
    try:
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=['ts','open','high','low','close','vol','ct','qv','nt','tb','tq','i'])
        df['close'] = df['close'].astype(float)
        return df
    except: return None

def monitor():
    send_telegram("🛰 **SYSTÈME RELANCÉ (V-ULTRA)**\n_Auto-réveil activé._")
    while True:
        print(f"🔍 Scan des marchés lancé à {datetime.now().strftime('%H:%M')}")
        for symbol in ACTIFS:
            df = fetch_data(symbol)
            if df is not None:
                # Logique simplifiée pour tester la réactivité
                df['ema'] = df['close'].ewm(span=50).mean()
                last = df.iloc[-1]
                prev = df.iloc[-2]
                if prev['close'] < prev['ema'] and last['close'] > last['ema']:
                    send_telegram(f"💹 **SIGNAL : {symbol}** (LONG)")
        
        time.sleep(600) # Scan toutes les 10 minutes

if __name__ == "__main__":
    # Lancement des 3 moteurs
    Thread(target=self_ping, daemon=True).start()
    Thread(target=monitor, daemon=True).start()
    
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Serveur démarré sur le port {port}")
    app.run(host='0.0.0.0', port=port)
