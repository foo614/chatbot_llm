import os
import sys

from flask import Flask, request
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
import requests
import constants

import openai
from langchain.chains import ConversationalRetrievalChain, RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.indexes import VectorstoreIndexCreator
from langchain.indexes.vectorstore import VectorStoreIndexWrapper
from langchain.llms import OpenAI
from langchain.vectorstores import Chroma

os.environ["OPENAI_API_KEY"] = constants.APIKEY

app = Flask(__name__)

ACCOUNT_ID = 'ACb800f6cbfa419dda0fdea370ee91b0c8'
TWILIO_TOKEN = 'bc57092f2a6249b5c379ee0786f59e2c'
TWILIO_NUMBER = 'whatsapp:+14155238886'
# ACCOUNT_ID = '38ffdbe01da3e2a46d2c074aeb7083c6'

client = Client(ACCOUNT_ID, TWILIO_TOKEN)

chat_history = []
# Enable to save to disk & reuse the model (for repeated queries on the same data)
PERSIST = False

query = None
if len(sys.argv) > 1:
  query = sys.argv[1]

if PERSIST and os.path.exists("persist"):
  print("Reusing index...\n")
  vectorstore = Chroma(persist_directory="persist", embedding_function=OpenAIEmbeddings())
  index = VectorStoreIndexWrapper(vectorstore=vectorstore)
else:
  #loader = TextLoader("data/data.txt") # Use this line if you only need data.txt
  loader = DirectoryLoader("data/")
  if PERSIST:
    index = VectorstoreIndexCreator(vectorstore_kwargs={"persist_directory":"persist"}).from_loaders([loader])
  else:
    index = VectorstoreIndexCreator().from_loaders([loader])

chain = ConversationalRetrievalChain.from_llm(
  llm=ChatOpenAI(model="gpt-3.5-turbo"),
  retriever=index.vectorstore.as_retriever(search_kwargs={"k": 1}),
)

global active

active = True
@app.route('/whatsapp/webhook', methods=['POST'])
def handle_whatsapp_webhook():
    global active

    message = request.values['Body']
    response = ""

    if "/switch" in message.lower():
        active = not active
        text = "BOT" if active else "AGENT"
        response = f"Switching to {text} mode."
    elif active:
        result = chain({"question": message, "chat_history": chat_history})
        response = result['answer']
        chat_history.append((query, response))
    else:
        response = "ChatGPT service is currently deactivated."

    send_whatsapp_message(request.values['From'], response)

    # Return a success response to Twilio
    return "200 OK"

def check_if_agent_message(message):
    # Implement your logic to check if the message is from an agent
    # For example, you could check for specific keywords or patterns in the message
    return "agent" in message.lower()

def send_whatsapp_message(to_number, message):
    account_sid = ACCOUNT_ID
    auth_token = TWILIO_TOKEN
    client = Client(account_sid, auth_token)
    message1 = client.messages.create(
            from_='whatsapp:+14155238886',
            body=message,
            to=to_number
            # to='whatsapp:+60187912826'
        )
    print(message1.sid)

def get_stock_price(stock_symbol):
   url = f"http://api.marketstack.com/v1/tickers/{stock_symbol}/eod"
   params = {
       "access_key": ACCOUNT_ID
   }
   response = requests.get(url, params=params)
   data = response.json()
   print(data["data"]['eod'][0]['close'])
   return data["data"]['eod'][0]['close']

def get_response_message(message):
    # url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=AIzaSyDaFcyEmqJEn_NMNyAUkztPHOxgYL-uSHk"
    headers = {
    'Content-Type': 'application/json',
    }

    params = {
        'key': 'AIzaSyDaFcyEmqJEn_NMNyAUkztPHOxgYL-uSHk',
    }

    json_data = {
        'contents': [
            {
                'parts': [
                    {
                        'text': message,
                    },
                ],
            },
        ],
    }

    response = requests.post(
        'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',
        params=params,
        headers=headers,
        json=json_data,
    )
    data = response.json()
    return data['candidates'][0]['content']['parts'][0]['text']


if __name__ == '__main__':
   app.run()