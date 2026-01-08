import time
import requests
import ccxt
import pandas as pd

from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange

# ================== CONFIG ==================
TELEGRAM_TOKEN = "8436955516:AAHYq6GhKrlbsOksPaKWs5WYlbJqP8OmFYQ"
TELEGRAM_CHAT_ID = "-1003538186561"

ALPHAVANTAGE_API_KEY = "5N92AXF7061WRWWJ"

CHECK_INTERVAL = 60  # secondi

CRYPTO_PAIRS = ["BTC/USDT", "ETH/USDT"]
FOREX_PAIRS = ["EURUSD", "GBPUSD"]

RSI_PERIOD = 14
RSI_BUY = 30
RSI_SELL = 70
# ===========================================
STATUS_INTERVAL = 1 * 60 * 60  # 6 ore
last_status_time = 0

exchange = ccxt.binance()
last_signal = {}

# ================== TELEGRAM ==================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg
    })
def send_status_message():
    message = (
        "ℹ️ STATO BOT\n\n"
        "🤖 Il bot è attivo e funzionante\n"
        "📊 Al momento nessun segnale BUY o SELL valido\n"
        "⏳ Continuo a monitorare i mercati\n\n"
        "🔍 Strategia: RSI + EMA + Volume + ATR"
    )
    send_telegram(message)

# ================== ATR ==================
def calculate_atr(ohlcv):
    df = pd.DataFrame(
        ohlcv,
        columns=["time", "open", "high", "low", "close", "volume"]
    )
    atr = AverageTrueRange(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=14
    ).average_true_range().iloc[-1]
    return atr

# ================== DATA ==================
def get_crypto_data(symbol):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe="1m", limit=250)
    closes = [c[4] for c in ohlcv]
    volumes = [c[5] for c in ohlcv]
    atr = calculate_atr(ohlcv)
    return closes, volumes, atr

def get_forex_data(pair):
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
        return None, None

    closes = [float(v["4. close"]) for v in list(data.values())[:250]][::-1]
    highs  = [float(v["2. high"]) for v in list(data.values())[:250]][::-1]
    lows   = [float(v["3. low"])  for v in list(data.values())[:250]][::-1]

    df = pd.DataFrame({
        "high": highs,
        "low": lows,
        "close": closes
    })

    atr = AverageTrueRange(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        window=14
    ).average_true_range().iloc[-1]

    return closes, atr

# ================== STRATEGY ==================
def process_asset(name, prices, volumes, atr, is_crypto=True):
    if prices is None or atr is None or len(prices) < 200:
        return

    series = pd.Series(prices)

    rsi = RSIIndicator(series, RSI_PERIOD).rsi().iloc[-1]
    ema_fast = EMAIndicator(series, window=50).ema_indicator().iloc[-1]
    ema_slow = EMAIndicator(series, window=200).ema_indicator().iloc[-1]

    price = prices[-1]
    prev = last_signal.get(name)

    # ===== Volume filter (solo crypto) =====
    volume_ok = True
    if is_crypto and volumes:
        vol_ma = pd.Series(volumes).rolling(20).mean().iloc[-1]
        volume_ok = volumes[-1] > vol_ma

    # ===== BUY =====
    if rsi < RSI_BUY and ema_fast > ema_slow and volume_ok and prev != "BUY":
        tp = price + atr * 2
        sl = price - atr

        send_telegram(
            f"🟢🟢🟢 SEGNALE DI ACQUISTO\n\n"
            f"📈 COMPRA\n"
            f"Asset: {name}\n"
            f"Prezzo: {round(price,5)}\n\n"
            f"📊 RSI: {round(rsi,2)}\n"
            f"📈 Trend rialzista\n"
            f"📊 Volume OK\n\n"
            f"🎯 TP: {round(tp,5)}\n"
            f"🛑 SL: {round(sl,5)}\n\n"
            f"🤖 Segnale automatico"
        )
        last_signal[name] = "BUY"

    # ===== SELL =====
    elif rsi > RSI_SELL and ema_fast < ema_slow and volume_ok and prev != "SELL":
        tp = price - atr * 2
        sl = price + atr

        send_telegram(
            f"🔴🔴🔴 SEGNALE DI VENDITA\n\n"
            f"📉 VENDI\n"
            f"Asset: {name}\n"
            f"Prezzo: {round(price,5)}\n\n"
            f"📊 RSI: {round(rsi,2)}\n"
            f"📉 Trend ribassista\n"
            f"📊 Volume OK\n\n"
            f"🎯 TP: {round(tp,5)}\n"
            f"🛑 SL: {round(sl,5)}\n\n"
            f"🤖 Segnale automatico"
        )
        last_signal[name] = "SELL"

# ================== MAIN LOOP ==================
send_telegram("🤖 Bot avviato correttamente")

while True:
    try:
        print("Controllo mercati...")

        for pair in CRYPTO_PAIRS:
            prices, volumes, atr = get_crypto_data(pair)
            process_asset(pair, prices, volumes, atr, is_crypto=True)

        for pair in FOREX_PAIRS:
            prices, atr = get_forex_data(pair)
            process_asset(pair, prices, None, atr, is_crypto=False)

    except Exception as e:
        print("ERRORE:", e)
        send_telegram(f"⚠️ Errore bot:\n{e}")

    current_time = time.time()

    if current_time - last_status_time > STATUS_INTERVAL:
        send_status_message()
        last_status_time = current_time




    time.sleep(CHECK_INTERVAL)
