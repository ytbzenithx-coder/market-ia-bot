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

# --- ANALYSE IA BLINDÉE ---
def analyze_market(symbol):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200: return 50.1, 0
        data = response.json()
        if not data or len(data) < 50: return 50.2, 0

        # Traitement des données
        df = pd.DataFrame(data, columns=['OT','O','H','L','C','V','CT','QV','NT','TB','TQ','I'])
        prices = df['C'].astype(float).values
        
        # Calcul des variations (Returns)
        returns = np.diff(prices) / prices[:-1]
        
        # Préparation des données pour la Régression Logistique
        X = returns[:-1].reshape(-1, 1)
        y = (returns[1:] > 0).astype(int)
        
        # Sécurité : il faut au moins deux classes (Up et Down) pour l'IA
        if len(np.unique(y)) < 2: 
            return 50.0, prices[-1]

        # Utilisation du solver 'liblinear' pour la stabilité sur serveur Linux
        model = LogisticRegression(solver='liblinear').fit(X, y)
        
        # Prédiction sur la dernière variation connue
        last_val = np.array([[returns[-1]]])
        prob = model.predict_proba(last_val)[0][1] * 100
        
        return round(prob, 1), prices[-1]
    except Exception as e:
        print(f"Erreur calcul {symbol}: {e}")
        return 48.0, 0

# --- COMMANDES ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 **MarketAI Cloud Online**\nLe système est synchronisé.")

# --- CYCLE DE SCAN ---
async def run_scan(app: Application):
    while True:
        start_time = datetime.now()
        rankings = []
        alerts_sent = 0
        
        for symbol in MARCHES:
            score, prix = analyze_market(symbol)
            rankings.append({"symbol": symbol, "score": score})
            
            # Alerte si score réel >= 70%
            if 70 <= score < 99:
                alerts_sent += 1
                try: 
                    msg = f"🚨 **SIGNAL ÉLITE IA**\n{symbol} : {score}%\nPrix : {prix:.4f}"
                    await app.bot.send_message(ADMIN_ID, msg)
                except: pass
            await asyncio.sleep(0.6)

        rankings.sort(key=lambda x: x["score"], reverse=True)
        
        # Rapport de Vie
        report = f"🛰 **RAPPORT DE VIE** ({datetime.now().strftime('%H:%M')})\n"
        report += "━━━━━━━━━━━━━━━━━━\n"
        for i, item in enumerate(rankings):
            # Gestion visuelle des codes erreurs
            if item['score'] == 50.1: status = "🚫 IP BLOCK"
            elif item['score'] == 50.2: status = "⚠️ DATA ERR"
            elif item['score'] == 48.0: status = "❌ MATH ERR"
            else:
                icon = "🟢" if item['score'] >= 65 else ("🟡" if item['score'] >= 55 else "⚪️")
                status = f"{icon} **{item['score']}%**"
            
            report += f"{i+1}. `{item['symbol']}` : {status}\n"
        
        try: await app.bot.send_message(ADMIN_ID, report, parse_mode='Markdown')
        except: pass

        # Synchronisation 15 minutes
        duration = (datetime.now() - start_time).total_seconds()
        await asyncio.sleep(max(0, 900 - duration))

async def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    
    asyncio.create_task(run_scan(app))
    async with app:
        await app.initialize()
        await app.start()
        # drop_pending_updates=True pour éviter les conflits au reboot
        await app.updater.start_polling(drop_pending_updates=True)
        while True: await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
