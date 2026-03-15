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

# --- ANALYSE IA SÉCURISÉE ---
def analyze_market(symbol):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200: return 50.1, 0
        data = response.json()
        if not data or len(data) < 50: return 50.2, 0

        df = pd.DataFrame(data, columns=['OT','O','H','L','C','V','CT','QV','NT','TB','TQ','I'])
        df['C'] = df['C'].astype(float)
        df['Returns'] = df['C'].pct_change().dropna()
        X = df['Returns'].values[:-1].reshape(-1, 1)
        y = (df['Returns'].values[1:] > 0).astype(int)
        
        if len(np.unique(y)) < 2: return 50.0, df['C'].iloc[-1]

        model = LogisticRegression().fit(X, y)
        prob = model.predict_proba(df['Returns'].values[-1].reshape(-1,1))[0][1] * 100
        return round(prob, 1), df['C'].iloc[-1]
    except: return 49.9, 0

# --- COMMANDES ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **MarketAI Cloud Online**\nLe scan est en cours...")

# --- CYCLE DE SCAN ---
async def run_scan(app: Application):
    while True:
        start_time = datetime.now()
        rankings = []
        for symbol in MARCHES:
            score, prix = analyze_market(symbol)
            rankings.append({"symbol": symbol, "score": score})
            if score >= 70:
                try: await app.bot.send_message(ADMIN_ID, f"🚨 **SIGNAL ÉLITE**\n{symbol}: {score}%")
                except: pass
            await asyncio.sleep(0.6) # Un peu plus lent pour la stabilité

        rankings.sort(key=lambda x: x["score"], reverse=True)
        report = f"🛰 **RAPPORT DE VIE** ({datetime.now().strftime('%H:%M')})\n"
        report += "━━━━━━━━━━━━━━━━━━\n"
        for i, item in enumerate(rankings):
            icon = "🟢" if item['score'] >= 65 else ("🟡" if item['score'] >= 55 else "⚪️")
            report += f"{i+1}. {icon} `{item['symbol']}` : **{item['score']}%**\n"
        
        try: await app.bot.send_message(ADMIN_ID, report, parse_mode='Markdown')
        except: pass

        duration = (datetime.now() - start_time).total_seconds()
        await asyncio.sleep(max(0, 900 - duration))

async def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    # drop_pending_updates=True évite les conflits au lancement
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    asyncio.create_task(run_scan(app))
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
                
