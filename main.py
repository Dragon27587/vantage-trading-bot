import os
import asyncio
import threading
from flask import Flask, request, jsonify
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

TOKEN = os.environ.get("METAAPI_TOKEN")
ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID")

async def execute_trade_async(symbol, action, volume, sl, tp):
    try:
        api = MetaApi(TOKEN)
        account = await api.metatrader_account_api.get_account(ACCOUNT_ID)
        
        connection = account.get_rpc_connection()
        await connection.connect()
        await connection.wait_synchronized()

        if action.upper() == 'BUY':
            res = await connection.create_market_buy_order(
                symbol=symbol,
                volume=volume,
                stop_loss=sl,
                take_profit=tp
            )
        else:
            res = await connection.create_market_sell_order(
                symbol=symbol,
                volume=volume,
                stop_loss=sl,
                take_profit=tp
            )

        print(f"Trade succesvol geplaatst via MetaApi: {res}")
        await connection.close()
        await api.close()
    except Exception as e:
        print(f"Fout in background trade execution: {str(e)}")

def run_async_trade(symbol, action, volume, sl, tp):
    asyncio.run(execute_trade_async(symbol, action, volume, sl, tp))

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True, silent=True)
        print("Ontvangen payload:", request.data)
        
        if not data:
            return jsonify({"status": "error", "message": "Geen geldige JSON ontvangen"}), 400
            
        action = data.get('action', 'BUY')
        symbol = data.get('symbol', 'BTCUSD')
        
        try:
            volume = float(data.get('volume', 0.01))
        except (TypeError, ValueError):
            volume = 0.01
            
        def safe_float(val):
            if val is None:
                return None
            val_str = str(val).strip()
            if not val_str or "{{" in val_str or val_str.lower() == "na":
                return None
            try:
                return float(val_str)
            except (ValueError, TypeError):
                return None

        sl = safe_float(data.get('sl'))
        tp = safe_float(data.get('tp'))
        
        final_volume = round(float(volume), 2)
        print(f"Ontvangen -> Actie: {action}, Symbool: {symbol}, Volume: {final_volume}, SL: {sl}, TP: {tp}")
        
        if not TOKEN or not ACCOUNT_ID:
            return jsonify({"status": "error", "message": "METAAPI credentials ontbreken in Render"}), 500

        # Start de trade direct in een achtergrond-thread en antwoord onmiddellijk aan TradingView
        threading.Thread(target=run_async_trade, args=(symbol, action, final_volume, sl, tp)).start()
        
        return jsonify({"status": "success", "message": "Webhook ontvangen, trade wordt in achtergrond uitgevoerd"}), 200
        
    except Exception as e:
        print(f"Fout bij verwerken webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    return "Vantage Trading Bot is actief!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
