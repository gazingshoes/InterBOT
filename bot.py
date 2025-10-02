
import discord
from discord.ext import commands
import random
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot setup with intents (permissions)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Event: Bot is ready
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} servers')
    await bot.change_presence(activity=discord.Game(name="!help for commands"))

# Event: Welcome new members
@bot.event
async def on_member_join(member):
    channel = member.guild.system_channel
    if channel:
        await channel.send(f'Welcome to the server, {member.mention}! 👋')

# Command: Simple greeting
@bot.command(name='hello', help='Bot greets you')
async def hello(ctx):
    await ctx.send(f'Hello {ctx.author.mention}! 👋')

# Command: Dice roll
@bot.command(name='roll', help='Roll a dice (e.g., !roll 6 or !roll 20)')
async def roll(ctx, sides: int = 6):
    if sides < 2:
        await ctx.send("Dice must have at least 2 sides!")
        return
    result = random.randint(1, sides)
    await ctx.send(f'🎲 You rolled a {result} (d{sides})')

# Command: Magic 8-ball
@bot.command(name='8ball', help='Ask the magic 8-ball a question')
async def eight_ball(ctx, *, question):
    responses = [
        'Yes, definitely!',
        'It is certain.',
        'Without a doubt.',
        'Reply hazy, try again.',
        'Ask again later.',
        'Better not tell you now.',
        "Don't count on it.",
        'My reply is no.',
        'Very doubtful.'
    ]
    await ctx.send(f'🎱 Question: {question}\nAnswer: {random.choice(responses)}')

# Command: Poll
@bot.command(name='poll', help='Create a poll. Usage: !poll "Question?" "Option 1" "Option 2"')
async def poll(ctx, question, *options):
    if len(options) < 2:
        await ctx.send("You need at least 2 options!")
        return
    if len(options) > 10:
        await ctx.send("Maximum 10 options allowed!")
        return
    
    emoji_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    
    description = '\n'.join([f'{emoji_numbers[i]} {option}' 
                             for i, option in enumerate(options)])
    
    embed = discord.Embed(
        title=f'📊 {question}',
        description=description,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f'Poll by {ctx.author.display_name}')
    
    poll_msg = await ctx.send(embed=embed)
    
    for i in range(len(options)):
        await poll_msg.add_reaction(emoji_numbers[i])

# Command: Server info
@bot.command(name='serverinfo', help='Get information about the server')
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(
        title=f'{guild.name} Server Info',
        color=discord.Color.green()
    )
    embed.add_field(name='Server ID', value=guild.id, inline=True)
    embed.add_field(name='Owner', value=guild.owner.mention, inline=True)
    embed.add_field(name='Members', value=guild.member_count, inline=True)
    embed.add_field(name='Created', value=guild.created_at.strftime('%Y-%m-%d'), inline=True)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    await ctx.send(embed=embed)

# Command: User info
@bot.command(name='userinfo', help='Get info about a user')
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    
    embed = discord.Embed(
        title=f'User Info: {member.display_name}',
        color=member.color
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name='Username', value=str(member), inline=True)
    embed.add_field(name='ID', value=member.id, inline=True)
    embed.add_field(name='Joined Server', value=member.joined_at.strftime('%Y-%m-%d'), inline=True)
    embed.add_field(name='Account Created', value=member.created_at.strftime('%Y-%m-%d'), inline=True)
    
    roles = [role.mention for role in member.roles[1:]]
    if roles:
        embed.add_field(name='Roles', value=' '.join(roles), inline=False)
    
    await ctx.send(embed=embed)

# Command: Clear messages (requires permissions)
@bot.command(name='clear', help='Clear messages. Usage: !clear 10')
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    if amount < 1 or amount > 100:
        await ctx.send("Please specify a number between 1 and 100.")
        return
    
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f'Cleared {amount} messages! 🧹')
    await asyncio.sleep(3)
    await msg.delete()

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to clear messages!")

# Command: Reminder
@bot.command(name='remind', help='Set a reminder. Usage: !remind 10 Take a break')
async def remind(ctx, seconds: int, *, message):
    if seconds < 1 or seconds > 86400:
        await ctx.send("Please set a reminder between 1 second and 24 hours!")
        return
    
    await ctx.send(f'⏰ Reminder set for {seconds} seconds from now!')
    await asyncio.sleep(seconds)
    await ctx.send(f'{ctx.author.mention} Reminder: {message}')

# Global error handler
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f'Missing required argument! Use `!help {ctx.command}` for usage info.')
    elif isinstance(error, commands.BadArgument):
        await ctx.send('Invalid argument provided!')
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f'Error: {error}')

# Run the bot using environment variable
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables!")
    else:
        bot.run(TOKEN)