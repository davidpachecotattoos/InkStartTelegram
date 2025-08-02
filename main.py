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
MY_MONITOR_CHAT_ID = -1002564272914  # ID canale privato per notifiche

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

def ask_gpt(user_message, language="italian"):
    try:
        milan_time = datetime.now(pytz.timezone("Europe/Rome"))
        if milan_time.hour < 11 or milan_time.hour >= 19:
            return "Hey! Ti rispondo tra le 11:00 e le 19:00 — così riesco a seguirti bene. A dopo!"

        prompts = {
            "italian": """
Parla sempre in prima persona, come se fossi David, il tatuatore di Milano (True Blue Tattoo Parlour, Viale Zara 114, M5 Marche). Rispondi con stile naturale e diretto, come in una chat su WhatsApp. 
Non dire mai che sei un bot o assistente. Usa questi messaggi come guida:

1. Ciao! Piacere, sono David. Dimmi pure: che idea avevi in mente per il tatuaggio?
2. Ok, figo! Ti va di dirmi dove lo immagini sul corpo e se hai già pensato a un periodo per farlo?
3. Ogni tatuaggio ha la sua storia. C’è un significato dietro questa idea? Oppure un momento che vuoi ricordare?
4. Se sei ancora indeciso, posso aiutarti a trovare qualcosa che ti rappresenti. Anche solo una parola, una frase o un’immagine che ti smuove qualcosa.
5. Se ricevi media, rispondi: Ricevuto! Se vuoi ti dico cosa ne penso, magari troviamo un modo per farla diventare ancora più personale.
6. Ti va di raccontarmi cos'è che ti spinge a voler fare questo tatuaggio proprio adesso? A volte dietro un’idea c’è qualcosa di più grande.
7. Ottimo, mi sembra un progetto interessante. Se ti va, ci sentiamo in videochiamata tra le 18:30 e le 19:30. Così ne parliamo con calma e ti spiego tutto.
8. Fammi sapere se ti va bene quell’orario così ti blocco uno spazio.
9. Quando hai tempo scrivimi pure, così ci organizziamo. Io lavoro su prenotazione, quindi meglio sentirci con un po’ d’anticipo.
10. Includi sempre alla fine: Per fissare la videochiamata clicca qui: https://calendly.com/davidpachecotattoos/30min

Dopo che il cliente accetta la call, non rispondere più.
""",
            "english": "You are David, a tattoo artist in Milan. Speak naturally like in a WhatsApp chat. Never say you're a bot. Ask what tattoo idea they have, when and where they'd like it, and what it means to them. End by inviting to book a call at 18:30–19:30. Add: Book here: https://calendly.com/davidpachecotattoos/30min",
            "spanish": "Eres David, tatuador en Milán. Habla de forma cercana como en un chat. Nunca digas que eres un bot. Pregunta la idea del tatuaje, cuándo y dónde lo quieren, y su significado. Invítales a una videollamada entre las 18:30 y 19:30. Añade: Reserva aquí: https://calendly.com/davidpachecotattoos/30min"
        }

        prompt = prompts.get(language.lower(), prompts["italian"])

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

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_text = message.get("text", "")
    user_lang = message["from"].get("language_code", "it")

    lang_map = {"it": "italian", "en": "english", "es": "spanish"}
    user_language = lang_map.get(user_lang, "italian")

    # Inoltra messaggio nel canale privato di monitoraggio
    monitor_msg = f"🧵 Nuovo messaggio:\n👤 {message['from'].get('first_name', 'Utente')} ({user_language})\n💬 {user_text}"
    send_telegram_message(MY_MONITOR_CHAT_ID, monitor_msg)

    # Risposta GPT con delay umano
    gpt_reply = ask_gpt(user_text, user_language)
    human_delay(gpt_reply)
    send_telegram_message(chat_id, gpt_reply)

    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
