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

# গ্লোবাল ডিকশনারি ডাটা স্টোর করার জন্য
candles_history = {}

# --- আপনার দেওয়া ফ্রেশ সেশন এবং কুকি ---
AUTH_SESSION = "eeR2zS5eKQ55tLC9GZQg1BRcsi1NAT3xLjFsK1SF"
MY_COOKIE = '_ga=GA1.1.453634495.1773337729; OTCTooltip={%22value%22:false}; sonr={%22value%22:false}; lang=en; __vid1=89f387f95a92729124e9994373142ae3; balance-visible={%22value%22:false}; tabFixed=[%22NZDCHF_otc%22%2C%22AUDCAD%22%2C%22EURJPY%22%2C%22EURGBP%22]; nas=[%22EURNZD_otc%22%2C%22USDARS_otc%22%2C%22USDNGN_otc%22%2C%22USDEGP_otc%22%2C%22USDMXN_otc%22%2C%22USDCOP_otc%22%2C%22USDBDT_otc%22%2C%22NZDJPY_otc%22%2C%22NZDUSD_otc%22%2C%22EURUSD%22%2C%22MCD_otc%22%2C%22USDINR_otc%22%2C%22NZDCAD_otc%22%2C%22PFE_otc%22%2C%22JNJ_otc%22%2C%22USDDZD_otc%22%2C%22ATOUSD_otc%22%2C%22USDJPY%22%2C%22BRLUSD_otc%22%2C%22USDPHP_otc%22%2C%22MSFT_otc%22%2C%22USDIDR_otc%22%2C%22USDPKR_otc%22%2C%22GBPJPY%22%2C%22AXP_otc%22]; activeAccount=live; z=[[%22graph%22%2C2%2C0%2C0%2C0.0833333]]; _ga_L4T5GBPFHJ=GS2.1.s1774718000$o29$g1$t1774718001$j59$l0$h0'

def on_message(ws, message):
    global candles_history
    # Heartbeat response
    if message == '2':
        ws.send('3')
        return
    
    if message.startswith('42'):
        try:
            res = json.loads(message[2:])
            # ক্যান্ডেল অথবা টিক ডাটা চেক করা
            if res[0] in ["candle", "tick"]:
                data = res[1]
                pair = data['s']
                
                if pair not in candles_history:
                    candles_history[pair] = []
                
                c_time = datetime.fromtimestamp(data['t']).strftime('%Y-%m-%d %H:%M:00')
                
                candle = {
                    "pair": pair,
                    "timeframe": "M1",
                    "candle_time": c_time,
                    "epoch": data['t'],
                    "open": str(data['o']),
                    "high": str(data['h']),
                    "low": str(data['l']),
                    "close": str(data['c']),
                    "volume": "0",
                    "color": "green" if float(data['c']) >= float(data['o']) else "red",
                    "created_at": c_time
                }
                
                # যদি একই সময়ের ক্যান্ডেল হয় তবে আপডেট করো, নাহলে নতুন যোগ করো
                if candles_history[pair] and candles_history[pair][-1]['epoch'] == data['t']:
                    candles_history[pair][-1] = candle
                else:
                    candles_history[pair].append(candle)
                
                # মেমোরি বাঁচাতে পেয়ার প্রতি ১০০ ক্যান্ডেলের বেশি রাখবো না
                if len(candles_history[pair]) > 100:
                    candles_history[pair].pop(0)
        except Exception as e:
            pass

def run_ws():
    while True:
        try:
            ws_url = "wss://ws2.market-qx.trade/socket.io/?EIO=3&transport=websocket"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Origin": "https://market-qx.trade",
                "Cookie": MY_COOKIE
            }
            
            ws = websocket.WebSocketApp(
                ws_url, 
                header=headers, 
                on_message=on_message
            )
            
            def on_open(ws):
                print(">>> Server Connected to Quotex WebSocket")
                ws.send('40') # Handshake
                time.sleep(2)
                
                # Authorization payload
                auth_payload = f'42["authorization", {{"session": "{AUTH_SESSION}", "isDemo": 0, "tournamentId": 0}}]'
                ws.send(auth_payload)
                time.sleep(2)
                
                # সব পেয়ার সাবস্ক্রাইব করা
                ws.send('42["subscribe_all"]')
                print(">>> Authorization Sent!")

            ws.on_open = on_open
            # SSL ভেরিফিকেশন ছাড়া কানেক্ট করা (সার্ভারের জন্য নিরাপদ)
            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, ping_interval=20, ping_timeout=10)
            
        except Exception as e:
            print(f">>> Socket Error: {e}. Reconnecting in 5s...")
            time.sleep(5)

@app.route('/Qx/Qx.php')
def get_qx():
    pair = request.args.get('pair', 'USDBDT_otc')
    limit = request.args.get('limit', default=10, type=int)
    
    if pair in candles_history and len(candles_history[pair]) > 0:
        # লেটেস্ট ডাটা সবার উপরে দেখানোর জন্য reverse করা হলো
        raw_data = list(reversed(candles_history[pair]))[:limit]
        
        formatted_data = []
        for index, item in enumerate(raw_data):
            # আপনার দেওয়া স্যাম্পল ফরম্যাট অনুযায়ী id যোগ করা
            c = item.copy()
            c["id"] = str(index + 1)
            formatted_data.append(c)
            
        return jsonify({
            "Owner_Developer": "DARK-X-RAYHAN",
            "Telegram": "@mdrayhan85",
            "success": True,
            "count": len(formatted_data),
            "data": formatted_data
        })
    
    return jsonify({
        "success": False, 
        "message": "Still Syncing... Please make sure your Quotex tab is active in browser."
    }), 404

if __name__ == '__main__':
    # ব্যাকগ্রাউন্ডে সকেট চালানো
    threading.Thread(target=run_ws, daemon=True).start()
    # ফ্ল্যাস্ক সার্ভার স্টার্ট
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
