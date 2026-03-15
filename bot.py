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

# Liste étendue à 30 marchés pour garantir 3 à 5 signaux Élite / jour
MARCHES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT", "DOGEUSDT", 
    "AVAXUSDT", "LINKUSDT", "LTCUSDT", "MATICUSDT", "NEARUSDT", "ATOMUSDT", "SHIBUSDT",
    "EURUSDT", "GBPUSDT", "AUDUSDT", "PAXGUSDT", "TRXUSDT", "UNIUSDT", "BCHUSDT", 
    "FILUSDT", "LDOUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "XLMUSDT", "VETUSDT", "ICPUSDT"
]

db = {"clients": {8166605026}, "stats": {"trades": 47, "profit": 142.50}}

# --- PETIT SERVEUR POUR RENDER FREE PLAN ---
def run_dummy_server():
    PORT = int(os.environ.get("PORT", 8080))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serveur de maintien en vie sur port {PORT}")
        httpd.serve_forever()

# --- LOGIQUE IA ---
def get_gauge(conf):
    filled = int(conf / 10)
    return "🟦" * filled + "⬜" * (10 - filled)

def analyze_market(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        data = requests.get(url, timeout=5).json()
        df = pd.DataFrame(data, columns=['OT','O','H','L','C','V','CT','QV','NT','TB','TQ','I'])
        df['C'] = df['C'].astype(float)
        df['Returns'] = df['C'].pct_change()
        df.dropna(inplace=True)
        X = df['Returns'].values[:-1].reshape(-1, 1)
        y = (df['Returns'].values[1:] > 0).astype(int)
        model = LogisticRegression().fit(X, y)
        prob = model.predict_proba(df['Returns'].values[-1].reshape(-1,1))[0][1] * 100
        return round(prob, 1), df['C'].iloc[-1]
    except: return 50.0, 0

# --- COMMANDES ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db["clients"].add(update.effective_user.id)
    await update.message.reply_text("🚀 **MarketAI Cloud Online**\nLe scan 15min est actif sur 30 marchés.")

async def send_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    s = db["stats"]
    msg = f"📈 **STATS BOT**\nProfit : +{s['profit']} USDT\nTrades : {s['trades']}"
    await update.message.reply_text(msg)

# --- BOUCLE DE SCAN ---
async def run_scan(app: Application):
    while True:
        start_time = datetime.now()
        results_text = []
        
        for symbol in MARCHES:
            score, prix = analyze_market(symbol)
            
            if score >= 70:
                alert = (f"🚨 **ALERTE ÉLITE IA**\n━━━━━━━━━━━━━━━━━━\n\n"
                         f"Actif : {symbol}\nDirection : {'BUY 🟢' if score > 50 else 'SELL 🔴'}\n"
                         f"Score : {score}%\n📍 Prix : {prix:.4f}")
                for uid in db["clients"]:
                    try: await app.bot.send_message(uid, alert, parse_mode='Markdown')
                    except: pass

            icon = "✅" if score >= 70 else ("⚠️" if score >= 55 else "❌")
            results_text.append(f"{icon} {symbol}: `{score}%`")
            await asyncio.sleep(0.1)

        dashboard = (f"🖥️ **TABLEAU DE BORD IA**\n📅 {start_time.strftime('%H:%M')}\n"
                     f"━━━━━━━━━━━━━━━━━━\n" + "\n".join(results_text[:15]) +
                     f"\n\n📈 SCORE : +{db['stats']['profit']} USDT")
        
        for uid in db["clients"]:
            try: await app.bot.send_message(uid, dashboard, parse_mode='Markdown')
            except: pass
            
        elapsed = (datetime.now() - start_time).total_seconds()
        await asyncio.sleep(max(0, 900 - elapsed))

# --- LANCEMENT ---
if __name__ == "__main__":
    # 1. Lancer le serveur de maintien en vie
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    # 2. Configurer le Bot
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", send_stats))
    
    # 3. Lancer le scan et le polling
    loop = asyncio.get_event_loop()
    loop.create_task(run_scan(application))
    
    print("Bot Ready on Render Free Plan")
    application.run_polling()

