from flask import Flask, request
import requests
import os
import openai
from datetime import datetime
import pytz

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

def send_telegram_message(chat_id, message):
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    requests.post(TELEGRAM_URL, json=payload)

def ask_gpt(user_message):
    try:
        # Orario attivo solo 08:30 – 11:30 (Milano time)
        milan_time = datetime.now(pytz.timezone("Europe/Rome"))
        if not (
            (milan_time.hour == 8 and milan_time.minute >= 30) or
            (milan_time.hour == 9) or
            (milan_time.hour == 10) or
            (milan_time.hour == 11 and milan_time.minute <= 30)
        ):
            return "Grazie per il tuo messaggio! Ti risponderò tra le 08:30 e le 11:30. A presto!"

        prompt = (
            "Agisci come InkStart, l'assistente personale di David, tatuatore esperto che lavora presso True Blue Tattoo Parlour, in Viale Zara 114 – Milano "
            "(a 2 minuti dalla fermata metro M5 – Marche). Riceve solo su appuntamento da lunedì a sabato, dalle 11:00 alle 19:00.\n\n"
            "Accogli ogni nuovo messaggio in modo cordiale, professionale e personalizzato, usando il nome dell’utente (se disponibile) e rispondendo nella lingua usata dal cliente "
            "(italiano, spagnolo o inglese).\n\n"
            "Il tuo obiettivo è capire se il cliente è in target, ponendo domande chiare ma gentili su:\n"
            "- Cosa vuole tatuarsi\n"
            "- Dove lo vuole fare (zona del corpo)\n"
            "- Quando vorrebbe farlo\n"
            "- Perché ha scelto quell’idea (significato)\n\n"
            "Se l’idea è vaga, aiuta con spunti creativi. Se ricevi foto, video o audio, interpreta in modo intelligente. "
            "Guida la conversazione (massimo 10 messaggi) verso una richiesta di appuntamento in videochiamata tra le 18:30 e le 19:30. "
            "Quando il cliente è pronto, rispondi: 'Perfetto! Ti riserverò uno spazio per parlarti di persona tra le 18:30 e le 19:30. Fammi sapere se ti va bene!' "
            "Dopo questa risposta, concludi il tuo compito."
        )

        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ]
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Errore GPT: {str(e)}"

@app.route("/")
def home():
    return "InkStart Telegram attivo!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if data is None or "message" not in data:
        return "no data", 400

    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"].get("text", "")

    gpt_reply = ask_gpt(user_text)
    send_telegram_message(chat_id, gpt_reply)

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
