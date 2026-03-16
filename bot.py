import os
import asyncio
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from telegram.ext import Application

# --- CONFIGURATION ---
TOKEN = "8748658608:AAEBzyCtNKERBZ69HVnoP6CpQP1hPWdJwAI"
ADMIN_ID = 8166605026

MARCHES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FETUSDT", "SUIUSDT", "TIAUSDT",
    "OPUSDT", "ARB"
]

# Dictionnaire pour ne pas spammer la même alerte
deja_alerte = {}

def analyze_market(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
        r = requests.get(url, timeout=5).json()
        df = pd.DataFrame(r, columns=['OT','O','H','L','C','V','CT','QV','NT','TB','TQ','I'])
        prices = df['C'].astype(float).values
        returns = np.diff(prices) / prices[:-1]
        X, y = returns[:-1].reshape(-1, 1), (returns[1:] > 0).astype(int)
        model = LogisticRegression().fit(X, y)
        prob = model.predict_proba(np.array([[returns[-1]]]))[0][1] * 100
        return round(prob, 1), prices[-1]
    except: return 50.0, 0

async def run_scan(app: Application):
    while True:
        for symbol in MARCHES:
            score, prix = analyze_market(symbol)
            if prix == 0: continue
            
            is_buy = score >= 60
            final_score = score if is_buy else round(100 - score, 1)
            side = "🟢 BUY" if is_buy else "🔴 SELL"

            # --- LOGIQUE DE PRÉ-ALERTE (60% à 64.9%) ---
            if 60 <= final_score < 65:
                if deja_alerte.get(symbol) != "PRE":
                    await app.bot.send_message(ADMIN_ID, f"🟠 **PRÉ-ALERTE : {symbol}**\nForce : {final_score}%\n*Ouvre BingX et cherche l'actif !*")
                    deja_alerte[symbol] = "PRE"

            # --- LOGIQUE ÉLITE (65%+) ---
            elif final_score >= 65:
                if deja_alerte.get(symbol) != "ELITE":
                    move = prix * 0.015
                    tp = prix + move if is_buy else prix - move
                    sl = prix - (move * 0.7) if is_buy else prix + (move * 0.7)
                    
                    msg = (f"🔥 **SIGNAL ÉLITE : {side}**\n"
                           f"💎 `{symbol}` | Prix: `{prix}`\n\n"
                           f"🎯 TP: `{tp:.4f}`\n"
                           f"🛡️ SL: `{sl:.4f}`\n\n"
                           f"⚡ **CLIQUE MAINTENANT (MODE MARCHÉ)**")
                    
                    await app.bot.send_message(ADMIN_ID, msg, parse_mode='Markdown')
                    deja_alerte[symbol] = "ELITE"
            
            # Reset de l'alerte si le score redescend
            if final_score < 55:
                deja_alerte[symbol] = None

            await asyncio.sleep(0.4) # Scan rapide
        await asyncio.sleep(60) # Attend 1 min entre deux tours complets

async def main():
    app = Application.builder().token(TOKEN).build()
    await app.initialize()
    asyncio.create_task(run_scan(app))
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True: await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
                
                
