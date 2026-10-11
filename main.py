import os
import asyncio
from flask import Flask, request, jsonify
from metaapi_cloud_sdk import MetaApi

app = Flask(__name__)

TOKEN = os.environ.get("METAAPI_TOKEN")
ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID")

async def execute_trade(symbol, action, volume, sl, tp):
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

    # Sluit de verbinding en de MetaApi client af om geheugen vrij te maken
    try:
        await connection.close()
        await api.close()
    except Exception:
        pass

    return res

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(silent=True)
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
        
        raw_volume = float(volume)
        # Compound veiligheidsbegrenzer op max 0.10 lot
        final_volume = min(round(raw_volume, 2), 0.10)
        print(f"Ontvangen -> Actie: {action}, Symbool: {symbol}, Volume: {raw_volume} (Aangepast: {final_volume}), SL: {sl}, TP: {tp}")
        
        if not TOKEN or not ACCOUNT_ID:
            return jsonify({"status": "error", "message": "METAAPI credentials ontbreken in Render"}), 500

        # Start een schone event loop per webhook request
        res = asyncio.run(execute_trade(symbol, action, final_volume, sl, tp))
        
        return jsonify({"status": "success", "message": "Order geplaatst", "result": str(res)}), 200
        
    except Exception as e:
        print(f"Fout bij verwerken webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    return "Vantage Trading Bot is actief!", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
