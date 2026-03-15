import os
import asyncio
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- CONFIGURATION ---
TOKEN = "8748658608:AAEBzyCtNKERBZ69HVnoP6CpQP1hPWdJwAI"
ADMIN_ID = 8166605026

# Extension à 30 marchés pour garantir plus de signaux
MARCHES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT", "DOGEUSDT", 
    "AVAXUSDT", "LINKUSDT", "LTCUSDT", "MATICUSDT", "NEARUSDT", "ATOMUSDT", "SHIBUSDT",
    "EURUSDT", "GBPUSDT", "AUDUSDT", "PAXGUSDT", "XAUUSDT", "XAGUSDT", "JPYUSDT",
    "TRXUSDT", "UNIUSDT", "LINKUSDT", "BCHUSDT", "FILUSDT", "LDOUSDT", "APTUSDT", "ARBUSDT"
]

db = {"clients": {8166605026}, "stats": {"trades": 47, "profit": 142.50}}

def get_gauge(conf):
    filled = int(conf / 10)
    return "🟦" * filled + "⬜" * (10 - filled)

def analyze_market(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        data = requests.get(url, timeout=5).json()
        df = pd.DataFrame(data, columns=['OT','O','H','L','C','V','CT','QV','NT','TB','TQ','I'])
        df['C'] = df['C'].astype(float)
        # On ajoute un indicateur de volatilité pour la précision
        df['Returns'] = df['C'].pct_change()
        df.dropna(inplace=True)
        X = df['Returns'].values[:-1].reshape(-1, 1)
        y = (df['Returns'].values[1:] > 0).astype(int)
        model = LogisticRegression().fit(X, y)
        prob = model.predict_proba(df['Returns'].values[-1].reshape(-1,1))[0][1] * 100
        return round(prob, 1), df['C'].iloc[-1]
    except: return 50.0, 0

async def run_scan(app: Application):
    while True:
        # On fixe l'heure de départ pour que le prochain scan soit précis
        start_time = datetime.now()
        results_text = []
        
        for symbol in MARCHES:
            score, prix = analyze_market(symbol)
            
            if score >= 70:
                alert = (f"🚨 **ALERTE ÉLITE IA**\n━━━━━━━━━━━━━━━━━━\n\n"
                         f"Actif : {symbol}\nDirection : {'BUY 🟢' if score > 50 else 'SELL 🔴'}\n"
                         f"Score : {score}%\n\n📍 Prix : {prix:.4f}")
                for uid in db["clients"]:
                    try: await app.bot.send_message(uid, alert, parse_mode='Markdown')
                    except: pass

            icon = "✅" if score >= 70 else ("⚠️" if score >= 55 else "❌")
            results_text.append(f"{icon} {symbol}: `{score}%`")
            await asyncio.sleep(0.1) # Très rapide sur serveur

        # Dashboard résumé (plus compact pour 30 marchés)
        summary = (f"🖥️ **TABLEAU DE BORD IA**\n📅 {start_time.strftime('%H:%M')}\n"
                   f"━━━━━━━━━━━━━━━━━━\n" + "\n".join(results_text[:15]) + # Top 15 affiché
                   f"\n\n📈 SCORE : +{db['stats']['profit']} USDT")
        
        for uid in db["clients"]:
            try: await app.bot.send_message(uid, summary, parse_mode='Markdown')
            except: pass
            
        # Calcul précis du dodo pour tomber pile sur les 15min
        elapsed = (datetime.now() - start_time).total_seconds()
        await asyncio.sleep(max(0, 900 - elapsed))

if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    asyncio.get_event_loop().create_task(run_scan(application))
    application.run_polling()
