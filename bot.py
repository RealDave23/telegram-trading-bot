import time
import requests
import ccxt
import pandas as pd
from ta.momentum import RSIIndicator

# ================== CONFIG ==================
TELEGRAM_TOKEN = "8436955516:AAHYq6GhKrlbsOksPaKWs5WYlbJqP8OmFYQ"
TELEGRAM_CHAT_ID = "6000376255"

ALPHAVANTAGE_API_KEY = "8225131381:AAETuNFRTrROpBnf7zMW-XVjSu04AFxwxFk"

CHECK_INTERVAL = 60  # secondi

# Asset
CRYPTO_PAIRS = ["BTC/USDT", "ETH/USDT"]
FOREX_PAIRS = ["EURUSD", "GBPUSD"]

# RSI
RSI_PERIOD = 14
RSI_BUY = 30
RSI_SELL = 70

# ============================================

exchange = ccxt.binance()

last_signal = {}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

def get_crypto_prices(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1m", limit=RSI_PERIOD + 1)
    return [candle[4] for candle in ohlcv]

def get_forex_prices(pair):
    url = (
        "https://www.alphavantage.co/query"
        "?function=FX_INTRADAY"
        f"&from_symbol={pair[:3]}"
        f"&to_symbol={pair[3:]}"
        "&interval=1min"
        f"&apikey={ALPHAVANTAGE_API_KEY}"
    )
    r = requests.get(url).json()
    data = r.get("Time Series FX (1min)")
    if not data:
        return None
    closes = [float(v["4. close"]) for v in list(data.values())[:RSI_PERIOD + 1]]
    return closes[::-1]

def process_asset(name, prices):
    if prices is None or len(prices) < RSI_PERIOD:
        return

    rsi = RSIIndicator(pd.Series(prices), RSI_PERIOD).rsi().iloc[-1]

    prev = last_signal.get(name)

    if rsi < RSI_BUY and prev != "BUY":
        send_telegram(
            f"🚨 SEGNALE AUTOMATICO\n\n"
            f"Asset: {name}\n"
            f"Azione: BUY\n"
            f"RSI: {round(rsi,2)}\n\n"
            f"⚠️ Non è un consiglio finanziario"
        )
        last_signal[name] = "BUY"

    elif rsi > RSI_SELL and prev != "SELL":
        send_telegram(
            f"🚨 SEGNALE AUTOMATICO\n\n"
            f"Asset: {name}\n"
            f"Azione: SELL\n"
            f"RSI: {round(rsi,2)}\n\n"
            f"⚠️ Non è un consiglio finanziario"
        )
        last_signal[name] = "SELL"

# ================== LOOP ==================
send_telegram("🤖 Bot avviato correttamente")
print("Bot avviato correttamente")

while True:
    print("Controllo mercati...")
    try:
        # CRYPTO
        for pair in CRYPTO_PAIRS:
            prices = get_crypto_prices(pair)
            process_asset(pair, prices)

        # FOREX
        for pair in FOREX_PAIRS:
            prices = get_forex_prices(pair)
            process_asset(pair, prices)

    except Exception as e:
        print("Errore:", e)
        send_telegram(f"⚠️ Errore bot:\n{e}")

    print("Attendo prossimo ciclo...\n")
    time.sleep(CHECK_INTERVAL)

