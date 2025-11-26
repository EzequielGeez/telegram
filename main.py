import os
import threading
import requests
from bs4 import BeautifulSoup
from flask import Flask
from telethon import TelegramClient, events
import asyncio
import time

# -- NUEVAS LIBRERÍAS DINÁMICAS --
from playwright.sync_api import sync_playwright

# --- 1. CONFIGURACIÓN (Variables de Entorno) ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

# --- 2. SERVIDOR FLASK (Keep-Alive) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot Online (Playwright Ready)"

def run_web_server():
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

# --- 3. LÓGICA DE EXTRACCIÓN (Playwright + Scrolling) ---
def procesar_erome_dinamico(url):
    resultados = []
    
    try:
        # --- INICIO DEL NAVEGADOR HEADLESS ---
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded")
            
            # 1. SIMULAR SCROLL para cargar contenido dinámico
            print("Simulando scroll para cargar todos los medios...")
            last_height = 0
            # Hacemos 5 scrolls grandes, esperando 1.5s cada vez
            for i in range(5): 
                page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                time.sleep(1.5) 
            
            # Obtener el HTML completo después de scrollear
            html_content = page.content()
            browser.close()
            # --- FIN DEL NAVEGADOR ---

            # 2. ANALIZAR EL CONTENIDO
            soup = BeautifulSoup(html_content, 'html.parser')
            media_divs = soup.find_all('div', class_='media-group')
            
            for div in media_divs:
                media_item = {}

                # Buscar la miniatura (img-front)
                thumb_tag = div.find('img', class_='img-front') 
                thumb_link = thumb_tag.get('src') or thumb_tag.get('data-src') if thumb_tag else None

                # Buscar el video
                video_tag = div.find('source')
                video_link = video_tag.get('src') if video_tag else None

                # Aplicar filtros y guardar
                if thumb_link and thumb_link.startswith('data:image/'):
                    thumb_link = None
                
                if video_link:
                    resultados.append({
                        'type': 'Video',
                        'link': video_link,
                        'thumb': thumb_link
                    })
                elif thumb_link:
                     resultados.append({
                        'type': 'Imagen',
                        'link': thumb_link,
                        'thumb': thumb_link
                    })
                        
            return resultados, None
    except Exception as e:
        return None, str(e)


# --- 4. FUNCIÓN PARA ENVIAR EMBEDS A DISCORD (Sin cambios) ---
def send_embed_to_discord(media_type, link, thumbnail):
    embed_color = 3447003 if media_type == 'Video' else 16750800 

    payload = {
        "username": "Erome Bridge Bot",
        "embeds": [
            {
                "title": f"Media Encontrado: {media_type}",
                "url": link,
                "description": f"Enlace directo: [Click para ver]({link})",
                "color": embed_color,
                "image": {"url": thumbnail} if thumbnail else None
            }
        ]
    }
    try:
        requests.post(DISCORD_WEBHOOK, json=payload)
    except Exception as e:
        print(f"Error enviando embed: {e}")


# --- 5. HANDLER DE TELEGRAM (ACTUALIZADO para Playwright) ---
client = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage)
async def handler(event):
    if event.is_private and ("erome.com" in event.text):
        url = event.text.strip()
        await event.reply(f"🕵️‍♂️ Iniciando Navegador... esto puede tardar 10 segundos.")
        
        # Ejecutar la función de scraping en un hilo separado (para que no bloquee Telegram)
        media_list, error = await asyncio.to_thread(procesar_erome_dinamico, url) 
        
        if error:
            await event.reply(f"❌ Falló al navegar: {error}")
            return
            
        if not media_list:
            await event.reply("❌ No encontré archivos (o tardó mucho en cargar).")
            return

        await event.reply(f"✅ Encontré {len(media_list)} archivos. Enviando a Discord...")
        
        for item in media_list:
            send_embed_to_discord(item['type'], item['link'], item['thumb'])
            time.sleep(1.5)
                
        await event.reply("🚀 ¡Terminado!")

# --- INICIO ---
if __name__ == '__main__':
    t = threading.Thread(target=run_web_server)
    t.start()
    print("Bot escuchando...")
    client.run_until_disconnected()
