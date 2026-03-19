import os
import time
import ccxt
import pandas as pd
import numpy as np
import requests
from flask import Flask
from threading import Thread
from sklearn.linear_model import LogisticRegression
from dotenv import load_dotenv

load_dotenv()

# --- Configuration des identifiants (Variables d'Environnement) ---
API_KEY = os.getenv('MEXC_API_KEY')
SECRET_KEY = os.getenv('MEXC_SECRET_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Initialisation MEXC Futures
exchange = ccxt.mexc({
    'apiKey': API_KEY,
    'secret': SECRET_KEY,
    'options': {'defaultType': 'swap'}
})

app = Flask('')

@app.route('/')
def home():
    return "Bot Trading IA est en ligne !"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Erreur Telegram: {e}")

def fetch_data(symbol="BTC/USDT"):
    # On récupère les données de Binance via CCXT pour l'analyse
    binance = ccxt.binance()
    bars = binance.fetch_ohlcv(symbol, timeframe="15m", limit=100)
    df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
    return df

def predict_signal(df):
    df['returns'] = df['close'].pct_change()
    df.dropna(inplace=True)
    
    # Feature engineering basique (5 dernières bougies)
    X = np.array([df['returns'].iloc
