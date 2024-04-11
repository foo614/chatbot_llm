import os
import re
from flask import Flask, request, jsonify, session
import openai
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import uuid

openai.api_key = os.environ["OPENAI_API_KEY"]

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())

ACCOUNT_ID = os.environ["ACCOUNT_ID"]
TWILIO_TOKEN = os.environ["TWILIO_TOKEN"]
TWILIO_NUMBER = os.environ["TWILIO_NUMBER"]

client = Client(ACCOUNT_ID, TWILIO_TOKEN)

@app.route("/")
def home():
    return f"Connected : {os.getenv('OPENAI_API_KEY')}", 200

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"status": 404, "message": "Not Found"}), 404

@app.route('/whatsapp/webhook', methods=['POST'])
def handle_whatsapp_webhook():
    message = request.values['Body']
    from_number = request.values['From']

    if "chat_mode" not in session:
        session["chat_mode"] = "bot"

    if "/switch" in message.lower():
        # Switching logic here if needed
        session["chat_mode"] = 'human' if session["chat_mode"] == 'bot' else 'bot'
        if session["chat_mode"] == 'bot':
            response = "Bot mode is active. Please type /switch to switch to human mode."
        else:
            response = "Human mode is active. Please type /switch to switch to bot mode."
        send_whatsapp_message(from_number, response )
        return "200 OK"
    
    print(session["chat_mode"])
    # only apply openai chat if the mode == BOT
    if session["chat_mode"] == 'bot':
        # Initialize or get the message history from session state
        if "message_history" not in session:
            session["message_history"] = [
                {"role": "assistant", "content": "Good day to you! Welcome to Lux Retreats! Thank you for your interest in our villas 🤩 We have two villas available, The Black Box Villa and The White Box Villa 🏘️ Both villas are conveniently located next to each other. Our clients have the option to rent them individually for small gatherings or book both villas for larger events. Please find the pricing details below"},
                {"role": "system", "content": "calculate and anlayse the total cost in details"},
                {"role": "system", "content": "contact Wendy at 016-3456126 to finalize the details"}
            ]
        message_history = session["message_history"]

        message = re.sub(r'\xa0', ' ', message)  # Replace '\xa0' with space
        message = message.replace('\n\n', '\n') 
        message = re.sub(r'\s+', ' ', message).strip()

        # Add the user's message to the message history
        message_history.append({"role": "user", "content": message})

        response = openai.ChatCompletion.create(
            model = 'gpt-3.5-turbo-1106',
            temperature= 0.3,  # Adjust temperature as needed
            messages = message_history
        )
        # Format the ChatGPT response
        chat_response = response["choices"][0]["message"]["content"]

        # Add the ChatGPT response to the message history
        message_history.append({"role": "assistant", "content": chat_response})
        print('chat count' + str(len(message_history)))
        print(message_history)
        session["message_history"] = message_history
        send_whatsapp_message(from_number, chat_response )
        
    return "200 OK"

def send_whatsapp_message(to_number, message):
    client.messages.create(
        from_=TWILIO_NUMBER,
        body=message,
        to=to_number
    )

if __name__ == '__main__':
    app.run(debug=True)
