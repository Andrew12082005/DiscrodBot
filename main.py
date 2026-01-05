import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
async def ping(ctx):
    # Helpful for checking if the new code deployed
    await ctx.send("Pong! 🏓 (v1.0 - Auto-Deploy Ready)")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    
    allowed_ids_str = os.getenv('ALLOWED_CHANNEL_IDS')
    allowed_ids = []
    
    if allowed_ids_str:
        allowed_ids = [x.strip() for x in allowed_ids_str.split(',') if x.strip()]
    
    # Fallback/Merge with old single ID
    old_id = os.getenv('ALLOWED_CHANNEL_ID')
    if old_id:
         # robustness: user might put commas in the singular var
         extras = [x.strip() for x in old_id.split(',') if x.strip()]
         for x in extras:
             if x not in allowed_ids:
                 allowed_ids.append(x)
                 
    if allowed_ids:
        print(f"🔒 Bot is restricted to channel IDs: {allowed_ids}")
    else:
        print("⚠️ No ALLOWED_CHANNEL_IDS found. Bot will respond in all channels.")
    
    print('------')
    
    # Load cogs
    initial_extensions = [
        'cogs.tasks',
        'cogs.reminders',
    ]
    
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
        except Exception as e:
            print(f'Failed to load extension {extension}.', e)

@bot.check
async def globally_block_channels(ctx):
    # Support multiple IDs
    allowed_ids_str = os.getenv('ALLOWED_CHANNEL_IDS')
    allowed_ids = []
    if allowed_ids_str:
        allowed_ids = [x.strip() for x in allowed_ids_str.split(',') if x.strip()]
    
    # Backward compatibility / Robustness
    old_id = os.getenv('ALLOWED_CHANNEL_ID')
    if old_id:
        extras = [x.strip() for x in old_id.split(',') if x.strip()]
        for x in extras:
            if x not in allowed_ids:
                allowed_ids.append(x)

    # If no configuration, allow everywhere
    if not allowed_ids:
        return True
    
    # Check if the message channel ID matches any allowed ID
    if str(ctx.channel.id) in allowed_ids:
        return True
        
    return False

if __name__ == '__main__':
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
    else:
        bot.run(TOKEN)
