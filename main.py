import os
import threading
from flask import Flask
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import requests
import asyncio

# --- CONFIGURACIÓN (Viene de las Variables de Entorno de Render) ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING") # Aquí va el código largo
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
TARGET_GROUP = os.environ.get("TARGET_GROUP") # Enlace o ID del grupo

# --- SERVIDOR WEB FALSO (Para mantener vivo a Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot funcionando OK"

def run_web_server():
    # Render asigna un puerto en la variable PORT, por defecto 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- LÓGICA DEL BOT ---
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

def send_to_discord(sender, content):
    data = {"username": f"TG: {sender}", "content": content}
    try:
        requests.post(DISCORD_WEBHOOK, json=data)
    except Exception as e:
        print(f"Error webhook: {e}")

@client.on(events.NewMessage(chats=TARGET_GROUP))
async def handler(event):
    sender = await event.get_sender()
    name = getattr(sender, 'first_name', 'Usuario')
    text = event.message.message
    
    if event.message.photo:
        text += " [Imagen adjunta]"
        
    if text:
        print(f"Reenviando: {text[:20]}...")
        send_to_discord(name, text)

# --- INICIO ---
if __name__ == '__main__':
    # 1. Iniciar el servidor web en un hilo aparte
    t = threading.Thread(target=run_web_server)
    t.start()

    # 2. Iniciar el cliente de Telegram
    print("Iniciando Bot...")
    client.start()
    client.run_until_disconnected()
