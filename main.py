from flask import Flask, request
import requests
import os
from openai import OpenAI
from datetime import datetime
import pytz
import time
import random
import json
from PIL import Image

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://inkstarttelegram.onrender.com/webhook")
MY_MONITOR_CHAT_ID = os.environ.get("MONITOR_CHAT_ID")
BOT_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

client = OpenAI(api_key=OPENAI_API_KEY)

STATE_FILE = "user_states.json"
user_states = {}

# Load state from file if exists
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        try:
            user_states = json.load(f)
        except:
            user_states = {}

@app.route("/")
def home():
    return "InkStart Telegram attivo!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if not data or "message" not in data:
        return "ok", 200

    msg = data["message"]
    chat_id = str(msg["chat"]["id"])
    user_lang = msg["from"].get("language_code", "it")
    lang_map = {"it": "italian", "en": "english", "es": "spanish"}
    user_language = lang_map.get(user_lang, "italian")
    first_name = msg["from"].get("first_name", "Utente")

    user_states[chat_id] = user_states.get(chat_id, 0) + 1
    save_states()

    if "text" in msg:
        user_text = msg["text"]
        notify_admin(f"🧵 Nuovo messaggio da {first_name} ({user_language}):\n{user_text}")
        if user_states[chat_id] <= 9:
            reply = ask_gpt(user_text, user_language, user_states[chat_id])
            human_delay(reply)
            send_message(chat_id, reply)
        elif user_states[chat_id] == 10:
            send_message(chat_id, "Per fissare la videochiamata clicca qui: https://calendly.com/davidpachecotattoos/30min")

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
        if user_states[chat_id] <= 9:
            reply = ask_gpt(transcription, user_language, user_states[chat_id])
            human_delay(reply)
            send_message(chat_id, reply)
        elif user_states[chat_id] == 10:
            send_message(chat_id, "Per fissare la videochiamata clicca qui: https://calendly.com/davidpachecotattoos/30min")

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
        requests.post(f"{BOT_URL}/sendMessage", json={
            "chat_id": MY_MONITOR_CHAT_ID,
            "text": message
        })

def human_delay(text):
    time.sleep(random.uniform(2, 5) if len(text) < 100 else random.uniform(5, 10))

def ask_gpt(user_message, language="italian", step=1):
    try:
        milan_time = datetime.now(pytz.timezone("Europe/Rome"))
        if milan_time.hour < 11 or milan_time.hour >= 19:
            return "Hey! Ti rispondo tra le 11:00 e le 19:00 — così riesco a seguirti bene. A dopo!"

        prompts = {
            "italian": f"""
Parla sempre in prima persona, come se fossi David, il tatuatore di Milano (True Blue Tattoo Parlour, Viale Zara 114, M5 Marche). Rispondi con stile naturale e diretto, come in una chat su WhatsApp. 
Non dire mai che sei un bot o assistente.
Se ricevi un vocale trascritto, rispondi al suo contenuto come se fosse parte della conversazione e poi prosegui nel flusso con la prossima domanda utile.
Evita di ripresentarti più volte: dai continuità.

Se questo è il messaggio n° {step}, continua con la prossima domanda.
Includi alla fine, solo se è il nono messaggio: "Per fissare la videochiamata clicca qui: https://calendly.com/davidpachecotattoos/30min"
""",
            "english": f"You are David, a tattoo artist in Milan. Speak naturally like in a WhatsApp chat. Never say you're a bot. Avoid repeating your intro. If you receive a voice message transcript, respond to it and continue the conversation. Step {step}. If step 9, end by inviting to book a call: https://calendly.com/davidpachecotattoos/30min",
            "spanish": f"Eres David, tatuador en Milán. Habla como en un chat natural. Nunca digas que eres un bot. Evita presentarte varias veces. Si recibes una transcripción de audio, respóndela y sigue la conversación. Paso {step}. Si es el paso 9, termina con: Reserva aquí: https://calendly.com/davidpachecotattoos/30min"
        }

        response = client.chat.completions.create(
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
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        return transcript.text.strip()
    except Exception as e:
        return f"[Errore trascrizione vocale: {str(e)}]"

# def image_analysis(file_id):
#     try:
#         file_info = requests.get(f"{BOT_URL}/getFile?file_id={file_id}").json()
#         file_path = file_info['result']['file_path']
#         file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
#         response = requests.get(file_url)
#         temp_path = "/tmp/image.jpg"
#         with open(temp_path, "wb") as f:
#             f.write(response.content)
#         image = Image.open(temp_path)
#         # Analisi visiva futura qui...
#     except Exception as e:
#         print("Errore analisi immagine:", e)

def save_states():
    with open(STATE_FILE, "w") as f:
        json.dump(user_states, f)

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
