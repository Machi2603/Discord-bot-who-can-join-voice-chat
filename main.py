import discord
from discord.ext import commands
from flask import Flask, request
import threading
import asyncio
import os
import yt_dlp # <--- Importante

# --- 1. CONFIGURACIÓN DEL TOKEN ---
TOKEN = os.environ.get("DISCORD_TOKEN")

# --- 2. CONFIGURACIÓN DEL BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
app = Flask(__name__)

# Configuración de YT-DLP para que no descargue, solo haga streaming
yt_dlp_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' 
}
ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

@bot.event
async def on_ready():
    print(f'✅ Bot DJ conectado como {bot.user}')

async def play_audio(channel_id, url):
    channel = bot.get_channel(channel_id)
    if not channel:
        return "Canal no encontrado"

    voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)
    
    # Conexión
    try:
        if voice_client and voice_client.is_connected():
            if voice_client.channel.id != channel_id:
                await voice_client.move_to(channel)
        else:
            voice_client = await channel.connect()
    except Exception as e:
        return f"Error conectando: {e}"

    if voice_client.is_playing():
        voice_client.stop()
    
    # --- LÓGICA HÍBRIDA (YouTube vs MP3 Directo) ---
    audio_source_url = url
    
    # Si es YouTube, extraemos la URL real del audio
    if "youtube.com" in url or "youtu.be" in url:
        try:
            with yt_dlp.YoutubeDL(yt_dlp_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_source_url = info['url'] # URL directa del stream
                print(f"Reproduciendo desde YouTube: {info.get('title')}")
        except Exception as e:
            return f"Error extrayendo de YouTube: {e}"

    # Función para desconectar al terminar
    def after_playing(error):
        if error: print(f"Error: {error}")
        coro = voice_client.disconnect()
        future = asyncio.run_coroutine_threadsafe(coro, bot.loop)
        try: future.result()
        except: pass

    try:
        # Reproducimos la URL (sea de YouTube extraída o MP3 directo)
        source = discord.FFmpegPCMAudio(audio_source_url, **ffmpeg_options)
        voice_client.play(source, after=after_playing)
        return "Reproduciendo..."
    except Exception as e:
        return f"Error reproduciendo: {e}"

# --- 3. ENDPOINT ---
@app.route('/reproducir', methods=['POST'])
def endpoint_reproducir():
    data = request.json
    channel_id = int(data.get('channel_id'))
    url = data.get('url')
    
    if not channel_id or not url:
        return {"status": "error", "message": "Faltan datos"}, 400

    asyncio.run_coroutine_threadsafe(play_audio(channel_id, url), bot.loop)
    return {"status": "ok", "track": url}

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: No hay token configurado.")
    else:
        t = threading.Thread(target=run_flask)
        t.start()
        bot.run(TOKEN)