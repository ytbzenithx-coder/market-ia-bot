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

MARCHES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT", "DOGEUSDT", 
    "AVAXUSDT", "LINKUSDT", "LTCUSDT", "MATICUSDT", "NEARUSDT", "ATOMUSDT", "SHIBUSDT",
    "EURUSDT", "GBPUSDT", "AUDUSDT", "PAXGUSDT", "TRXUSDT", "UNIUSDT", "BCHUSDT", 
    "FILUSDT", "LDOUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "XLMUSDT", "VETUSDT", "ICPUSDT"
]

# --- SERVEUR DE MAINTIEN ---
def run_dummy_server():
    PORT = int(os.environ.get("PORT", 8080))
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args): return
    with socketserver.TCPServer(("", PORT), QuietHandler) as httpd:
        httpd.serve_forever()

# --- ANALYSE IA ---
def analyze_market(symbol):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
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

# --- CYCLE DE SCAN OPTIMISÉ ---
async def run_scan(app: Application):
    while True:
        start_time = datetime.now()
        rankings = []
        
        for symbol in MARCHES:
            score, prix = analyze_market(symbol)
            rankings.append({"symbol": symbol, "score": score, "price": prix})
            
            # --- ALERTES ÉLITE (PUSH) ---
            if score >= 70: # HAUSSE
                msg = f"🚀 **SIGNAL ÉLITE : ACHAT (LONG)**\n━━━━━━━━━━━━━━\n💎 Actif : `{symbol}`\n📈 Probabilité : **{score}%**\n💵 Prix : `{prix:.4f}`"
                try: await app.bot.send_message(ADMIN_ID, msg, parse_mode='Markdown')
                except: pass
            elif score <= 30: # BAISSE
                prob_baisse = round(100 - score, 1)
                msg = f"⚠️ **SIGNAL ÉLITE : VENTE (SHORT)**\n━━━━━━━━━━━━━━\n💎 Actif : `{symbol}`\n📉 Probabilité : **{prob_baisse}%**\n💵 Prix : `{prix:.4f}`"
                try: await app.bot.send_message(ADMIN_ID, msg, parse_mode='Markdown')
                except: pass
                
            await asyncio.sleep(0.6)

        # --- RAPPORT SIMPLIFIÉ ---
        rankings.sort(key=lambda x: x["score"], reverse=True)
        
        report = f"🛰 **RADAR MARKET-IA** ({datetime.now().strftime('%H:%M')})\n"
        report += "━━━━━━━━━━━━━━━━━━\n\n"
        
        # On ne prend que le Top 5 Hausse et Top 5 Baisse pour la clarté
        report += "🔥 **TOP OPPORTUNITÉS (BUY) :**\n"
        for item in rankings[:5]:
            report += f"🟢 `{item['symbol']}` : **{item['score']}%**\n"
        
        report += "\n❄️ **TOP OPPORTUNITÉS (SELL) :**\n"
        # On prend les 5 derniers et on les inverse pour avoir le plus bas en premier
        worst = rankings[-5:]
        worst.reverse()
        for item in worst:
            p_baisse = round(100 - item['score'], 1)
            report += f"🔴 `{item['symbol']}` : **{p_baisse}%**\n"
        
        report += "\n━━━━━━━━━━━━━━━━━━\n💡 *Scores > 70% = Alerte immédiate*"
        
        try: await app.bot.send_message(ADMIN_ID, report, parse_mode='Markdown')
        except: pass

        duration = (datetime.now() - start_time).total_seconds()
        await asyncio.sleep(max(0, 900 - duration))

async def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    asyncio.create_task(run_scan(app))
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
