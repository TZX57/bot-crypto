import time, requests, datetime, os, threading, json
from flask import Flask

# ===== CONFIG V5 TELEGRAM =====
CAPITALE_INIZIALE = 100.0
STOP_LOSS = -5.0
TAKE_PROFIT = 15.0
MAX_ORE_POSIZIONE = 12
CONTROLLO_SECONDI = 30
MAX_POSIZIONI_APERTE = 5
MAX_OPERAZIONI_GIORNO = 50
FILE_STATO = "stato.json"

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

CRYPTO = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT", "NEARUSDT", "ATOMUSDT"]
AZIONI = ["AAPL", "AMZN", "AMAT"]
# ======================

saldo = CAPITALE_INIZIALE
posizioni = []
storico = []
ultimo_report_giorno = None

def salva_stato():
try:
data = {
"saldo": saldo,
"posizioni": [{"symbol": p["symbol"], "prezzo": p["prezzo"], "quantita": p["quantita"], "ora": p["ora"].isoformat(), "importo": p["importo"], "tipo": p["tipo"]} for p in posizioni],
"storico": [{"symbol": s["symbol"], "profitto": s["profitto"], "ora_chiusura": s["ora_chiusura"].isoformat()} for s in storico],
"ultimo_report": str(ultimo_report_giorno) if ultimo_report_giorno else None
}
with open(FILE_STATO, "w") as f:
json.dump(data, f)
except Exception as e:
print("Errore salvataggio:", e)

def carica_stato():
global saldo, posizioni, storico, ultimo_report_giorno
if not os.path.exists(FILE_STATO):
print("Nessun stato, parto da 100€")
return
try:
with open(FILE_STATO, "r") as f:
data = json.load(f)
saldo = data.get("saldo", CAPITALE_INIZIALE)
posizioni = [{"symbol": p["symbol"], "prezzo": p["prezzo"], "quantita": p["quantita"], "ora": datetime.datetime.fromisoformat(p["ora"]), "importo": p["importo"], "tipo": p["tipo"]} for p in data.get("posizioni", [])]
storico = [{"symbol": s["symbol"], "profitto": s["profitto"], "ora_chiusura": datetime.datetime.fromisoformat(s["ora_chiusura"])} for s in data.get("storico", [])]
if data.get("ultimo_report"):
ultimo_report_giorno = datetime.date.fromisoformat(data["ultimo_report"][:10])
print(f"Stato ripristinato! Saldo: {saldo:.2f}€ Posizioni: {len(posizioni)}")
except Exception as e:
print("Errore caricamento:", e)

carica_stato()

app = Flask(__name__)
@app.route('/')
def home():
return f"Bot V5 Telegram attivo - Saldo: {saldo:.2f}€ - Posizioni: {len(posizioni)} - Op. oggi: {operazioni_oggi()}"
threading.Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000))), daemon=True).start()

def manda_telegram(msg):
try:
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
except Exception as e:
print("Errore Telegram:", e)

def calcola_rsi(chiusure, periodo=14):
if len(chiusure) < periodo + 1:
return 50
guadagni, perdite = [], []
for i in range(1, len(chiusure)):
diff = chiusure[i] - chiusure[i-1]
guadagni.append(max(diff, 0))
perdite.append(max(-diff, 0))
avg_gain = sum(guadagni[-periodo:]) / periodo
avg_loss = sum(perdite[-periodo:]) / periodo
if avg_loss == 0:
return 100
rs = avg_gain / avg_loss
return 100 - (100 / (1 + rs))

def prendi_crypto(symbol):
url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=15m&limit=100"
r = requests.get(url, timeout=10).json()
chiusure = [float(c[4]) for c in r]
volumi = [float(c[5]) for c in r]
return chiusure, volumi, chiusure[-1]

def prendi_azione(symbol):
url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=15m&range=5d"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers, timeout=10).json()
result = r['chart']['result'][0]
chiusure = [x for x in result['indicators']['quote'][0]['close'] if x is not None]
volumi = [x for x in result['indicators']['quote'][0]['volume'] if x is not None]
if len(chiusure) < 50:
return None, None, None
return chiusure, volumi, chiusure[-1]

def mercato_azioni_aperto():
ora = datetime.datetime.now()
if ora.weekday() >= 5:
return False
minuti = ora.hour * 60 + ora.minute
return 930 <= minuti <= 1320

def valuta(chiusure, volumi, prezzo):
media50 = sum(chiusure[-50:]) / 50
media20 = sum(chiusure[-20:]) / 20
rsi = calcola_rsi(chiusure)
volume_medio = sum(volumi[-24:]) / 24 if len(volumi) >= 24 else sum(volumi)/len(volumi)
volume_ultimo = volumi[-1]
if prezzo > media50 and rsi < 35 and volume_ultimo > volume_medio:
return {"livello": "PERFETTO", "importo": 4.0, "rsi": rsi, "motivo": f"RSI {rsi:.0f} + Trend UP + Volume"}
if prezzo > media20 and rsi < 45:
return {"livello": "BUONO", "importo": 2.0, "rsi": rsi, "motivo": f"RSI {rsi:.0f} + Sopra media 20"}
return None

def operazioni_oggi():
oggi = datetime.datetime.now().date()
return len([s for s in storico if s["ora_chiusura"].date() == oggi]) + len([p for p in posizioni if p["ora"].date() == oggi])

def manda_report():
oggi = datetime.datetime.now().date()
chiuse_oggi = [s for s in storico if s["ora_chiusura"].date() == oggi]
n_vinte = len([s for s in chiuse_oggi if s["profitto"] > 0])
n_perse = len([s for s in chiuse_oggi if s["profitto"] <= 0])
tot = sum([s["profitto"] for s in chiuse_oggi])
win = (n_vinte / len(chiuse_oggi) * 100) if chiuse_oggi else 0
manda_telegram(f"📊 REPORT GIORNALIERO 21:00\nData: {oggi}\n\nOperazioni chiuse: {len(chiuse_oggi)}\nVinte: {n_vinte} | Perse: {n_perse}\nWin Rate: {win:.0f}%\nProfitto oggi: {tot:+.2f}€\n\nPosizioni aperte: {len(posizioni)}\nSaldo totale: {saldo:.2f}€\nVariazione totale: {((saldo - CAPITALE_INIZIALE)/CAPITALE_INIZIALE*100):+.2f}%")

def controlla_bot():
global saldo, ultimo_report_giorno
ora = datetime.datetime.now()
if ora.hour == 21 and ora.minute < 1 and ultimo_report_giorno != ora.date():
manda_report()
ultimo_report_giorno = ora.date()
salva_stato()
print(f"--- {ora.strftime('%H:%M:%S')} Saldo: {saldo:.2f}€ Pos: {len(posizioni)} Op.oggi: {operazioni_oggi()} ---")
for pos in posizioni[:]:
try:
if pos['tipo'] == 'crypto':
_, _, prezzo_attuale = prendi_crypto(pos['symbol'])
else:
_, _, prezzo_attuale = prendi_azione(pos['symbol'])
if prezzo_attuale is None:
continue
var = ((prezzo_attuale - pos['prezzo']) / pos['prezzo']) * 100
ore = (ora - pos['ora']).total_seconds() / 3600
motivo = None
if var <= STOP_LOSS:
motivo = f"STOP LOSS {var:.2f}%"
elif var >= TAKE_PROFIT:
motivo = f"TAKE PROFIT +{var:.2f}%"
elif ore >= MAX_ORE_POSIZIONE:
motivo = f"Timeout 12h ({var:.2f}%)"
if motivo:
ricavo = pos['quantita'] * prezzo_attuale
profitto = ricavo - pos['importo']
saldo += ricavo
posizioni.remove(pos)
storico.append({"symbol": pos['symbol'], "profitto": profitto, "ora_chiusura": ora})
salva_stato()
emoji = "📈" if profitto >= 0 else "📉"
manda_telegram(f"🤖 BOT V5 {emoji}\nVENDUTO {pos['symbol']} a {prezzo_attuale:.2f}\nMotivo: {motivo}\nProfitto: {profitto:+.2f}€\nSaldo: {saldo:.2f}€ | Op. oggi: {operazioni_oggi()}/{MAX_OPERAZIONI_GIORNO}")
except Exception as e:
print(f"Errore chiusura {pos['symbol']}: {e}")
if len(posizioni) >= MAX_POSIZIONI_APERTE or operazioni_oggi() >= MAX_OPERAZIONI_GIORNO:
return
for symbol in CRYPTO:
if len(posizioni) >= MAX_POSIZIONI_APERTE:
break
if any(p['symbol'] == symbol for p in posizioni):
continue
try:
chiusure, volumi, prezzo = prendi_crypto(symbol)
segnale = valuta(chiusure, volumi, prezzo)
if segnale and saldo >= segnale['importo']:
saldo -= segnale['importo']
posizioni.append({"symbol": symbol, "prezzo": prezzo, "quantita": segnale['importo']/prezzo, "ora": ora, "importo": segnale['importo'], "tipo": "crypto"})
salva_stato()
manda_telegram(f"🤖 BOT V5\nCOMPRATO {symbol} a {prezzo:.2f} - {segnale['importo']:.0f}€\nLivello: {segnale['livello']} | {segnale['motivo']}\nSaldo: {saldo:.2f}€")
except Exception as e:
print(f"Errore {symbol}: {e}")
if mercato_azioni_aperto():
for symbol in AZIONI:
if len(posizioni) >= MAX_POSIZIONI_APERTE:
break
if any(p['symbol'] == symbol for p in posizioni):
continue
try:
chiusure, volumi, prezzo = prendi_azione(symbol)
if chiusure is None:
continue
segnale = valuta(chiusure, volumi, prezzo)
if segnale and saldo >= segnale['importo']:
saldo -= segnale['importo']
posizioni.append({"symbol": symbol, "prezzo": prezzo, "quantita": segnale['importo']/prezzo, "ora": ora, "importo": segnale['importo'], "tipo": "azione"})
salva_stato()
manda_telegram(f"🤖 BOT V5\nCOMPRATO {symbol} a {prezzo:.2f} - {segnale['importo']:.0f}€\nLivello: {segnale['livello']} | {segnale['motivo']}\nSaldo: {saldo:.2f}€")
except Exception as e:
print(f"Errore {symbol}: {e}")

if saldo == CAPITALE_INIZIALE and len(posizioni) == 0 and len(storico) == 0:
manda_telegram(f"🤖 BOT V5 TELEGRAM AVVIATO\nPaper Trading 100€\nMax 5 pos | Max 50 op/giorno\nCrypto 24/7 + AAPL/AMZN/AMAT\nReport ore 21:00")
else:
manda_telegram(f"🤖 BOT V5 RIAVVIATO\nSaldo ripristinato: {saldo:.2f}€\nPosizioni aperte: {len(posizioni)}")
print("Bot V5 avviato")
while True:
try:
controlla_bot()
except Exception as e:
print("Errore loop:", e)
time.sleep(CONTROLLO_SECONDI)
