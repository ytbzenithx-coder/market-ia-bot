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
    return "✅ Bot Observateur (BTC, WIF, PYTH) - En attente de signaux..."

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        # Timeout de 10s pour éviter que le bot ne bloque si Telegram est lent
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erreur d'envoi Telegram : {e}")

def fetch_data(symbol):
    try:
        # Récupération des données 15m via l'API publique de Binance
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
        res = requests.get(url, timeout=10).json()
        df = pd.DataFrame(res, columns=['ts', 'open', 'high', 'low', 'close', 'vol', 'close_ts', 'q_vol', 'trades', 'tb_base', 'tb_quote', 'ignore'])
        df['close'] = df['close'].astype(float)
        return df
    except:
        return None

def predict_signal(df):
    # Calcul des rendements pour l'IA
    df['returns'] = df['close'].pct_change()
    df.dropna(inplace=True)
    
    # On crée les caractéristiques (X) et la cible (y)
    X = np.array([df['returns'].iloc[i-5:i].values for i in range(5, len(df))])
    y = np.where(df['returns'].iloc[5:].values > 0, 1, 0)
    
    # Entraînement rapide du modèle de Régression Logistique
    model = LogisticRegression()
    model.fit(X, y)
    
    # Prédiction sur les 5 dernières bougies
    last_features = df['returns'].iloc[-5:].values.reshape(1, -1)
    return model.predict_proba(last_features)[0][1]

def monitor_loop():
    # Message de bienvenue pour confirmer que le bot est lancé
    send_telegram("🛰 **LANCEMENT DU TEST RÉEL (SANS ARGENT)**\n"
                  "Analyse en cours : `BTC`, `WIF`, `PYTH`\n"
                  "Seuil de confiance : **65%**\n"
                  "Objectif : Calculer la moyenne de signaux/jour.")
    
    # Liste des actifs (Format Binance sans le '/')
    actifs = ["BTCUSDT", "WIFUSDT", "PYTHUSDT"]
    
    while True:
        for crypto in actifs:
            df = fetch_data(crypto)
            if df is not None:
                prob = predict_signal(df)
                price = df['close'].iloc[-1]
                
                side = ""
                # Si probabilité > 65% on achète, si < 35% on vend
                if prob >= 0.65:
                    side = "HAUSSE (BUY) 🟢"
                elif prob <= 0.35:
                    side = "BAISSE (SELL) 🔴"
                
                if side:
                    # Calcul fictif du TP (1.2%) et SL (0.8%) pour l'analyse
                    tp = price * 1.012 if "BUY" in side else price * 0.988
                    sl = price * 0.992 if "BUY" in side else price * 1.008
                    
                    msg = (f"📢 **SIGNAL DÉTECTÉ**\n"
                           f"💎 Actif : *{crypto}*\n"
                           f"🔥 Confiance IA : *{prob*100:.1f}%*\n"
                           f"🧭 Direction : *{side}*\n"
                           f"💵 Prix d'entrée : `{price}`\n"
                           f"🎯 Objectif (TP) : `{tp:.4f}`\n"
                           f"🛡 Sécurité (SL) : `{sl:.4f}`")
                    send_telegram(msg)
                    
        # On attend 15 minutes avant la prochaine analyse (bougie suivante)
        time.sleep(900)

if __name__ == "__main__":
    # Serveur Flask pour que Render ne coupe pas le service
    t = Thread(target=lambda: app.run(host='0.0.0.0', port=8080))
    t.start()
    # Lancement du bot
    monitor_loop()
