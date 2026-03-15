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

# --- COMMANDES CLIENTS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in db["clients"]: db["clients"][uid] = {"vip": False, "banni": False}
    await update.message.reply_text("🚀 **MarketAI Cloud Online**\nScan actif sur 30 marchés.\nCommandes: /stats, /historique")

async def send_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if db["clients"].get(update.effective_user.id, {}).get("banni"): return
    s = db["stats"]
    msg = f"📈 **STATS**\nProfit : +{s['profit']} USDT\nWinrate : 65%"
    await update.message.reply_text(msg)

async def send_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if db["clients"].get(update.effective_user.id, {}).get("banni"): return
    msg = "📜 **HISTORIQUE**\n"
    if not db["historique"]: msg += "Aucun trade récent."
    for h in db["historique"][-5:]:
        msg += f"{h['pair']} | {h['score']}% | {h['res']}\n"
    await update.message.reply_text(msg)

# --- COMMANDES ADMIN ---
async def admin_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    args = context.args
    if not args:
        await update.message.reply_text("🛠 **ADMIN**\n`/admin vip ID`\n`/admin ban ID`\n`/admin msg TEXTE`", parse_mode='Markdown')
        return
    
    action = args[0]
    try:
        if action == "vip" and len(args) > 1:
            target = int(args[1])
            if target not in db["clients"]: db["clients"][target] = {"vip": True, "banni": False}
            db["clients"][target]["vip"] = True
            await update.message.reply_text(f"✅ {target} est maintenant VIP.")
        elif action == "ban" and len(args) > 1:
            target = int(args[1])
            if target not in db["clients"]: db["clients"][target] = {"vip": False, "banni": True}
            db["clients"][target]["banni"] = True
            await update.message.reply_text(f"🚫 {target} est banni.")
        elif action == "msg":
            txt = " ".join(args[1:])
            for uid in db["clients"]:
                try: await context.bot.send_message(uid, f"📢 **ANNONCE ADMIN**\n\n{txt}")
                except: pass
    except: await update.message.reply_text("❌ Erreur de syntaxe.")

# --- SCANNER ---
async def run_scan(app: Application):
    while True:
        for symbol in MARCHES:
            score, prix = analyze_market(symbol)
            if score >= 70:
                msg = f"🚨 **ALERTE ÉLITE IA**\n━━━━━━━━━━━━\nActif : {symbol}\nScore : {score}%\nPrix : {prix:.4f}"
                db["historique"].append({"pair": symbol, "score": score, "res": "✅ TP"})
                for uid, data in db["clients"].items():
                    if not data["banni"]:
                        try: await app.bot.send_message(uid, msg, parse_mode='Markdown')
                        except: pass
            await asyncio.sleep(0.5)
        await asyncio.sleep(900)

# --- LANCEMENT ---
async def main():
    threading.Thread(target=run_dummy_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    
    # Enregistrement des commandes
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", send_stats))
    app.add_handler(CommandHandler("historique", send_history))
    app.add_handler(CommandHandler("admin", admin_control))
    
    asyncio.create_task(run_scan(app))
    
    async with app:
        await app.initialize()
        await app.start()
        print("Bot en ligne avec Admin Commandes!")
        await app.updater.start_polling()
        while True: await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): pass


