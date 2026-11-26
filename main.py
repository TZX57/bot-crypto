import os, time, threading, requests
from flask import Flask
app = Flask(__name__)
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID","").strip()
print(f"BOT AVVIATO - TOKEN: {bool(TOKEN)} - CHAT_ID: {CHAT_ID}", flush=True)
def send_telegram(text): print("INVIO TELEGRAM...", flush=True); r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": text}, timeout=10); print(f"TELEGRAM RISPOSTA: {r.status_code} - {r.text[:200]}", flush=True); return r.status_code == 200
def bot_loop(): time.sleep(3); print("INVIO MESSAGGIO DI AVVIO...", flush=True); send_telegram("🤖 BOT V5 TELEGRAM AVVIATO - Il bot è online e funziona!")
def home(): return "Bot attivo!"
def test(): ok = send_telegram("✅ TEST: Se leggi questo, il bot funziona!"); return f"Test inviato: {ok}"
app.add_url_rule("/", "home", home)
app.add_url_rule("/test", "test", test)
if __name__ == "__main__": threading.Thread(target=bot_loop, daemon=True).start(); port = int(os.environ.get("PORT", 10000)); app.run(host="0.0.0.0", port=port)
