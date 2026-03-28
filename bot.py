import time
import pandas as pd
import numpy as np
import requests
from flask import Flask
from threading import Thread
from sklearn.linear_model import LogisticRegression

# ==========================================
# CONFIGURATION DIRECTE (Tes identifiants)
# ==========================================
TELEGRAM_TOKEN = "8748658608:AAEBzyCtNKERBZ69HVnoP6CpQP1hPWdJwAI"
TELEGRAM_CHAT_ID = "8166605026"
# ==========================================

app = Flask('')

@app.route('/')
def home():
    return "✅ BOT EN TEST DE CONNEXION - Vérifie ton Telegram !"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"Statut Telegram: {r.status_code}")
    except Exception as e:
        print(f"Erreur d'envoi : {e}")

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
    model = LogisticRegression()
    model.fit(X, y)
    last_features = df['returns'].iloc[-5:].values.reshape(1, -1)
    return model.predict_proba(last_features)[0][1]

def monitor_loop():
    # TEST DE CONNEXION IMMEDIAT
    print("Tentative d'envoi du message de bienvenue...")
    send_telegram("🚀 **TEST DE CONNEXION RÉUSSI !**\n\nSi tu lis ce message, c'est que le bot est bien relié à ton compte.\n\nL'analyse intensive (1 min) commence sur BTC, WIF et PYTH.")
    
    actifs = ["BTCUSDT", "WIFUSDT", "PYTHUSDT"]
    
    while True:
        for crypto in actifs:
            df = fetch_data(crypto)
            if df is not None:
                prob = predict_signal(df)
                price = df['close'].iloc[-1]
                
                # SEUIL DE TEST BAS (10%) POUR VOIR SI CA VIBRE
                if prob >= 0.10 or prob <= 0.90:
                    msg = (f"📢 **SIGNAL DE TEST**\n"
                           f"💎 Actif : *{crypto}*\n"
                           f"🔥 Confiance : {prob*100:.1f}%\n"
                           f"💵 Prix : `{price}`")
                    send_telegram(msg)
                    
        # On attend seulement 60 secondes pour le test
        time.sleep(60)

if __name__ == "__main__":
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.start()
    monitor_loop()
