import os
import threading
import time
import requests
import cloudscraper
from bs4 import BeautifulSoup
from flask import Flask
from telethon import TelegramClient, events

# --- 1. CONFIGURACIÓN (Viene de Render) ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

# --- 2. SERVIDOR PARA MANTENER VIVO A RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Online. Envíame un link por Telegram."

def run_web_server():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- 3. LÓGICA DE EXTRACCIÓN (EROME) ---
def procesar_erome(url):
    scraper = cloudscraper.create_scraper() # Se hace pasar por humano
    resultados = []
    
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            return None, f"Error web: {response.status_code}"

        soup = BeautifulSoup(response.text, 'html.parser')
        media_divs = soup.find_all('div', class_='media-group')
        
        for div in media_divs:
            # Video
            video = div.find('source')
            if video and video.get('src'):
                resultados.append(video.get('src'))
                continue
            # Imagen
            img = div.find('img', class_='img-front') or div.find('img', {'data-src': True})
            if img:
                link = img.get('src') or img.get('data-src')
                if link:
                    resultados.append(link)
                    
        return resultados, None
    except Exception as e:
        return None, str(e)

# --- 4. BOT DE TELEGRAM ---
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage)
async def handler(event):
    # Solo funciona en chat privado
    if event.is_private and ("erome.com" in event.text):
        url = event.text.strip()
        await event.reply(f"🕵️‍♂️ Procesando álbum...")
        
        links, error = procesar_erome(url)
        
        if error:
            await event.reply(f"❌ Falló: {error}")
            return
            
        if not links:
            await event.reply("❌ No encontré archivos. Quizás el álbum está vacío.")
            return

        await event.reply(f"✅ Encontré {len(links)} archivos. Enviando a Discord...")
        
        # Enviar a Discord
        headers = {"Content-Type": "application/json"}
        for link in links:
            try:
                requests.post(DISCORD_WEBHOOK, json={"content": link}, headers=headers)
                time.sleep(1.2) # Pausa pequeña para no saturar
            except:
                pass
                
        await event.reply("🚀 ¡Terminado!")

# --- INICIO ---
if __name__ == '__main__':
    t = threading.Thread(target=run_web_server)
    t.start()
    client.run_until_disconnected()
