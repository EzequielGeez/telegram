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

# --- 2. SERVIDOR FLASK (Para que Render no se duerma) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Online. Envíame un link por Telegram."

def run_web_server():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- 3. LÓGICA DE EXTRACCIÓN (Ahora busca Link y Miniatura) ---
def procesar_erome(url):
    scraper = cloudscraper.create_scraper()
    resultados = []
    
    try:
        response = scraper.get(url)
        if response.status_code != 200:
            return None, f"Error web: {response.status_code}"

        soup = BeautifulSoup(response.text, 'html.parser')
        media_divs = soup.find_all('div', class_='media-group')
        
        for div in media_divs:
            media_item = {}

            # Buscar la miniatura (imagen de portada)
            thumb_tag = div.find('img', class_='img-front') 
            thumb_link = thumb_tag.get('src') or thumb_tag.get('data-src') if thumb_tag else None

            # Aplicar filtro Base64
            if thumb_link and thumb_link.startswith('data:image/'):
                thumb_link = None
            
            # Buscar el video
            video_tag = div.find('source')
            video_link = video_tag.get('src') if video_tag else None

            # Si es video:
            if video_link:
                resultados.append({
                    'type': 'Video',
                    'link': video_link,
                    'thumb': thumb_link
                })
            # Si es solo imagen (usamos el mismo link como miniatura)
            elif thumb_link:
                 resultados.append({
                    'type': 'Imagen',
                    'link': thumb_link,
                    'thumb': thumb_link
                })
                    
        return resultados, None
    except Exception as e:
        return None, str(e)

# --- 4. FUNCIÓN PARA ENVIAR EMBEDS A DISCORD ---
def send_embed_to_discord(media_type, link, thumbnail):
    embed_color = 3447003 if media_type == 'Video' else 16750800 # Blue or Orange

    payload = {
        "username": "Erome Bridge Bot",
        "embeds": [
            {
                "title": f"Media Encontrado: {media_type}",
                "url": link,
                "description": f"Enlace directo: [Click para ver]({link})",
                "color": embed_color,
            }
        ]
    }
    
    if thumbnail:
        # Pone la miniatura como imagen principal del embed
        payload["embeds"][0]["image"] = {"url": thumbnail}
        
    try:
        requests.post(DISCORD_WEBHOOK, json=payload)
    except Exception as e:
        print(f"Error enviando embed: {e}")


# --- 5. HANDLER DE TELEGRAM (ACTUALIZADO) ---
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage)
async def handler(event):
    if event.is_private and ("erome.com" in event.text):
        url = event.text.strip()
        await event.reply(f"🕵️‍♂️ Procesando álbum...")
        
        media_list, error = procesar_erome(url)
        
        if error:
            await event.reply(f"❌ Falló: {error}")
            return
            
        if not media_list:
            await event.reply("❌ No encontré archivos. Quizás el álbum está vacío o la estructura web ha cambiado.")
            return

        await event.reply(f"✅ Encontré {len(media_list)} archivos. Enviando a Discord con miniaturas...")
        
        # Enviar cada item con su embed y miniatura
        for item in media_list:
            send_embed_to_discord(item['type'], item['link'], item['thumb'])
            time.sleep(1.5) # Pausa para evitar rate-limit
                
        await event.reply("🚀 ¡Terminado!")

# --- INICIO ---
if __name__ == '__main__':
    t = threading.Thread(target=run_web_server)
    t.start()
    client.run_until_disconnected()
