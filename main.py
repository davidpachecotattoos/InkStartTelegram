from flask import Flask, request
import requests
import os
import openai
from datetime import datetime
import pytz
import time
import random

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

# 🔐 Sostituisci questo con l'ID reale del tuo canale
MY_MONITOR_CHAT_ID = -1001234567890

def send_telegram_message(chat_id, message):
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    requests.post(TELEGRAM_URL, json=payload)

def human_delay(reply_text):
    length = len(reply_text)
    if length < 100:
        time.sleep(random.uniform(2, 5))
    else:
        time.sleep(random.uniform(5, 10))

def ask_gpt(user_message):
    try:
        # Orario attivo: 11:00 – 19:00 (fuso orario Milano)
        milan_time = datetime.now(pytz.timezone("Europe/Rome"))
        hour = milan_time.hour
        if not (11 <= hour <= 19):
            return "Hey! Ti rispondo tra le 11:00 e le 19:00 — così riesco a seguirti bene. A dopo!"

        # Rilevamento lingua
        if any(x in user_message.lower() for x in ["hola", "tatuaje", "quiero", "gracias"]):
            lang = "spanish"
        elif any(x in user_message.lower() for x in ["tattoo", "hi", "please", "want"]):
            lang = "english"
        else:
            lang = "italian"

        # Prompt GPT in 3 lingue
        prompt = {
            "italian": (
                "Parla sempre in prima persona, come se fossi David, il tatuatore. "
                "Usa uno stile naturale e diretto, come in una chat Telegram. "
                "Evita toni da bot o da assistente. Rispondi seguendo questo flusso:\n"
                "1. Ciao! Piacere, sono David. Dimmi pure: che idea avevi in mente per il tatuaggio?\n"
                "2. Ok, figo! Ti va di dirmi dove lo immagini sul corpo e se hai già pensato a un periodo per farlo?\n"
                "3. Ogni tatuaggio ha la sua storia. C’è un significato dietro questa idea? Oppure un momento che vuoi ricordare?\n"
                "4. Se sei ancora indeciso, posso aiutarti a trovare qualcosa che ti rappresenti. Anche solo una parola, una frase o un’immagine che ti smuove qualcosa.\n"
                "5. Se ricevi foto, audio o video, commenta con naturalezza e offri uno spunto: 'Ricevuto! Se vuoi ti dico cosa ne penso, magari troviamo un modo per farla diventare ancora più personale.'\n"
                "6. Ti va di raccontarmi cos'è che ti spinge a voler fare questo tatuaggio proprio adesso? A volte dietro un’idea c’è qualcosa di più grande.\n"
                "7. Ottimo, mi sembra un progetto interessante. Se ti va, ci sentiamo in videochiamata tra le 18:30 e le 19:30. Così ne parliamo con calma e ti spiego tutto.\n"
                "8. Fammi sapere se ti va bene quell’orario così ti blocco uno spazio: https://cal.com/davidpacheco/tattoo\n"
                "9. Quando hai tempo scrivimi pure, così ci organizziamo. Io lavoro su prenotazione, quindi meglio sentirci con un po’ d’anticipo.\n\n"
                "Non dire mai che sei un assistente. Sei David. Dopo che il cliente accetta la call, non rispondere più."
            ),
            "english": (
                "Speak as if you were David, the tattoo artist in Milan. First person, natural, Telegram-style. "
                "Avoid sounding like a bot. Ask about the idea, placement, meaning, timing. Give input if needed. "
                "End by suggesting a video call between 6:30pm–7:30pm and send this link: https://cal.com/davidpacheco/tattoo. "
                "After call is confirmed, stop replying."
            ),
            "spanish": (
                "Habla como si fueras David, el tatuador en Milán. Estilo natural, directo, como si chatearas. "
                "Haz preguntas sobre la idea, zona del cuerpo, el por qué. Da sugerencias si hace falta. "
                "Termina proponiendo una videollamada entre las 18:30 y las 19:30 con este link: https://cal.com/davidpacheco/tattoo. "
                "Después de confirmar, no respondas más."
            )
        }

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt[lang]},
                {"role": "user", "content": user_message}
            ]
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Errore GPT: {str(e)}"

@app.route("/")
def home():
    return "InkStart attivo!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if data is None or "message" not in data:
        return "no data", 400

    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"].get("text", "")
    user_name = data["message"]["from"].get("first_name", "Utente")

    # Inoltro messaggio al canale privato
    requests.post(TELEGRAM_URL, json={
        "chat_id": MY_MONITOR_CHAT_ID,
        "text": f"✉️ {user_name} ha scritto:\n{user_text}"
    })

    # Risposta GPT
    gpt_reply = ask_gpt(user_text)

    # Ritardo simulato (risposte brevi/lunghe)
    human_delay(gpt_reply)

    # Invia risposta
    send_telegram_message(chat_id, gpt_reply)
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
