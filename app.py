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

candles_history = {}

def on_message(ws, message):
    global candles_history
    if message == '2':
        ws.send('3')
        return
    if message.startswith('42'):
        try:
            res = json.loads(message[2:])
            if res[0] in ["candle", "tick"]:
                data = res[1]
                pair = data['s']
                if pair not in candles_history: candles_history[pair] = []
                
                candle = {
                    "id": str(len(candles_history[pair]) + 1),
                    "pair": pair,
                    "open": str(data['o']), "high": str(data['h']),
                    "low": str(data['l']), "close": str(data['c']),
                    "color": "green" if data['c'] >= data['o'] else "red",
                    "epoch": data['t'],
                    "candle_time": datetime.fromtimestamp(data['t']).strftime('%Y-%m-%d %H:%M:%S')
                }
                
                if candles_history[pair] and candles_history[pair][-1]['epoch'] == candle['epoch']:
                    candles_history[pair][-1] = candle
                else:
                    candles_history[pair].append(candle)
                
                if len(candles_history[pair]) > 200: candles_history[pair].pop(0)
        except: pass

def run_ws():
    # রেন্ডারে হোস্ট করার পর এখানে আপনার ফ্রেশ কুকি এবং সেশন আপডেট করতে হবে
    MY_COOKIE = "_ga=GA1.1.453634495.1773337729; lang=en; activeAccount=live;"
    AUTH_SESSION = "আপনার_সেশন_আইডি" 

    while True:
        try:
            ws_url = "wss://ws2.market-qx.trade/socket.io/?EIO=3&transport=websocket"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
                "Origin": "https://market-qx.trade",
                "Cookie": MY_COOKIE
            }
            ws = websocket.WebSocketApp(ws_url, header=headers, on_message=on_message)
            def on_open(ws):
                ws.send('40')
                time.sleep(1)
                ws.send(f'42["authorization", {{"session": "{AUTH_SESSION}"}}]')
                time.sleep(1)
                ws.send('42["subscribe_all"]')
                print("--- SERVER CONNECTED TO QUOTEX ---")
            ws.on_open = on_open
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_interval=5)
        except: time.sleep(5)

@app.route('/Qx/Qx.php')
def get_qx():
    pair = request.args.get('pair', 'USDBDT_otc')
    limit = request.args.get('limit', default=10, type=int)
    if pair in candles_history:
        return jsonify({
            "Owner_Developer": "DARK-X-RAYHAN",
            "success": True,
            "data": list(reversed(candles_history[pair][-limit:]))
        })
    return jsonify({"success": False, "message": "Syncing on Server..."}), 404

if __name__ == '__main__':
    threading.Thread(target=run_ws, daemon=True).start()
    # রেন্ডার বা হোস্টিং সার্ভারের পোর্ট ধরার জন্য এটি জরুরি
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
