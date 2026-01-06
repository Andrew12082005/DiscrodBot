from discord.ext import commands, tasks
import discord
import datetime
import dateparser
import os
from database import db

class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    def resolve_users(self, guild, text):
        if not text: return "Unknown"
        parts = [x.strip() for x in text.split(',') if x.strip()]
        results = []
        for p in parts:
            found = p
            if p.isdigit():
                found = f"<@{p}>"
            elif guild:
                target = p.lower()
                for m in guild.members:
                     if target == m.name.lower() or target == m.display_name.lower():
                         found = m.mention
                         break
                if found == p:
                     for m in guild.members:
                         if target in m.name.lower() or (m.display_name and target in m.display_name.lower()):
                             found = m.mention
                             break
            results.append(found)
        return ", ".join(results)

    @tasks.loop(seconds=10)
    async def check_reminders(self):
        if not self.bot.is_ready():
            return

        try:
            pending_tasks = db.get_pending_tasks()
            now = datetime.datetime.now()

            # 使用 enumerate 取得 index (i)
            for i, task in enumerate(pending_tasks):
                # ★ 關鍵：計算正確的行數
                # get_all_records 跳過了標題列 (Row 1)，所以資料是從 Row 2 開始
                current_row_index = i + 2
                
                status = task.get('Status', '')

                # 邏輯 1: 過期檢查 (Pending -> Expired)
                due_date_str = task.get('Due Date')
                if status == 'Pending' and due_date_str:
                    try:
                        due_date = dateparser.parse(due_date_str)
                        if due_date and due_date < now:
                            print(f"🕰️ Task '{task.get('Task Name')}' is overdue. Marking Row {current_row_index} as Expired.")
                            db.update_task_status_by_row(current_row_index, 'Expired')
                            continue 
                    except Exception as e:
                        print(f"Error checking expiration: {e}")

                # 邏輯 2: 發送觸發 (只有 Status 為 'Sent' 時執行)
                if status != 'Sent':
                    continue

                # ==========================
                # 準備發送訊息
                # ==========================
                group_val = task.get('Group', '').strip()
                embed_color = discord.Color.from_rgb(0, 255, 255) # Default Cyan

                # 1. 判斷群組顏色與 ID
                allowed_ids_str = None
                if group_val == "Propulsion 推進組":
                    allowed_ids_str = os.getenv('Propulsion_CHANNEL_ID')
                    embed_color = discord.Color.red()
                elif group_val == "Avionics 航電組": 
                    allowed_ids_str = os.getenv('Avionics_CHANNEL_ID')
                    embed_color = discord.Color.blue()
                elif group_val == "Structure 結構組":
                    allowed_ids_str = os.getenv('Structure_CHANNEL_ID')
                    embed_color = discord.Color.orange()
                elif group_val == "Machining 加工組": 
                    allowed_ids_str = os.getenv('Machining_CHANNEL_ID')
                    embed_color = discord.Color.green()
                
                allowed_ids = []
                if allowed_ids_str:
                    allowed_ids = [x.strip() for x in allowed_ids_str.split(',') if x.strip()]

                # 2. 決定目標頻道
                target_channel = None
                
                # 優先使用 Env 設定的頻道
                if allowed_ids:
                     first_id = allowed_ids[0]
                     try:
                         if first_id.isdigit():
                             target_channel = self.bot.get_channel(int(first_id))
                         else: 
                             target_channel = discord.utils.get(self.bot.get_all_channels(), name=first_id)
                     except: pass
                
                # 若無 Env 設定，嘗試使用 Task Information (Legacy)
                if not target_channel:
                    inform_val = str(task.get('Task Information', '')).strip()
                    if inform_val.isdigit():
                        target_channel = self.bot.get_channel(int(inform_val))
                    else:
                        target_channel = discord.utils.get(self.bot.get_all_channels(), name=inform_val)

                if not target_channel:
                     print(f"❌ Channel not found for Row {current_row_index}. Marking as Error.")
                     db.update_task_status_by_row(current_row_index, 'Error-NoCh')
                     continue

                # 3. 建立 Embed
                assignee_val = str(task.get('Assigned To', '')).strip()
                guild_obj = target_channel.guild
                mention_str = self.resolve_users(guild_obj, assignee_val)

                assigned_by_val = str(task.get('Assigned By', 'Unknown')).strip()
                assigned_by_str = self.resolve_users(guild_obj, assigned_by_val)
                
                todaydate = task.get('Assigned Date', '')
                task_name = task.get('Task Name', 'Unnamed Task')
                due_disp = task.get('Due Date', 'No due date')
                task_inform_val = task.get('Task Information', '')
                link_val = task.get('Link', '')

                embed = discord.Embed(
                    description=f"# {group_val} {todaydate} 工作分配\n# **Task : {task_name}**",
                    color=embed_color
                )
                embed.add_field(name="Assigned By", value=assigned_by_str, inline=True)
                embed.add_field(name="Assigned To", value=mention_str, inline=True)
                embed.add_field(name="**Task Information**", value=f"{task_inform_val}", inline=False)
                embed.add_field(name="Due Date", value=f"**{due_disp}**", inline=True)
                
                if link_val.startswith('http'):
                    embed.add_field(name="Upload Link", value=f"[Click Here]({link_val})", inline=True)
                else:
                    embed.add_field(name="Upload Link", value=f"{link_val}", inline=True)
                
                # 4. 發送並更新狀態
                try:
                    await target_channel.send(embed=embed)
                    print(f"✅ Message sent to {target_channel.name}")

                    # ★★★ 核心修改：利用行數更新狀態 ★★★
                    # 如果這行失敗，表示機器人沒有 Google Sheet 的編輯權限
                    db.update_task_status_by_row(current_row_index, 'Actived')

                    # 額外功能：同步到 Admin 頻道
                    admin_id_str = os.getenv('Admin_ID')
                    if admin_id_str:
                        admin_ids = [x.strip() for x in admin_id_str.split(',') if x.strip()]
                        for aid in admin_ids:
                            if str(aid) != str(target_channel.id):
                                try:
                                    ach = self.bot.get_channel(int(aid)) or discord.utils.get(self.bot.get_all_channels(), name=aid)
                                    if ach: await ach.send(embed=embed)
                                except: pass

                except discord.Forbidden:
                     print(f"❌ 403 Forbidden in {target_channel.name}")
                     db.update_task_status_by_row(current_row_index, 'Error-Forbidden')
                     
                except Exception as e:
                     print(f"❌ Failed to send message: {e}")

        except Exception as e:
            print(f"Error in reminder loop: {e}")

    # ★ 這裡就是之前出錯的地方，現在已經修正為 check_reminders ★
    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Reminders(bot))