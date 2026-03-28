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

# --- আপনার দেওয়া লেটেস্ট ডাটা ---
AUTH_SESSION = "eeR2zS5eKQ55tLC9GZQg1BRcsi1NAT3xLjFsK1SF"
MY_COOKIE = "_ga=GA1.1.453634495.1773337729; OTCTooltip={%22value%22:false}; sonr={%22value%22:false}; lang=en; __vid1=89f387f95a92729124e9994373142ae3; balance-visible={%22value%22:false}; tabFixed=[%22NZDCHF_otc%22%2C%22AUDCAD%22%2C%22EURJPY%22%2C%22EURGBP%22]; nas=[%22EURNZD_otc%22%2C%22USDARS_otc%22%2C%22USDNGN_otc%22%2C%22USDEGP_otc%22%2C%22USDMXN_otc%22%2C%22USDCOP_otc%22%2C%22USDBDT_otc%22%2C%22NZDJPY_otc%22%2C%22NZDUSD_otc%22%2C%22EURUSD%22%2C%22MCD_otc%22%2C%22USDINR_otc%22%2C%22NZDCAD_otc%22%2C%22PFE_otc%22%2C%22JNJ_otc%22%2C%22USDDZD_otc%22%2C%22ATOUSD_otc%22%2C%22USDJPY%22%2C%22BRLUSD_otc%22%2C%22USDPHP_otc%22%2C%22MSFT_otc%22%2C%22USDIDR_otc%22%2C%22USDPKR_otc%22%2C%22GBPJPY%22%2C%22AXP_otc%22]; activeAccount=live; z=[[%22graph%22%2C2%2C0%2C0%2C0.4633264]]; _ga_L4T5GBPFHJ=GS2.1.s1774694107$o25$g1$t1774696271$j53$l0$h0"

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
                    "pair": pair,
                    "open": str(data['o']), "high": str(data['h']),
                    "low": str(data['l']), "close": str(data['c']),
                    "color": "green" if float(data['c']) >= float(data['o']) else "red",
                    "epoch": data['t'],
                    "time": datetime.fromtimestamp(data['t']).strftime('%H:%M:%S')
                }
                
                if candles_history[pair] and candles_history[pair][-1]['epoch'] == data['t']:
                    candles_history[pair][-1] = candle
                else:
                    candles_history[pair].append(candle)
                
                if len(candles_history[pair]) > 50: candles_history[pair].pop(0)
        except: pass

def run_ws():
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
                ws.send('40')
                time.sleep(1)
                auth_data = f'42["authorization", {{"session": "{AUTH_SESSION}", "isDemo": 0, "tournamentId": 0}}]'
                ws.send(auth_data)
                time.sleep(1)
                ws.send('42["subscribe_all"]')
                print("--- DARK-X-RAYHAN SYNC STARTED ---")
            ws.on_open = on_open
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_interval=15)
        except: time.sleep(5)

@app.route('/')
def health(): return "<h1>DARK-X-RAYHAN API IS ACTIVE</h1>"

@app.route('/Qx/Qx.php')
def get_qx():
    pair = request.args.get('pair', 'USDBDT_otc')
    limit = request.args.get('limit', default=10, type=int)
    if pair in candles_history:
        return jsonify({"success": True, "data": list(reversed(candles_history[pair]))[:limit]})
    return jsonify({"success": False, "message": "Syncing... Please wait a few seconds."}), 404

if __name__ == '__main__':
    threading.Thread(target=run_ws, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
