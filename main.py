import requests
import pandas as pd
import datetime
import time
import smtplib
from email.mime.text import MIMEText

# --- CONFIG ---
ETORO_PRICE_MANUAL = 93187.39  # Update this manually or fetch via API if available
EMAIL = "jahboh123@gmail.com"
APP_PASSWORD = "gkwi dagy khuh ykxa"
TO_EMAIL = EMAIL  # Change if sending to different address

# --- Fetch BTC Price Data from CoinGecko ---
def fetch_btc_data(days=200):
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    params = {"vs_currency": "usd", "days": days, "interval": "daily"}
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data['prices'], columns=['timestamp', 'Close'])
    df['Date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('Date', inplace=True)
    df.drop(columns='timestamp', inplace=True)
    return df

# --- Calculate Indicators ---
def calculate_indicators(df):
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    short_ema = df['Close'].ewm(span=12, adjust=False).mean()
    long_ema = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = short_ema - long_ema
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

# --- Signal Logic ---
def generate_signal(rsi, price, sma50, sma200, macd, macd_signal):
    if macd < macd_signal and (rsi > 65 or (price > sma50 and price > sma200)):
        return "🔻 Sell Signal - Sell all"
    elif macd > macd_signal and rsi < 35 and price < sma50 and price > sma200:
        return "🟢 Buy Signal - Invest all"
    elif 35 <= rsi < 45 and price <= sma50 and macd > macd_signal:
        return "🟡 Building Buy Zone - Invest slowly"
    else:
        return "⚪ Neutral/Wait - Hold cash"

# --- Email Function ---
def send_email(subject, body):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL
    msg['To'] = TO_EMAIL
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, APP_PASSWORD)
        server.send_message(msg)

# --- Main Worker ---
last_signal = None

def check_and_alert():
    global last_signal
    df = fetch_btc_data()
    df = calculate_indicators(df)
    latest = df.iloc[-1]

    price = ETORO_PRICE_MANUAL  # Replace with live fetch if you have one
    signal = generate_signal(latest['RSI'], price, latest['SMA_50'], latest['SMA_200'], latest['MACD'], latest['MACD_Signal'])

    if signal != last_signal:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        reason = f"Signal changed at {now}\n\nPrice: ${price:.2f}\nRSI: {latest['RSI']:.2f}\nSMA_50: ${latest['SMA_50']:.2f}\nSMA_200: ${latest['SMA_200']:.2f}\nMACD: {latest['MACD']:.4f}\nMACD Signal: {latest['MACD_Signal']:.4f}"
        send_email(f"BTC Alert: {signal}", reason)
        last_signal = signal

# --- Loop every 60 mins ---
if __name__ == "__main__":
    while True:
        try:
            check_and_alert()
        except Exception as e:
            send_email("BTC Script Error", str(e))
        time.sleep(3600)  # Wait 1 hour
