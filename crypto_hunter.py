import time
from datetime import datetime
import pytz
import requests

# --- TELEGRAM CONFIG ---
BOT_TOKEN = "8626042409:AAHElsiJD8_Jk9R7r5VHUj8fPjcl8Meacp4"
CHAT_ID = "706694019"

# Delta Exchange Symbols
DELTA_SYMBOLS = ["BTCUSD", "ETHUSD"]

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_delta_candles(symbol, resolution="15m", count=60):
    end_time = int(time.time())
    
    if resolution == "15m":
        start_time = end_time - (count * 15 * 60)
    elif resolution == "1d":
        start_time = end_time - (count * 24 * 60 * 60)
    else:
        start_time = end_time - (count * 60)
        
    url = "https://api.india.delta.exchange/v2/history/candles"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "start": start_time,
        "end": end_time
    }
    headers = {"Accept": "application/json"}
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10).json()
        candles = res.get("result", [])
        candles.reverse()
        return candles
    except Exception as e:
        print(f"Fetch Error ({symbol}): {e}")
        return []

def run_15m_crypto_scanner():
    ist = pytz.timezone('Asia/Kolkata')
    today_str = datetime.now(ist).strftime("%Y-%m-%d")
    alerts = []

    print(f"[{datetime.now(ist).strftime('%H:%M:%S')}] 15-Min Crypto Scanner Active...")

    for sym in DELTA_SYMBOLS:
        try:
            # 15-Minute Data
            c_15m = get_delta_candles(sym, resolution="15m", count=45)
            if len(c_15m) < 22:
                continue

            latest_c = c_15m[-2]
            c_time = datetime.fromtimestamp(latest_c[0], ist).strftime("%H:%M")
            c_open = float(latest_c[1])
            c_high = float(latest_c[2])
            c_low = float(latest_c[3])
            c_close = float(latest_c[4])
            c_vol = float(latest_c[5])

            # 20-SMA Volume
            prev_vols = [float(c[5]) for c in c_15m[-22:-2]]
            avg_vol_20 = sum(prev_vols) / len(prev_vols)
            if avg_vol_20 == 0:
                continue

            vol_ratio = c_vol / avg_vol_20

            # Daily High / Low
            c_1d = get_delta_candles(sym, resolution="1d", count=5)
            prev_high, prev_low = 0, 0
            if len(c_1d) >= 2:
                prev_day = c_1d[-2]
                prev_high = float(prev_day[2])
                prev_low = float(prev_day[3])

            # Today High / Low
            today_highs = []
            today_lows = []
            for c in c_15m:
                dt_str = datetime.fromtimestamp(c[0], ist).strftime("%Y-%m-%d")
                if dt_str == today_str:
                    today_highs.append(float(c[2]))
                    today_lows.append(float(c[3]))

            curr_today_high = max(today_highs) if today_highs else c_high
            curr_today_low = min(today_lows) if today_lows else c_low

            key_levels = [
                ("Today High", curr_today_high),
                ("Today Low", curr_today_low),
                ("Yesterday High", prev_high),
                ("Yesterday Low", prev_low)
            ]

            # Touching or Near Key Levels
            touched_level_names = []
            for name, lvl in key_levels:
                if lvl > 0:
                    if (c_low <= lvl <= c_high) or (abs(c_close - lvl) / c_close <= 0.002):
                        touched_level_names.append(f"{name} (${lvl:,.0f})")

            # Condition: 2x Volume + Level match
            if vol_ratio >= 2.0 and len(touched_level_names) > 0:
                is_bullish = c_close >= c_open
                signal = "🟢 *BUY SETUP (Bullish)*" if is_bullish else "🔴 *SELL SETUP (Bearish)*"
                level_str = ", ".join(touched_level_names)

                alert_text = (
                    f"💎 *{sym} (15-MIN)* ➔ {signal}\n"
                    f"⚡ *Volume Spike:* `{vol_ratio:.1f}x` (vs 20-Avg)\n"
                    f"🎯 *Key Level:* {level_str}\n"
                    f"💰 *LTP:* `${c_close:,.2f}`\n"
                    f"📊 *15m Range:* `${c_low:,.1f}` - `${c_high:,.1f}`\n"
                    f"⏱ *Candle Time:* {c_time} IST"
                )
                alerts.append(alert_text)

        except Exception as e:
            print(f"Error {sym}: {e}")
            continue

    if alerts:
        msg = f"🚀 *DELTA 15-MIN BREAKOUT ALERT*\n\n" + "\n\n".join(alerts)
        send_telegram(msg)
    else:
        print("No stock met criteria.")

if __name__ == "__main__":
    run_15m_crypto_scanner()
