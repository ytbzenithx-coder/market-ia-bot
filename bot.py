import os
import requests
import time
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "CONNEXION OK - EN ATTENTE DE TELEGRAM"

def send_loop():
    # On attend 10 secondes pour que Render soit bien prêt
    time.sleep(10)
    token = "8748658608:AAEBzyCtNKERBZ69HVnoP6CpQP1hPWdJwAI"
    chat_id = "8166605026"
    
    while True:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": "🚩 NIVEAU 1 : Connexion établie ! Le bot te voit."}
        try:
            r = requests.post(url, json=payload, timeout=10)
            print(f"Tentative : {r.status_code}")
        except Exception as e:
            print(f"Erreur : {e}")
        time.sleep(30) # Un message toutes les 30s pour tester

if __name__ == "__main__":
    t = Thread(target=send_loop)
    t.start()
    app.run(host='0.0.0.0', port=8080)

