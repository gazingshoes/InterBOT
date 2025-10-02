# ssl fix macos
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import os
from dotenv import load_dotenv
import yt_dlp
from collections import deque
import traceback
import ctypes
import ctypes.util

# manual load opus (anjeng anjeng)
opus_paths = [
    '/opt/homebrew/lib/libopus.dylib',  # Apple Silicon (M1/M2/M3)
    '/usr/local/lib/libopus.dylib',     # Intel Mac
    '/opt/homebrew/opt/opus/lib/libopus.dylib',  # Homebrew alternative path
    'libopus.0.dylib',                   # System search
    'opus'                               # Generic search
]

opus_loaded = False
for path in opus_paths:
    try:
        discord.opus.load_opus(path)
        print(f"✅ Loaded opus from: {path}")
        opus_loaded = True
        break
    except Exception as e:
        continue

if not opus_loaded:
    print("⚠️ Could not load opus! Music commands won't work.")
    print("Try running: brew reinstall opus")

# load environment variables
load_dotenv()

# setup bot pake intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True 

# yt-dlp options buat donlod lagu
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': False,  # false buat debugging
    'no_warnings': False,  # false buat debugging
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # ambil first item dari playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class MusicQueue:
    def __init__(self):
        self.queue = deque()
        self.current = None
        self.loop = False
        
    def add(self, song):
        self.queue.append(song)
    
    def next(self):
        if self.loop and self.current:
            return self.current
        if self.queue:
            self.current = self.queue.popleft()
            return self.current
        return None
    
    def clear(self):
        self.queue.clear()
        self.current = None
    
    def is_empty(self):
        return len(self.queue) == 0

# queue per guild
music_queues = {}

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        
    async def setup_hook(self):
        # sync slash commands (buat testing)
        guild = discord.Object(id=1417824633096372356)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("Slash commands synced to your server!")
        
        await self.tree.sync()
        print("Global slash commands synced!")

bot = MyBot()

def get_queue(guild_id):
    if guild_id not in music_queues:
        music_queues[guild_id] = MusicQueue()
    return music_queues[guild_id]

async def play_next(interaction: discord.Interaction):
    queue = get_queue(interaction.guild.id)
    voice_client = interaction.guild.voice_client
    
    if not voice_client:
        return
    
    song = queue.next()
    if song:
        try:
            print(f"Attempting to play: {song['title']}")  # log debug
            player = await YTDLSource.from_url(song['url'], loop=bot.loop, stream=True)
            
            voice_client.play(
                player,
                after=lambda e: bot.loop.create_task(play_next(interaction)) if not e else print(f"Player error: {e}")
            )
            
            embed = discord.Embed(
                title="🎵 lagu nya sekarang",
                description=f"**{player.title}**",
                color=discord.Color.blue()
            )
            if player.thumbnail:
                embed.set_thumbnail(url=player.thumbnail)
            
            await interaction.followup.send(embed=embed)
            print(f"Now playing: {player.title}")  # log debug
            
        except Exception as e:
            print(f"Error in play_next: {e}")  # log debug
            import traceback
            traceback.print_exc()
            await interaction.followup.send(f"❌ ngga bisa muter lagunya {str(e)}")
            await play_next(interaction)
    else:
        # disconnect abis 5 menit kalo ga muter lagu
        await asyncio.sleep(300)
        if voice_client and not voice_client.is_playing():
            await voice_client.disconnect()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} servers')
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name="/play buat muter lagu (di VC ya)"
    ))

# command: play
@bot.tree.command(name="play", description="muter lagu dari yutub")
@app_commands.describe(query="masukkin judul lagu atau link yutubnya")
async def play(interaction: discord.Interaction, query: str):
    start_time = time.time()
    try:
        print(f"[PLAY] Command received from {interaction.user.name} at {start_time}")
        print(f"[PLAY] Interaction created at: {interaction.created_at}")
        print(f"[PLAY] Time since creation: {(time.time() - interaction.created_at.timestamp()):.3f}s")
        
        # defer immediately to prevent timeout
        await interaction.response.defer()
        defer_time = time.time()
        print(f"[PLAY] Deferred successfully in {(defer_time - start_time):.3f}s")
    except discord.errors.NotFound as e:
        print(f"[PLAY] Failed to defer - interaction expired: {e}")
        print(f"[PLAY] Time elapsed: {(time.time() - start_time):.3f}s")
        return
    except Exception as e:
        print(f"[PLAY] Unexpected error during defer: {e}")
        traceback.print_exc()
        return
    
    # ngecek ada user apa engga di channel
    if not interaction.user.voice:
        await interaction.followup.send("❌ pean harus masuk vc dulu!", ephemeral=True)
        return
    
    # connect ke channel kalo belom
    voice_client = interaction.guild.voice_client
    if not voice_client:
        channel = interaction.user.voice.channel
        voice_client = await channel.connect()
    
    try:
        # nyari lagu
        async with interaction.channel.typing():
            print(f"Searching for: {query}")  # log debug
            
            data = await bot.loop.run_in_executor(
                None,
                lambda: ytdl.extract_info(f"ytsearch:{query}", download=False)
            )
            
            print(f"Search complete, processing data...")  # log debug
            
            if 'entries' in data:
                data = data['entries'][0]
            
            song_info = {
                'url': data['webpage_url'],
                'title': data['title'],
                'duration': data.get('duration', 0),
                'thumbnail': data.get('thumbnail')
            }
            
            print(f"Found song: {song_info['title']}")  # log debug
            
            queue = get_queue(interaction.guild.id)
            
            # kalo ga ada lagu yang muter, langsung puter
            if not voice_client.is_playing():
                queue.add(song_info)
                await play_next(interaction)
            else:
                # nambahin ke antrian
                queue.add(song_info)
                embed = discord.Embed(
                    title="➕ ditambahkan ke antrian",
                    description=f"**{song_info['title']}**",
                    color=discord.Color.green()
                )
                embed.add_field(name="antrian nomor", value=f"#{len(queue.queue)}")
                if song_info['thumbnail']:
                    embed.set_thumbnail(url=song_info['thumbnail'])
                
                await interaction.followup.send(embed=embed)
                
    except Exception as e:
        print(f"Error in play command: {e}")  # log debug
        import traceback
        traceback.print_exc()
        await interaction.followup.send(f"❌ Error: {str(e)}")

# command: pause
@bot.tree.command(name="pause", description="pause lagunya")
async def pause(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message("⏸️ lagunya di pause")
    else:
        await interaction.response.send_message("❌ ga ada lagu yang lagi di puter!", ephemeral=True)

# command: resume
@bot.tree.command(name="resume", description="nerusin lagunya")
async def resume(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message("▶️ lagunya dilanjutin")
    else:
        await interaction.response.send_message("❌ ga ada lagu yang lagi di pause!", ephemeral=True)

# command: skip
@bot.tree.command(name="skip", description="skip lagu")
async def skip(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("⏭️ lagunya di skip")
    else:
        await interaction.response.send_message("❌ ga ada lagu yang lagi di puter!", ephemeral=True)

# command: stop
@bot.tree.command(name="stop", description="stop lagu")
async def stop(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    queue = get_queue(interaction.guild.id)
    
    if voice_client:
        queue.clear()
        voice_client.stop()
        await voice_client.disconnect()
        await interaction.response.send_message("⏹️ lagu di stop")
    else:
        await interaction.response.send_message("❌ aku gak lagi di VC loh!", ephemeral=True)

# command: queue
@bot.tree.command(name="queue", description="nunjukkin antrian lagu")
async def show_queue(interaction: discord.Interaction):
    queue = get_queue(interaction.guild.id)
    
    if queue.is_empty() and not queue.current:
        await interaction.response.send_message("📭 antriannya kosong ni", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎵 antrian lagu",
        color=discord.Color.blue()
    )
    
    if queue.current:
        embed.add_field(
            name="lagi muter:",
            value=f"**{queue.current['title']}**",
            inline=False
        )
    
    if not queue.is_empty():
        queue_list = "\n".join([
            f"{i+1}. {song['title']}"
            for i, song in enumerate(list(queue.queue)[:10])
        ])
        embed.add_field(name="abis ini", value=queue_list, inline=False)
        
        if len(queue.queue) > 10:
            embed.add_field(name="", value=f"... dan {len(queue.queue) - 10} terus", inline=False)
    
    await interaction.response.send_message(embed=embed)

# command: loop
@bot.tree.command(name="loop", description="loop lagu")
async def loop(interaction: discord.Interaction):
    queue = get_queue(interaction.guild.id)
    queue.loop = not queue.loop
    
    status = "nyala" if queue.loop else "mati"
    emoji = "🔂" if queue.loop else "➡️"
    await interaction.response.send_message(f"{emoji} loop {status}!")

# command: now playing
@bot.tree.command(name="nowplaying", description="nunjukkin lagu yang lagi diputer")
async def nowplaying(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    queue = get_queue(interaction.guild.id)
    
    if not voice_client or not voice_client.is_playing():
        await interaction.response.send_message("❌ ga ada lagu yang lagi di puter!", ephemeral=True)
        return
    
    if queue.current:
        embed = discord.Embed(
            title="🎵 lagi muter:",
            description=f"**{queue.current['title']}**",
            color=discord.Color.blue()
        )
        if queue.current.get('thumbnail'):
            embed.set_thumbnail(url=queue.current['thumbnail'])
        
        await interaction.response.send_message(embed=embed)

# command laen

@bot.tree.command(name="roll", description="roll dadu anjay")
@app_commands.describe(sides="pilih jumlah nomor (default: 6)")
async def roll(interaction: discord.Interaction, sides: int = 6):
    if sides < 2 or sides > 100:
        await interaction.response.send_message("pilih antara 2 sampai 100!", ephemeral=True)
        return
    
    result = random.randint(1, sides)
    await interaction.response.send_message(f'🎲 wee dapet **{result}** (d{sides})')

# run bot anjayyy
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables!")
    else:
        bot.run(TOKEN)