import os
import asyncio
from flask import Flask, request, jsonify
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

TOKEN = os.environ.get("METAAPI_TOKEN")
ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID")

async def place_order_async(symbol, action, volume, sl=None, tp=None):
    api = MetaApi(TOKEN)
    account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
    connection = account.get_rpc_connection()
    await connection.connect()
    await connection.wait_synchronized()

    if action.upper() == 'BUY':
        res = await connection.create_market_buy_order(
            symbol=symbol,
            volume=float(volume),
            stop_loss=float(sl) if sl else None,
            take_profit=float(tp) if tp else None
        )
    else:
        res = await connection.create_market_sell_order(
            symbol=symbol,
            volume=float(volume),
            stop_loss=float(sl) if sl else None,
            take_profit=float(tp) if tp else None
        )
    return res

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "error", "message": "Geen geldige JSON ontvangen"}), 400
            
        action = data.get('action')
        symbol = data.get('symbol', 'BTCUSD')
        
        try:
            volume = float(data.get('volume', 0.01))
        except (TypeError, ValueError):
            volume = 0.01
            
        sl_raw = data.get('sl')
        tp_raw = data.get('tp')
        
        sl = float(sl_raw) if sl_raw and str(sl_raw).lower() != 'na' else None
        tp = float(tp_raw) if tp_raw and str(tp_raw).lower() != 'na' else None
        
        print(f"Ontvangen -> Actie: {action}, Symbool: {symbol}, Volume: {volume}, SL: {sl}, TP: {tp}")
        
        # Voer hier eventueel je MetaApi / order-functie uit
        # res = asyncio.run(place_order_async(symbol, action, volume, sl, tp))
        
        return jsonify({"status": "success", "message": "Webhook verwerkt"}), 200
        
    except Exception as e:
        print(f"Fout bij verwerken webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    return "Vantage Trading Bot is actief!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
