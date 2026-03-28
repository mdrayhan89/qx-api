import json
import threading
import time
import os
import websocket
import ssl
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

# গ্লোবাল ভেরিয়েবল যেখানে ক্যান্ডেল ডেটা জমা থাকবে
candles_history = {}

def get_candle_color(o, c):
    return "green" if float(c) >= float(o) else "red"

def on_message(ws, message):
    global candles_history
    if message == '2': # Heartbeat
        ws.send('3')
        return

    if message.startswith('42'):
        try:
            msg_data = json.loads(message[2:])
            event = msg_data[0]
            data = msg_data[1]

            if event in ["candle", "tick"]:
                symbol = data.get('s')
                if symbol:
                    if symbol not in candles_history:
                        candles_history[symbol] = []
                    
                    o, h, l, c = data['o'], data['h'], data['l'], data['c']
                    t = int(data['t'])
                    f_time = datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')

                    candle_obj = {
                        "pair": symbol,
                        "open": str(o),
                        "high": str(h),
                        "low": str(l),
                        "close": str(c),
                        "color": get_candle_color(o, c),
                        "epoch": t,
                        "time": f_time
                    }

                    # একই ক্যান্ডেল হলে আপডেট করো, নতুন হলে অ্যাপেন্ড করো
                    if candles_history[symbol] and candles_history[symbol][-1]['epoch'] == t:
                        candles_history[symbol][-1] = candle_obj
                    else:
                        candles_history[symbol].append(candle_obj)
                    
                    # মেমোরি সেভ করতে লাস্ট ১০০ ক্যান্ডেল রাখো
                    if len(candles_history[symbol]) > 100:
                        candles_history[symbol].pop(0)
        except:
            pass

def run_ws():
    # --- আপনার দেওয়া লেটেস্ট সেশন আইডি ---
    AUTH_SESSION = "eeR2zS5eKQ55tLC9GZQg1BRcsi1NAT3xLjFsK1SF"
    # আপনার ব্রাউজার থেকে নেওয়া ফুল কুকি এখানে আপডেট করে দিন (জরুরি)
    MY_COOKIE = "_ga=GA1.1.453634495.1773337729; lang=en; activeAccount=live;"

    while True:
        try:
            ws_url = "wss://ws2.market-qx.trade/socket.io/?EIO=3&transport=websocket"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Origin": "https://market-qx.trade",
                "Cookie": MY_COOKIE
            }
            
            ws = websocket.WebSocketApp(ws_url, header=headers, on_message=on_message)

            def on_open(ws):
                ws.send('40') # Handshake Start
                time.sleep(1)
                # অথোরাইজেশন মেসেজ
                auth_payload = f'42["authorization", {{"session": "{AUTH_SESSION}", "isDemo": 0, "tournamentId": 0}}]'
                ws.send(auth_payload)
                time.sleep(1)
                ws.send('42["subscribe_all"]')
                print("--- DARK-X-RAYHAN API: SERVER CONNECTED AND AUTHORIZED ---")

            ws.on_open = on_open
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_interval=5)
        except Exception as e:
            print(f"Connection lost. Reconnecting... Error: {e}")
            time.sleep(5)

@app.route('/')
def home():
    return "DARK-X-RAYHAN API IS LIVE"

@app.route('/Qx/Qx.php')
def get_qx_data():
    pair = request.args.get('pair', 'USDBDT_otc')
    limit = request.args.get('limit', default=10, type=int)
    
    if pair in candles_history:
        data = list(reversed(candles_history[pair]))[:limit]
        return jsonify({
            "Owner": "DARK-X-RAYHAN",
            "success": True,
            "pair": pair,
            "data": data
        })
    return jsonify({
        "success": False, 
        "message": "Syncing on server, please wait...",
        "active_pairs": list(candles_history.keys())
    }), 404

if __name__ == '__main__':
    # সকেট আলাদা থ্রেডে চালানো
    threading.Thread(target=run_ws, daemon=True).start()
    # হোস্টিং পোর্টে রান করা
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
