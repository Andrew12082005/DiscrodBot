import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# 1. 載入環境變數
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

# 2. 設定 Intent
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
async def ping(ctx):
    # 用於測試 Bot 是否活著
    await ctx.send("Pong! 🏓 (v1.2 - Group Support Ready)")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    
    # --- 讀取所有允許的頻道 ID (包含各組) ---
    env_keys = [
        'ALLOWED_CHANNEL_ID', 'ALLOWED_CHANNEL_IDS', # 全域/管理員
        'Propulsion_CHANNEL_ID',    # 推進組
        'Avionics_CHANNEL_ID',      # 航電組
        'Structure_CHANNEL_ID',     # 結構組
        'Machining_CHANNEL_ID',     # 加工組
        'Admin_ID'                  # 管理員備份頻道
    ]

    allowed_ids = []
    
    for key in env_keys:
        val = os.getenv(key)
        if val:
            # 切割逗號並去除空白
            ids = [x.strip() for x in val.split(',') if x.strip()]
            for x in ids:
                if x not in allowed_ids:
                    allowed_ids.append(x)
                    
    if allowed_ids:
        print(f"🔒 Bot is restricted to {len(allowed_ids)} channels.")
        print(f"   Allowed IDs: {allowed_ids}")
    else:
        print("⚠️ No channel restrictions found. Bot will respond in ALL channels.")
    
    print('------')
    
    # Load cogs
    initial_extensions = [
        'cogs.tasks',
        'cogs.reminders',
    ]
    
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            print(f'✅ Loaded extension: {extension}')
        except Exception as e:
            print(f'❌ Failed to load extension {extension}: {e}')

@bot.check
async def globally_block_channels(ctx):
    # --- 全域檢查邏輯：確保指令只能在允許的頻道使用 ---
    
    env_keys = [
        'ALLOWED_CHANNEL_ID', 'ALLOWED_CHANNEL_IDS',
        'Propulsion_CHANNEL_ID',
        'Avionics_CHANNEL_ID',
        'Structure_CHANNEL_ID',
        'Machining_CHANNEL_ID',
        'Admin_ID'
    ]
    
    allowed_ids = []
    
    # 讀取並合併所有 ID
    for key in env_keys:
        val = os.getenv(key)
        if val:
            ids = [x.strip() for x in val.split(',') if x.strip()]
            allowed_ids.extend(ids)

    # 如果完全沒設定限制，則預設允許所有頻道
    if not allowed_ids:
        return True
    
    # 檢查當前頻道 ID 是否在清單中
    if str(ctx.channel.id) in allowed_ids:
        return True
    else:
        # 印出阻擋訊息，方便除錯
        print(f"⛔ Blocked command in channel '{ctx.channel.name}' (ID: {ctx.channel.id}). Not in allowed list.")
        return False

if __name__ == '__main__':
    if not TOKEN:
        print("❌ Error: DISCORD_TOKEN not found in .env")
    else:
        bot.run(TOKEN)