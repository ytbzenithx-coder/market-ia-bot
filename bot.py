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

db = {
    "clients": {8166605026: {"vip": True, "banni": False}},
    "stats": {"trades": 47, "gagnes": 31, "perdus": 16, "profit": 142.50},
    "historique": []
}

# --- SERVEUR DE MAINTIEN ---
def run_dummy_server():
    PORT = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        httpd.serve_forever()

# --- LOGIQUE IA ---
def analyze_market(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        data = requests.get(url, timeout=5).json()
        df = pd.DataFrame(data, columns=['OT','O','H','L','C','V','CT','QV','NT','TB','TQ','I'])
        df['C'] = df['C'].astype(float)
        df['Returns'] = df['C'].pct_change().dropna()
        X = df['Returns'].values[:-1].reshape(-1, 1)
        y = (df['Returns'].values[1:] > 0).astype(int)
        model = LogisticRegression().fit(X, y)
        prob = model.predict_proba(df['Returns'].values[-1].reshape(-1,1))[0][1] * 100
        return round(prob, 1), df['C'].iloc[-1]
    except: return 50.0, 0

# --- COMMANDES ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in db["clients"]: db["clients"][uid] = {"vip": False, "banni": False}
    await update.message.reply_text("🚀 **MarketAI Cloud Online**\nLe scan automatique est synchronisé toutes les 15min.")

async def send_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if db["clients"].get(update.effective_user.id, {}).get("banni"): return
    await update.message.reply_text("📊 Analyse manuelle...")
    rankings = []
    for s in MARCHES:
        score, _ = analyze_market(s)
        rankings.append({"s": s, "p": score})
    rankings.sort(key=lambda x: x["p"], reverse=True)
    msg = "🏆 **TOP 15 ACTUEL**\n"
    for i, item in enumerate(rankings[:15]):
        msg += f"{i+1}. `{item['s']}` : {item['p']}%\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    args = context.args
    if not args:
        await update.message.reply_text("🛠 /admin vip ID | /admin msg TEXTE")
        return
    action = args[0]
    try:
        if action == "vip":
            target = int(args[1])
            db["clients"][target] = {"vip": True, "banni": False}
            await update.message.reply_text(f"✅ VIP ajouté.")
        elif action == "msg":
            txt = " ".join(args[1:])
            for uid in db["clients"]:
                try: await context.bot.send_message(uid, f"📢 **ANNONCE**\n\n{txt}")
                except: pass
    except: await update.message.reply_text("❌ Erreur.")

# --- SCANNER SYNCHRONISÉ ---
async def run_scan(app: Application):
    while True:
        start_scan_time = datetime.now()
        rankings = []
        alerts_sent = 0
        
        for symbol in MARCHES:
            score, prix = analyze_market(symbol)
            rankings.append({"symbol": symbol, "score": score, "price": prix})
            if score >= 70:
                alerts_sent += 1
                msg = f"🚨 **SIGNAL ÉLITE IA**\nActif : {symbol}\nScore : {score}%\nPrix : {prix:.4f}"
                for uid, data in db["clients"].items():
                    if not data["banni"]:
                        try: await app.bot.send_message(uid, msg, parse_mode='Markdown')
                        except: pass
            await asyncio.sleep(0.5)

        rankings.sort(key=lambda x: x["score"], reverse=True)
        
        report = f"🛰 **RAPPORT DE VIE CLOUD** ({datetime.now().strftime('%H:%M')})\n"
        report += f"━━━━━━━━━━━━━━━━━━\n✅ Scan terminé. Alertes envoyées : {alerts_sent}\n\n📊 **TOP 30 :**\n"
        for i, item in enumerate(rankings):
            icon = "🟢" if item['score'] >= 65 else ("🟡" if item['score'] >= 55 else "⚪️")
            report += f"{i+1}. {icon} `{item['symbol']}` : **{item['score']}%**\n"
        
        try: await app.bot.send_message(ADMIN_ID, report, parse_mode='Markdown')
        except: pass

        # CALCUL DU TEMPS DE REPOS POUR TOMBER PILE SUR 15 MIN
        duration = (datetime.now() - start_scan_time).total_seconds()
        sleep_time = max(0, 900 - duration) 
        print(f"Scan duré {duration}s. Pause de {sleep_time}s.")
        await asyncio.sleep(sleep_time)

# --- LANCEMENT ---
async def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top", send_top))
    app.add_handler(CommandHandler("admin", admin_control))
    
    asyncio.create_task(run_scan(app))
    async with app:
        await app.initialize()
        await app.start()
        print("Bot en ligne - Temps synchronisé")
        await app.updater.start_polling()
        while True: await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

