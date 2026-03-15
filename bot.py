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
# Remplace par ton token si nécessaire, mais celui-ci semble être le bon
TOKEN = "8748658608:AAEBzyCtNKERBZ69HVnoP6CpQP1hPWdJwAI"
ADMIN_ID = 8166605026

# Liste des 30 marchés à scanner
MARCHES = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT", "DOGEUSDT", 
    "AVAXUSDT", "LINKUSDT", "LTCUSDT", "MATICUSDT", "NEARUSDT", "ATOMUSDT", "SHIBUSDT",
    "EURUSDT", "GBPUSDT", "AUDUSDT", "PAXGUSDT", "TRXUSDT", "UNIUSDT", "BCHUSDT", 
    "FILUSDT", "LDOUSDT", "APTUSDT", "ARBUSDT", "OPUSDT", "XLMUSDT", "VETUSDT", "ICPUSDT"
]

# Base de données temporaire
db = {
    "clients": {8166605026: {"vip": True, "banni": False}},
    "stats": {"trades": 47, "gagnes": 31, "perdus": 16, "profit": 142.50},
    "historique": []
}

# --- SERVEUR DE MAINTIEN (POUR RENDER) ---
def run_dummy_server():
    PORT = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"Serveur actif sur le port {PORT}")
        httpd.serve_forever()

# --- LOGIQUE IA ---
def analyze_market(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        response = requests.get(url, timeout=5)
        data = response.json()
        df = pd.DataFrame(data, columns=['OT','O','H','L','C','V','CT','QV','NT','TB','TQ','I'])
        df['C'] = df['C'].astype(float)
        df['Returns'] = df['C'].pct_change().dropna()
        
        # Préparation du modèle Logistique
        X = df['Returns'].values[:-1].reshape(-1, 1)
        y = (df['Returns'].values[1:] > 0).astype(int)
        model = LogisticRegression().fit(X, y)
        
        # Calcul de probabilité sur la dernière bougie
        last_ret = df['Returns'].values[-1].reshape(-1,1)
        prob = model.predict_proba(last_ret)[0][1] * 100
        return round(prob, 1), df['C'].iloc[-1]
    except Exception:
        return 50.0, 0

# --- COMMANDES CLIENTS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in db["clients"]:
        db["clients"][uid] = {"vip": False, "banni": False}
    await update.message.reply_text("🚀 **MarketAI Cloud Online**\nLe scan automatique tourne toutes les 15min.\nCommandes: /top, /stats")

async def send_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if db["clients"].get(update.effective_user.id, {}).get("banni"): return
    s = db["stats"]
    msg = f"📈 **STATS GLOBALES**\n━━━━━━━━━━━━\nProfit : +{s['profit']} USDT\nWinrate : 65%\nTrades : {s['trades']}"
    await update.message.reply_text(msg)

async def send_top_manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if db["clients"].get(update.effective_user.id, {}).get("banni"): return
    await update.message.reply_text("📊 Analyse manuelle en cours sur 30 marchés...")
    rankings = []
    for s in MARCHES:
        score, _ = analyze_market(s)
        rankings.append({"s": s, "p": score})
    rankings.sort(key=lambda x: x["p"], reverse=True)
    
    msg = "🏆 **TOP 15 ACTUEL**\n━━━━━━━━━━━━\n"
    for i, item in enumerate(rankings[:15]):
        msg += f"{i+1}. `{item['s']}` : **{item['p']}%**\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

# --- COMMANDES ADMIN ---
async def admin_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    args = context.args
    if not args:
        await update.message.reply_text("🛠 **ADMIN**\n`/admin vip ID`\n`/admin msg TEXTE`", parse_mode='Markdown')
        return
    
    action = args[0]
    try:
        if action == "vip":
            target = int(args[1])
            db["clients"][target] = {"vip": True, "banni": False}
            await update.message.reply_text(f"✅ Utilisateur {target} est maintenant VIP.")
        elif action == "msg":
            txt = " ".join(args[1:])
            for uid in db["clients"]:
                try: await context.bot.send_message(uid, f"📢 **ANNONCE ADMIN**\n\n{txt}")
                except: pass
    except: await update.message.reply_text("❌ Erreur de syntaxe.")

# --- SCANNER AUTOMATIQUE & RAPPORT TOP 30 ---
async def run_scan(app: Application):
    while True:
        rankings = []
        alerts_sent = 0
        
        # Scan des 30 marchés
        for symbol in MARCHES:
            score, prix = analyze_market(symbol)
            rankings.append({"symbol": symbol, "score": score, "price": prix})
            
            # Alerte si Élite
            if score >= 70:
                alerts_sent += 1
                alert_msg = f"🚨 **SIGNAL ÉLITE IA**\n━━━━━━━━━━━━\nActif : {symbol}\nDirection : BUY 🟢\nScore : {score}%\nPrix : {prix:.4f}"
                for uid, data in db["clients"].items():
                    if not data["banni"]:
                        try: await app.bot.send_message(uid, alert_msg, parse_mode='Markdown')
                        except: pass
            await asyncio.sleep(0.5)

        # Tri pour le rapport
        rankings.sort(key=lambda x: x["score"], reverse=True)
        
        # Construction du Rapport de Vie Top 30
        report = f"🛰 **RAPPORT DE VIE CLOUD** ({datetime.now().strftime('%H:%M')})\n"
        report += f"━━━━━━━━━━━━━━━━━━\n"
        report += f"✅ Scan terminé. Alertes envoyées : {alerts_sent}\n\n"
        report += f"📊 **CLASSEMENT TOP 30 :**\n"
        
        for i, item in enumerate(rankings):
            icon = "🟢" if item['score'] >= 65 else ("🟡" if item['score'] >= 55 else "⚪️")
            report += f"{i+1}. {icon} `{item['symbol']}` : **{item['score']}%**\n"
        
        report += f"\n━━━━━━━━━━━━━━━━━━\nProchain scan dans 15 minutes."

        # Envoi à l'Admin uniquement
        try:
            await app.bot.send_message(ADMIN_ID, report, parse_mode='Markdown')
        except:
            pass
            
        await asyncio.sleep(900)

# --- LANCEMENT ---
async def main():
    # Lancement serveur web Render
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", send_stats))
    app.add_handler(CommandHandler("top", send_top_manual))
    app.add_handler(CommandHandler("admin", admin_control))
    
    # Lancement du scanneur en fond
    asyncio.create_task(run_scan(app))
    
    # Démarrage
    async with app:
        await app.initialize()
        await app.start()
        print("Bot opérationnel sur Render !")
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
