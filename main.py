import os
import time
import threading
import requests
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
return "Bot attivo!"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(msg):
try:
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
data = {"chat_id": CHAT_ID, "text": msg}
requests.post(url, data=data, timeout=10)
except Exception as e:
print(f"Errore invio: {e}")

def bot_loop():
time.sleep(5)
send_telegram("🤖 BOT V5 TELEGRAM AVVIATO\nBot online e funzionante!")
while True:
time.sleep(60)

if __name__ == "__main__":
t = threading.Thread(target=bot_loop, daemon=True)
t.start()
port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
