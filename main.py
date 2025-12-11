import discord
from discord.ext import commands
from flask import Flask, request
import threading
import asyncio
import os

# --- 1. CONFIGURACIÓN DEL TOKEN (PRIMERO DE TODO) ---
# Busca la variable en el sistema. Si no existe, da error y avisa.
TOKEN = os.environ.get("DISCORD_TOKEN")

if not TOKEN:
    print("❌ ERROR CRÍTICO: No he encontrado el DISCORD_TOKEN en las variables de entorno.")
    print("   Asegúrate de haberlo añadido en Easypanel -> Environment.")
    # Si quieres probar en local sin variables, descomenta la siguiente línea y pon tu token:
    # TOKEN = "TU_TOKEN_AQUI" 
    # Pero recuerda NO subirlo a GitHub si haces esto.
    if not TOKEN:
        raise ValueError("Falta el Token")

# --- 2. CONFIGURACIÓN DEL BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
app = Flask(__name__)

@bot.event
async def on_ready():
    print(f'✅ Bot DJ conectado como {bot.user}')

async def play_audio(channel_id, mp3_url):
    channel = bot.get_channel(channel_id)
    if not channel:
        return "Canal no encontrado"

    # Gestionar conexión al canal de voz
    voice_client = discord.utils.get(bot.voice_clients, guild=channel.guild)
    
    try:
        if voice_client and voice_client.is_connected():
            if voice_client.channel.id != channel_id:
                await voice_client.move_to(channel)
        else:
            voice_client = await channel.connect()
    except Exception as e:
        return f"Error conectando: {e}"

    # Detener si ya está sonando algo
    if voice_client.is_playing():
        voice_client.stop()

    # Reproducir el MP3
    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    
    try:
        source = discord.FFmpegPCMAudio(mp3_url, **ffmpeg_options)
        voice_client.play(source, after=lambda e: print('Reproducción terminada'))
        return "Reproduciendo..."
    except Exception as e:
        return f"Error reproduciendo: {e}"

# --- 3. ENDPOINT PARA N8N ---
@app.route('/reproducir', methods=['POST'])
def endpoint_reproducir():
    data = request.json
    channel_id = int(data.get('channel_id'))
    url = data.get('url')
    
    if not channel_id or not url:
        return {"status": "error", "message": "Faltan datos (channel_id o url)"}, 400

    # Mandamos la tarea al bot de forma segura
    asyncio.run_coroutine_threadsafe(play_audio(channel_id, url), bot.loop)
    return {"status": "ok", "track": url}

def run_flask():
    app.run(host='0.0.0.0', port=5000)

# --- 4. ARRANQUE FINAL ---
if __name__ == "__main__":
    # Arrancamos el servidor web en un hilo secundario
    t = threading.Thread(target=run_flask)
    t.start()
    
    # Arrancamos el bot de Discord (ESTA LÍNEA ES VITAL)
    bot.run(TOKEN)