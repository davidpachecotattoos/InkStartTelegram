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
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://inkstarttelegram.onrender.com/webhook")
MY_MONITOR_CHAT_ID = os.environ.get("MONITOR_CHAT_ID")
BOT_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

openai.api_key = OPENAI_API_KEY

@app.route("/")
def home():
    return "InkStart Telegram attivo!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data or "message" not in data:
        return "ok", 200

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    user_lang = msg["from"].get("language_code", "it")
    lang_map = {"it": "italian", "en": "english", "es": "spanish"}
    user_language = lang_map.get(user_lang, "italian")
    first_name = msg["from"].get("first_name", "Utente")

    if "text" in msg:
        user_text = msg["text"]
        notify_admin(f"🧵 Nuovo messaggio da {first_name} ({user_language}):\n{user_text}")
        reply = ask_gpt(user_text, user_language)
        human_delay(reply)
        send_message(chat_id, reply)

    elif "photo" in msg:
        notify_admin(f"📸 Immagine ricevuta da {first_name} ({user_language})")
        send_message(chat_id, "Bella immagine! Vuoi raccontarmi cosa rappresenta per te?")

    elif "video" in msg:
        notify_admin(f"🎥 Video ricevuto da {first_name} ({user_language})")
        send_message(chat_id, "Video interessante! C’è un significato dietro che vuoi condividere?")

    elif "voice" in msg:
        file_id = msg["voice"]["file_id"]
        transcription = transcribe_voice(file_id)
        notify_admin(f"🎤 Vocale da {first_name} ({user_language}):\n{transcription}")
        send_message(chat_id, f"Ho ascoltato il vocale! Ecco cosa ho capito:\n{transcription}")

    else:
        notify_admin(f"📦 Altro contenuto da {first_name} ({user_language})")
        send_message(chat_id, "Ricevuto! Dimmi pure la tua idea.")

    return "ok", 200

def send_message(chat_id, text):
    if len(text) > 250:
        text = text[:247] + "..."
    requests.post(f"{BOT_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def notify_admin(message):
    if MY_MONITOR_CHAT_ID:
        send_message(MY_MONITOR_CHAT_ID, message)

def human_delay(text):
    time.sleep(random.uniform(2, 5) if len(text) < 100 else random.uniform(5, 10))

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

        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompts[language]},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Errore GPT: {str(e)}"

def transcribe_voice(file_id):
    try:
        file_info = requests.get(f"{BOT_URL}/getFile?file_id={file_id}").json()
        file_path = file_info['result']['file_path']
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

        response = requests.get(file_url)
        temp_path = "/tmp/audio.ogg"
        with open(temp_path, "wb") as f:
            f.write(response.content)

        with open(temp_path, "rb") as audio_file:
            transcript = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text.strip()
    except Exception as e:
        return f"[Errore trascrizione vocale: {str(e)}]"

def set_webhook():
    try:
        r = requests.get(f"{BOT_URL}/setWebhook?url={WEBHOOK_URL}")
        print("✅ Webhook impostato:", r.json())
    except Exception as e:
        print("❌ Errore nel set webhook:", e)

if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=True)
