import time
import pandas as pd
import numpy as np
import requests
from flask import Flask
from threading import Thread
from sklearn.linear_model import LogisticRegression

# --- CONFIGURATION ---
TOKEN = "8748658608:AAEBzyCtNKERBZ69HVnoP6CpQP1hPWdJwAI"
CHAT_ID = "8166605026"

# Les 15 meilleurs actifs pour ce bot
ACTIFS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "PEPEUSDT", "WIFUSDT", "BONKUSDT", "DOGEUSDT", "SUIUSDT",
    "TIAUSDT", "OPUSDT", "ARBUSDT", "PYTHUSDT", "FETUSDT"
]

app = Flask('')

@app.route('/')
def home():
    return "✅ BOT 15 ACTIFS EN LIGNE - PULSATION ACTIVE"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=15)
    except:
        pass

def fetch_data(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
        res = requests.get(url, timeout=10).json()
        df = pd.DataFrame(res, columns=['ts', 'open', 'high', 'low', 'close', 'vol', 'close_ts', 'q_vol', 'trades', 'tb_base', 'tb_quote', 'ignore'])
        df['close'] = df['close'].astype(float)
        return df
    except:
        return None

def predict_signal(df):
    df['returns'] = df['close'].pct_change()
    df.dropna(inplace=True)
    X = np.array([df['returns'].iloc[i-5:i].values for i in range(5, len(df))])
    y = np.where(df['returns'].iloc[5:].values > 0, 1, 0)
    model = LogisticRegression().fit(X, y)
    last_features = df['returns'].iloc[-5:].values.reshape(1, -1)
    return model.predict_proba(last_features)[0][1]

def monitor_loop():
    time.sleep(15)
    send_telegram("🚀 **DÉMARRAGE DU SCANNER (15 ACTIFS)**\nSurveillance active : BTC, SOL, PEPE, WIF...\nIntervalle : 15 min\n_Rapport de vie activé._")
    
    while True:
        signals_found = 0
        status_msg = "🛰 **RAPPORT DE VIE (15 MARCHÉS)**\n"
        
        for crypto in ACTIFS:
            df = fetch_data(crypto)
            if df is not None:
                prob = predict_signal(df)
                price = df['close'].iloc[-1]
                
                # Signal d'achat ou vente si confiance > 65%
                if prob >= 0.65 or prob <= 0.35:
                    type_signal = "🟢 BUY" if prob >= 0.65 else "🔴 SELL"
                    confiance = prob if prob >= 0.65 else (1 - prob)
                    
                    signal_alert = (f"🔥 **ALERTE SIGNAL**\n"
                                   f"💎 Actif : `{crypto}`\n"
                                   f"📈 Direction : *{type_signal}*\n"
                                   f"⚡ Confiance : {confiance*100:.1f}%\n"
                                   f"💵 Prix : `{price}`")
                    send_telegram(signal_alert)
                    signals_found += 1
                
                # On ajoute les 5 premiers actifs au rapport pour pas que le message soit trop long
                if crypto in ACTIFS[:5]:
                    status_msg += f"• {crypto} : `{price}`\n"
        
        if signals_found == 0:
            send_telegram(status_msg + "\n_Aucun signal fort. Je continue de surveiller..._")
            
        time.sleep(900) # Attente de 15 minutes

if __name__ == "__main__":
    t = Thread(target=monitor_loop)
    t.start()
    app.run(host='0.0.0.0', port=8080)
