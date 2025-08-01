from flask import Flask, request
import requests
import os
import openai
from datetime import datetime
import pytz

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
openai.api_key = OPENAI_API_KEY

# Prompt personalizzato InkStart
BASE_PROMPT = (
    "Sei InkStart, assistente digitale di David, tatuatore professionista. "
    "Il tuo compito è accogliere con energia e gentilezza chi ti scrive, ascoltare la richiesta e rispondere solo negli orari 8-20. "
    "Rispondi sempre in modo umano e professionale, aiutando il potenziale cliente a chiarire la propria idea. "
    "Il tuo obiettivo è portare la conversazione verso un incontro diretto o una chat personale con David, senza mai forzare, "
    "ma suggerendo che il modo migliore per proseguire è parlarne direttamente con lui. "
    "Sii pratico, mai troppo lungo, e chiudi sempre offrendo la possibilità di fissare una chiacchierata diretta. "
    "Se ti scrivono fuori orario, spiega gentilmente che risponderai nelle fasce 8-20."
)

# Fuso orario Italia
tz = pytz.timezone('Europe/Rome')

@app.route("/")
def home():
    return "Bot InkStart attivo!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_message = data["message"]["text"]

        # Orario attuale in Italia
        now = datetime.now(tz)
        hour = now.hour

        if 8 <= hour < 20:
            # Risposta GPT normale
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": BASE_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=400,
                temperature=0.5,
            )
            gpt_reply = response.choices[0].message.content.strip()
        else:
            # Risposta fuori orario
            gpt_reply = (
                "Ciao! Grazie per il tuo messaggio. "
                "Rispondo attivamente dalle 8:00 alle 20:00. "
                "Ti scrivo appena torno operativo!"
            )

        # Invia la risposta su Telegram
        payload = {
            "chat_id": chat_id,
            "text": gpt_reply
        }
        requests.post(URL, json=payload)

    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
