import os, time, threading, requests, datetime
from flask import Flask
import json
FILE_STATO = "stato.json"
def salva_stato(): json.dump({"saldo": ST, "posizioni": POSIZIONI, "storico": STORICO}, open(FILE_STATO, "w"))
def carica_stato(): (lambda d: [ST.update(d["saldo"]), POSIZIONI.update(d["posizioni"]), STORICO.extend(d["storico"])])(json.load(open(FILE_STATO))) if os.path.exists(FILE_STATO) else None
app = Flask(__name__)
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = "7205695814"
ST = {"saldo": 100.0, "op": 0, "report": ""}
POSIZIONI = {}
STORICO = []
carica_stato()
CRYPTO = ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","ADAUSDT","AVAXUSDT","LINKUSDT","DOTUSDT","LTCUSDT","NEARUSDT","ATOMUSDT","APTUSDT","ARBUSDT","OPUSDT","INJUSDT","STXUSDT","TIAUSDT","SEIUSDT","SUIUSDT"]
AZIONI = ["AAPL","AMZN","AMAT"]
print(f"BOT FINALE AVVIATO - SALDO: {ST['saldo']} - CHAT: {CHAT_ID}", flush=True)
def send_telegram(text): print(f"INVIO: {text[:80]}", flush=True); r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": text}, timeout=15); print(f"RISPOSTA TG: {r.status_code}", flush=True); return r.status_code == 200
def rsi_calc(p): d = [p[i]-p[i-1] for i in range(1, len(p))]; g = [max(0, x) for x in d]; l = [max(0, -x) for x in d]; mg = sum(g[-14:]) / 14; ml = sum(l[-14:]) / 14; rs = mg / (ml if ml != 0 else 0.01); return 100 - (100 / (1 + rs))
def get_crypto(s): r = requests.get(f"https://api.binance.com/api/v3/klines?symbol={s}&interval=15m&limit=20", timeout=10); c = [float(x[4]) for x in r.json()]; return c[-1], rsi_calc(c), ((c[-1]-c[-2])/c[-2]*100)
def get_azione(s): r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?interval=15m&range=1d", headers={"User-Agent": "Mozilla/5.0"}, timeout=10); q = r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]; c = [x for x in q if x is not None]; return c[-1], rsi_calc(c), ((c[-1]-c[-2])/c[-2]*100)
def decidi(rsi, var): return (4, "PERFETTO RIMBALZO - RSI molto basso, probabile rimbalzo") if rsi < 30 else (2, "BUONO RIMBALZO - RSI basso e prezzo in calo") if rsi < 38 and var < 0 else (4, "PERFETTO TREND - RSI forte e prezzo in salita") if rsi > 65 and var > 1 else (2, "BUONO TREND - RSI in crescita e prezzo in salita") if rsi > 55 and var > 0.5 else (0, "")
def apri(sym, prezzo, importo, motivo, tipo): POSIZIONI[sym] = {"prezzo": prezzo, "importo": importo, "motivo": motivo, "tipo": tipo}; ST["saldo"] = ST["saldo"] - importo; ST["op"] = ST["op"] + 1; STORICO.append(f"COMPRA {sym} {importo}E"); send_telegram(f"🟢 COMPRA\nCOSA: {sym}\nQUANTO: {importo}€\nPREZZO: {prezzo}\nPERCHE: {motivo}\nTIPO: {tipo}\nSALDO RIMASTO: {round(ST['saldo'],2)}€\nOPERAZIONE {ST['op']}/50"); salva_stato()
def chiudi(sym, prezzo, motivo_chiusura): pos = POSIZIONI.pop(sym); profitto = (prezzo - pos["prezzo"]) / pos["prezzo"] * 100; guadagno = pos["importo"] * profitto / 100; ST["saldo"] = ST["saldo"] + pos["importo"] + guadagno; ST["op"] = ST["op"] + 1; STORICO.append(f"VENDI {sym} {round(guadagno,2)}E"); send_telegram(f"🔴 VENDI\nCOSA: {sym}\nQUANTO: {pos['importo']}€\nPREZZO ENTRATA: {pos['prezzo']} | USCITA: {prezzo}\nPROFITTO: {round(profitto,2)}% = {round(guadagno,2)}€\nPERCHE: {motivo_chiusura}\nSALDO: {round(ST['saldo'],2)}€\nOPERAZIONE {ST['op']}/50"); salva_stato()
def check_vendita(sym): prezzo, rsi, var = get_crypto(sym) if sym in CRYPTO else get_azione(sym); profitto = (prezzo - POSIZIONI[sym]["prezzo"]) / POSIZIONI[sym]["prezzo"] * 100; motivo = "STOP LOSS -5% raggiunto" if profitto <= -5 else "TAKE PROFIT +20% - massimo preso" if profitto >= 20 else "VENDI - era a +4% ma ora scende" if profitto >= 4 and var < 0 else "VENDI - RSI alto, mercato stanco" if profitto >= 4 and rsi > 65 else "VENDI - RSI > 75 ipercomprato" if rsi > 75 else ""; chiudi(sym, prezzo, motivo) if motivo != "" else None
def check_asset(sym, is_crypto): prezzo, rsi, var = get_crypto(sym) if is_crypto else get_azione(sym); importo, motivo = decidi(rsi, var); tipo = "RIMBALZO" if "RIMBALZO" in motivo else "TREND"; apri(sym, prezzo, importo, motivo, tipo) if importo > 0 and len(POSIZIONI) < 5 and ST["op"] < 50 and sym not in POSIZIONI and ST["saldo"] >= importo else None
def check_all(): [check_vendita(s) for s in list(POSIZIONI.keys())]; [check_asset(s, True) for s in CRYPTO]; [check_asset(s, False) for s in AZIONI]
def report_21(): ora = datetime.datetime.now(); oggi = ora.strftime("%Y-%m-%d"); testo = f"📊 REPORT 21:00 - Ultime 24h\n💰 Saldo: {round(ST['saldo'],2)}€ / 100€\n🔢 Operazioni: {ST['op']}/50\n📂 Posizioni aperte: {len(POSIZIONI)}\n📜 Storico:\n" + "\n".join(STORICO[-20:]) if len(STORICO) > 0 else "📊 REPORT 21:00 - Nessuna operazione oggi, nessuna operazione forzata"; send_telegram(testo); ST["report"] = oggi
def maybe_report(): o = datetime.datetime.now(); report_21() if o.hour == 21 and o.minute < 15 and ST["report"] != o.strftime("%Y-%m-%d") else None
def tick(): check_all(); maybe_report(); threading.Timer(900, tick).start()
def bot_loop(): time.sleep(5); send_telegram("🤖 BOT FINALE ATTIVO - Controllo ogni 15m"); tick()
def home(): return f"Bot Finale attivo - Saldo: {round(ST['saldo'],2)} - Op: {ST['op']} - Pos: {len(POSIZIONI)}"
def test(): ok = send_telegram("✅ TEST FINALE: Bot funziona!"); return f"Test: {ok}"
app.add_url_rule("/", "home", home)
app.add_url_rule("/test", "test", test)
if __name__ == "__main__": threading.Thread(target=bot_loop, daemon=True).start(); port = int(os.environ.get("PORT", 10000)); app.run(host="0.0.0.0", port=port)
