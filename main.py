from flask import Flask, request
import requests
import os
import openai

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# Funzione per inviare messaggio al bot Telegram
def send_telegram_message(chat_id, message):
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    requests.post(TELEGRAM_URL, json=payload)

# Funzione aggiornata per chiamare GPT-4 con openai >=1.0.0
def ask_gpt(user_message):
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sei InkStart, un assistente personale che aiuta i clienti a descrivere la loro idea di tatuaggio per poi guidarli alla prenotazione."},
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
