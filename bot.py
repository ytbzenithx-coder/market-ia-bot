import os
import asyncio
import requests
import pandas as pd
import numpy as np
import threading
import http.server
import socketserver
from datetime import datetime
from sklearn.linear_model import LogisticRegression
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- CONFIGURATION ---
TOKEN = "8748658608:AAEBzyCtNKERBZ69HVnoP6CpQP1hPWdJwAI"
ADMIN_ID = 8166605026

# LISTE ÉLARGIE (50 MARCHÉS) - Mélange de Majors et Volatiles
MARCHES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT", "DOGEUSDT", 
    "AVAXUSDT", "LINKUSDT", "LTCUSDT", "MATICUSDT", "NEARUSDT", "ATOMUSDT", "SHIBUSDT",
    "EURUSDT", "GBPUSDT", "AUDUSDT", "PAXGUSDT", "TRXUSDT", "UNIUSDT", "BCHUSDT", 
    "FILUSDT", "LDOUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "XLMUSDT", "VETUSDT", "ICPUSDT",
    "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FETUSDT", "RNDRUSDT", "TIAUSDT", "SEIUSDT", "INJUSDT",
    "SUIUSDT", "STXUSDT", "ORDIUSDT", "GALAUSDT", "AGIXUSDT", "KASUSDT", "FLOKIUSDT", "JUPUSDT",
    "PYTHUSDT", "DYDXUSDT", "IMXUSDT", "ROSEUSDT"
]

def run_dummy_server():
    PORT = int(os.environ.get("PORT", 8080))
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args): return
    with socketserver.TCPServer(("", PORT), QuietHandler) as httpd:
        httpd.serve_forever()

def analyze_market(symbol):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return 50.0, 0
        data = response.json()
        df = pd.DataFrame(data, columns=['OT','O','H','L','C','V','CT','QV','NT','TB','TQ','I'])
        prices = df['C'].astype(float).values
        returns = np.diff(prices) / prices[:-1]
        X = returns[:-1].reshape(-1, 1)
        y = (returns[1:] > 0).astype(int)
        if len(np.unique(y)) < 2: return 50.0, prices[-1]
        model = LogisticRegression(solver='liblinear').fit(X, y)
        prob = model.predict_proba(np.array([[returns[-1]]]))[0][1] * 100
        return round(prob, 1), prices[-1]
    except: return 50.0, 0

async def run_scan(app: Application):
    while True:
        start_time = datetime.now()
        rankings = []
        
        for symbol in MARCHES:
            score, prix = analyze_market(symbol)
            if prix > 0: rankings.append({"symbol": symbol, "score": score, "price": prix})
            
            # --- ALERTE ÉLITE (65%) ---
            if score >= 65 or score <= 35:
                is_buy = score >= 65
                final_score = score if is_buy else round(100 - score, 1)
                side = "🟢 BUY (LONG)" if is_buy else "🔴 SELL (SHORT)"
                emoji = "🚀" if is_buy else "⚠️"
                
                # Calcul TP/SL simplifié pour l'alerte
                move = prix * 0.015
                tp = prix + move if is_buy else prix - move
                sl = prix - (move * 0.7) if is_buy else prix + (move * 0.7)

                msg = (f"{emoji} **SIGNAL ÉLITE : {side}**\n"
                       f"━━━━━━━━━━━━━━\n"
                       f"💎 Actif : `{symbol}`\n"
                       f"🔥 Force : **{final_score}%**\n"
                       f"💵 Entrée : `{prix:.4f}`\n\n"
                       f"🎯 **TP : `{tp:.4f}`**\n"
                       f"🛡 **SL : `{sl:.4f}`**\n"
                       f"━━━━━━━━━━━━━━")
                try: await app.bot.send_message(ADMIN_ID, msg, parse_mode='Markdown')
                except: pass
            
            # Scan plus rapide (0.4s) pour couvrir les 50 marchés sans timeout
            await asyncio.sleep(0.4)

        # Rapport de performance
        rankings.sort(key=lambda x: x["score"], reverse=True)
        report = f"🛰 **RADAR IA (50 MARCHÉS)**\n"
        report += f"Top 1 : {rankings[0]['symbol']} ({rankings[0]['score']}%)\n"
        report += f"Top 2 : {rankings[1]['symbol']} ({rankings[1]['score']}%)\n"
        report += f"Top 3 : {rankings[2]['symbol']} ({rankings[2]['score']}%)"
        try: await app.bot.send_message(ADMIN_ID, report)
        except: pass
        
        await asyncio.sleep(max(0, 900 - (datetime.now() - start_time).total_seconds()))

async def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    # Utilisation de drop_pending_updates pour éviter l'erreur de conflit au démarrage
    await app.initialize()
    asyncio.create_task(run_scan(app))
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    while True: await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
