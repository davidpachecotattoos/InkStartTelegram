
from flask import Flask, request
import requests
import os

app = Flask(__name__)
TOKEN = os.environ.get("TELEGRAM_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

@app.route("/")
def home():
    return "Bot attivo!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        response = {
            "chat_id": chat_id,
            "text": "Ciao! Grazie per il tuo messaggio. Raccontami la tua idea!"
        }
        requests.post(URL, json=response)
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
