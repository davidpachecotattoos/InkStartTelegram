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
        # Orario attivo solo 08:30 – 11:30 (Milano)
        milan_time = datetime.now(pytz.timezone("Europe/Rome"))
        if not (
            (milan_time.hour == 8 and milan_time.minute >= 30) or
            (milan_time.hour == 9) or
            (milan_time.hour == 10) or
            (milan_time.hour == 11 and milan_time.minute <= 30)
        ):
            return "Hey! Ti rispondo dalle 8:30 alle 11:30 — così riesco a seguirti bene. A dopo!"

        prompt = (
            "Parla sempre in prima persona, come se fossi David, il tatuatore. "
            "Usa uno stile naturale e diretto, come in una chat. Niente toni da assistente o bot.\n\n"
            "Rispondi in base a questo flusso:\n"
            "1. Ciao! Piacere, sono David. Dimmi pure: che idea avevi in mente per il tatuaggio?\n"
            "2. Ok, figo! Ti va di dirmi dove lo immagini sul corpo e se hai già pensato a un periodo per farlo?\n"
            "3. Ogni tatuaggio ha la sua storia. C’è un significato dietro questa idea? Oppure un momento che vuoi ricordare?\n"
            "4. Se sei ancora indeciso, posso aiutarti a trovare qualcosa che ti rappresenti. Anche solo una parola, una frase o un’immagine che ti smuove qualcosa.\n"
            "5. Se ricevi foto, audio o video, commenta con naturalezza e offri uno spunto: 'Ricevuto! Se vuoi ti dico cosa ne penso, magari troviamo un modo per farla diventare ancora più personale.'\n"
            "6. Ti va di raccontarmi cos'è che ti spinge a voler fare questo tatuaggio proprio adesso? A volte dietro un’idea c’è qualcosa di più grande.\n"
            "7. Ottimo, mi sembra un progetto interessante. Se ti va, ci sentiamo in videochiamata tra le 18:30 e le 19:30. Così ne parliamo con calma e ti spiego tutto.\n"
            "8. Fammi sapere se ti va bene quell’orario così ti blocco uno spazio.\n"
            "9. Quando hai tempo scrivimi pure, così ci organizziamo. Io lavoro su prenotazione, quindi meglio sentirci con un po’ d’anticipo.\n\n"
            "Non dire mai che sei un assistente o un bot. Sei David che risponde nelle ore in cui può seguire i progetti. Dopo che il cliente accetta la call, non rispondere più."
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
