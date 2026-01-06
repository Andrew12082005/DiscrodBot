from discord.ext import commands, tasks
import discord
import datetime
import dateparser
import os  # 將 import 移到最上方比較規範
from database import db

class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    @tasks.loop(seconds=20)
    async def check_reminders(self):
        # Prevent running before bot is ready
        if not self.bot.is_ready():
            return

        try:
            pending_tasks = db.get_pending_tasks()
            now = datetime.datetime.now()

            for i, task in enumerate(pending_tasks):
                row_index = i + 2 # Header is row 1
                status = task.get('Status', '')
                
                # Logic 1: Immediate trigger if Status is 'Actived'
                # Logic 2: Due date trigger if Status is 'Pending'
                
                # Safety: Ensure Link ID exists to avoid infinite spam
                if not task.get('Link'):
                    continue

                trigger = False
            
                # Logic 3: User Request - "make Sent to trigger and change to Actived"
                if status == 'Sent':
                    trigger = True
                
                # Logic: Automatic Expiration
                due_date_str = task.get('Due Date')
                if status == 'Pending' and due_date_str:
                    try:
                        due_date = dateparser.parse(due_date_str)
                        if due_date and due_date < now:
                            print(f"🕰️ Task '{task.get('Task Name')}' is overdue (Due: {due_date}). Marking as Expired.")
                            db.update_task_status_by_row(row_index, 'Expired')
                            continue 
                    except Exception as e:
                        print(f"Error checking expiration for task '{task.get('Task Name')}': {e}")

                # ==========================================
                # ★ 修改開始：群組頻道解析邏輯 (Fix Start)
                # ==========================================
                
                # 1. 先取得群組名稱 (去除前後空白)
                group_val = task.get('Group', '').strip()
                allowed_ids_str = None
                
                # 2. 根據群組對應到 .env 變數
                if group_val == "Propulsion 推進組":
                    allowed_ids_str = os.getenv('Propulsion_CHANNEL_ID')
                elif group_val == "Avionics 航電組": # 請確認資料庫內是「組」還是「阻」
                    allowed_ids_str = os.getenv('Avionics_CHANNEL_ID')
                elif group_val == "Structure 結構組":
                    allowed_ids_str = os.getenv('Structure_CHANNEL_ID')
                elif group_val == "Machining 加工組": # 新增加工組
                    allowed_ids_str = os.getenv('Machining_CHANNEL_ID')
                
                allowed_ids = []
                
                # 3. 解析群組專屬 ID
                if allowed_ids_str:
                    allowed_ids = [x.strip() for x in allowed_ids_str.split(',') if x.strip()]
                
                # 3.5 加入 Admin_ID (Essential for Fallback & Admin Copy validation)
                admin_id_env = os.getenv('Admin_ID')
                if admin_id_env:
                     admin_ids = [x.strip() for x in admin_id_env.split(',') if x.strip()]
                     for x in admin_ids:
                         if x not in allowed_ids:
                             allowed_ids.append(x)
                
                # 4. 加入全域/舊版允許 ID (Backward compatibility)
                # 支援 ALLOWED_CHANNEL_IDS 或 ALLOWED_CHANNEL_ID
                global_ids_str = os.getenv('ALLOWED_CHANNEL_IDS') or os.getenv('ALLOWED_CHANNEL_ID')
                if global_ids_str:
                    extras = [x.strip() for x in global_ids_str.split(',') if x.strip()]
                    for x in extras:
                        if x not in allowed_ids:
                            allowed_ids.append(x)

                target_channel = None

                if trigger:
                    print(f"DEBUG: Processing task '{task.get('Task Name')}'. Group: '{group_val}'")
                    
                    # 優先權 1: 如果有設定允許清單 (allowed_ids)，抓第一個當作目標
                    if allowed_ids:
                         first_id = allowed_ids[0]
                         try:
                             if first_id.isdigit():
                                 target_channel = self.bot.get_channel(int(first_id))
                             else: 
                                 target_channel = discord.utils.get(self.bot.get_all_channels(), name=first_id)
                             
                             if not target_channel:
                                 print(f"❌ Default allowed channel '{first_id}' not found!")
                         except Exception as e:
                             print(f"Error resolving default channel: {e}")

                    else:
                        # 優先權 2 (Legacy): 如果完全沒有設定環境變數，才從 Task Information 抓
                        inform_val = str(task.get('Task Information', '')).strip()
                        if inform_val.isdigit():
                            target_channel = self.bot.get_channel(int(inform_val))
                        else:
                            target_channel = discord.utils.get(self.bot.get_all_channels(), name=inform_val)
                            if not target_channel:
                                 target_channel = discord.utils.get(self.bot.get_all_channels(), name=inform_val.lower())

                    if not target_channel:
                         print(f"❌ Channel not found for task '{task.get('Task Name')}' (Group: {group_val})")
                         continue
                
                # ==========================================
                # ★ 修改結束 (Fix End)
                # ==========================================

                    # 2. Resolve User (Assigned To)
                    assignee_val = str(task.get('Assigned To', '')).strip()
                    mention_str = assignee_val 
                    
                    if assignee_val.isdigit():
                         mention_str = f"<@{assignee_val}>"
                    else:
                         if hasattr(target_channel, 'guild'):
                             found_member = None
                             target_name = assignee_val.lower()
                             
                             # DEBUG: Check if we can see members
                             members = target_channel.guild.members
                             # print(f"DEBUG: Searching for '{target_name}' in {len(members)} members...")
                             
                             for m in members:
                                 if target_name in m.name.lower() or (m.display_name and target_name in m.display_name.lower()):
                                     found_member = m
                                     break
                             
                             if found_member:
                                 mention_str = found_member.mention

                    # 3. Resolve Assigned By User
                    assigned_by_val = str(task.get('Assigned By', 'Unknown')).strip()
                    assigned_by_str = assigned_by_val
                    
                    if assigned_by_val.isdigit():
                         assigned_by_str = f"<@{assigned_by_val}>"
                    else:
                         if hasattr(target_channel, 'guild'):
                             found_author = None
                             target_name = assigned_by_val.lower()
                             for m in target_channel.guild.members:
                                 if target_name in m.name.lower() or (m.display_name and target_name in m.display_name.lower()):
                                     found_author = m
                                     break
                             
                             if found_author:
                                 assigned_by_str = found_author.mention
                    
                    # 4. Send Message
                    todaydate = task.get('Assigned Date', '')
                    task_name = task.get('Task Name', 'Unnamed Task')
                    due_disp = task.get('Due Date', 'No due date')
                    task_inform_val = task.get('Task Information', '')
                    link_val = task.get('Link', '')
                    
                    # Create Embed
                    embed = discord.Embed(
                        description=f"# {group_val} {todaydate} 工作分配\n# **Task : {task_name}**",
                        color=discord.Color.from_rgb(0, 255, 255)
                    )
                    
                    embed.add_field(name="Assigned By", value=assigned_by_str, inline=True)
                    embed.add_field(name="Assigned To", value=mention_str, inline=True)
                    embed.add_field(name="**Task Information**", value=f"{task_inform_val}", inline=False)
                    embed.add_field(name="Due Date", value=f"**{due_disp}**", inline=True)
                    
                    if link_val.startswith('http'):
                        embed.add_field(name="Upload Link", value=f"[Click Here]({link_val})", inline=True)
                    else:
                        embed.add_field(name="Upload Link", value=f"{link_val}", inline=True)
                    
                    try:
                        # 4.1 Send to Group Channel
                        await target_channel.send(embed=embed)
                        print(f"✅ Message sent to {target_channel.name} (ID: {target_channel.id})")

                        # ==========================================
                        # ★ 新增：同步發送給 Admin (New)
                        # ==========================================
                        admin_id_str = os.getenv('Admin_ID')
                        if admin_id_str:
                             admin_ids = [x.strip() for x in admin_id_str.split(',') if x.strip()]
                             for aid in admin_ids:
                                 # 避免重複發送 (如果目標頻道就是 Admin 頻道)
                                 if str(aid) == str(target_channel.id):
                                     continue

                                 try:
                                     admin_ch = None
                                     if aid.isdigit():
                                         admin_ch = self.bot.get_channel(int(aid))
                                     else:
                                         admin_ch = discord.utils.get(self.bot.get_all_channels(), name=aid)
                                     
                                     if admin_ch:
                                         await admin_ch.send(embed=embed)
                                         print(f"✅ Copied message to Admin Channel: {admin_ch.name}")
                                     else:
                                         print(f"⚠️ Admin channel ID '{aid}' not found.")
                                 except Exception as admin_ex:
                                     print(f"❌ Failed to copy to Admin Channel ({aid}): {admin_ex}")
                        # ==========================================

                        # 5. Update Status
                        new_status = 'Sent'
                        if status == 'Sent':
                            new_status = 'Actived'

                        db.update_task_status_by_row(row_index, new_status)
                            
                    except discord.Forbidden:
                         print(f"❌ 403 Forbidden: No permission in '{target_channel.name}'. Checking alternatives...")
                         
                         fallback_success = False
                         if allowed_ids:
                             print(f"DEBUG: Fallback candidates: {allowed_ids}")
                             for alt_id in allowed_ids:
                                 if str(target_channel.id) == str(alt_id):
                                     continue
                                 
                                 alt_channel = None
                                 if alt_id.isdigit():
                                     alt_channel = self.bot.get_channel(int(alt_id))
                                 else:
                                     alt_channel = discord.utils.get(self.bot.get_all_channels(), name=alt_id)
                                 
                                 if alt_channel:
                                     print(f"🔄 Fallback to: {alt_channel.name}...")
                                     try:
                                         await alt_channel.send(embed=embed)
                                         print(f"✅ Fallback successful!")
                                         
                                         new_status = 'Sent'
                                         if status == 'Sent':
                                             new_status = 'Actived'

                                         db.update_task_status_by_row(row_index, new_status)
                                         fallback_success = True
                                         break
                                     except Exception as ex:
                                          print(f"❌ Fallback failed: {ex}")
                         
                         if not fallback_success:
                             print("❌ All attempts failed. Skipping task.")
                             link_id = task.get('Link')
                             if link_id:
                                 db.update_task_status(link_id, 'Skipped')
                             
                    except Exception as e:
                         print(f"❌ Failed to send message: {e}")

        except Exception as e:
            print(f"Error in reminder loop: {e}")

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Reminders(bot))

if __name__ == "__main__":
    print("❌ ERROR: You are running this file directly!")
    print("Please run 'main.py' in the main folder instead.")