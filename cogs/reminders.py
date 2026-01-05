from discord.ext import commands, tasks
import discord
import datetime
import dateparser
from database import db

class Reminders(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    @tasks.loop(seconds=10)
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
                # Logic 2: Due date trigger if Status is 'Pending' (Optional, keeping purely valid Pending logic)
                
                # Safety: Ensure Link ID exists to avoid infinite spam (since we can't update status without it)
                if not task.get('Link'):
                    # Only warn once per loop? or just ignore?
                    # valid tasks must have a link (or some unique ID) to be updatable.
                    continue

                trigger = False
            
                
                # Logic 3: User Request - "make Sent to trigger and change to Actived"
                # This creates a cycle: Sent -> Actived -> Pending -> Sent
                if status == 'Sent':
                    trigger = True
                

                if trigger:
                    # 1. Resolve Channel
                    target_channel = None
                    
                    # RESTRICTION CHECK
                    import os
                    allowed_ids_str = os.getenv('ALLOWED_CHANNEL_IDS')
                    allowed_ids = []
                    
                    # Parse multiple IDs
                    if allowed_ids_str:
                        allowed_ids = [x.strip() for x in allowed_ids_str.split(',') if x.strip()]
                    
                    # Backward compatibility for single ID (Robust split)
                    old_id = os.getenv('ALLOWED_CHANNEL_ID')
                    if old_id:
                        extras = [x.strip() for x in old_id.split(',') if x.strip()]
                        for x in extras:
                            if x not in allowed_ids:
                                allowed_ids.append(x)

                    # Logic Update: User confirmed "Task Information" is JUST DATA, not a channel name.
                    # Priority: 
                    # 1. Use Allowed Channel (first one) if configured.
                    # 2. Only check Task Information if NO allowed channels are set (Legacy behavior).

                    if allowed_ids:
                         # Use the first allowed channel
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
                        # Legacy: Try to resolve from Task Info if no restrictions
                        inform_val = str(task.get('Task Information', '')).strip()
                        if inform_val.isdigit():
                            target_channel = self.bot.get_channel(int(inform_val))
                        else:
                            target_channel = discord.utils.get(self.bot.get_all_channels(), name=inform_val)
                            if not target_channel:
                                 target_channel = discord.utils.get(self.bot.get_all_channels(), name=inform_val.lower())

                    if not target_channel:
                         print(f"❌ Channel '{inform_val}' (or restricted fallback) not found for task '{task.get('Task Name')}'")
                         continue

                    # 2. Resolve User (Assigned To)
                    assignee_val = str(task.get('Assigned To', '')).strip()
                    mention_str = assignee_val # Default to just text
                    
                    if assignee_val.isdigit():
                         mention_str = f"<@{assignee_val}>"
                    else:
                         # Try finding member in the guild of the channel
                         if hasattr(target_channel, 'guild'):
                             # Case-insensitive lookup
                             found_member = None
                             target_name = assignee_val.lower()
                             
                             # DEBUG: Check if we can see members
                             members = target_channel.guild.members
                             print(f"DEBUG: Searching for '{target_name}' in {len(members)} members...")
                             
                             for m in members:
                                 # print(f" - Checking: {m.name} / {m.display_name}") # Uncomment for spammy debug
                                 # Partial match: if "andrew" is inside "andrew1208" or "superandrew"
                                 if target_name in m.name.lower() or (m.display_name and target_name in m.display_name.lower()):
                                     found_member = m
                                     print(f"DEBUG: Found match! {m.name} -> {m.id}")
                                     break
                             
                             if found_member:
                                 mention_str = found_member.mention
                             else:
                                 print(f"DEBUG: No match found for '{target_name}'")

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
                    group_val = task.get('Group', '')
                    task_name = task.get('Task Name', 'Unnamed Task')
                    due_disp = task.get('Due Date', 'No due date')
                    task_inform_val = task.get('Task Information', '')
                    link_val = task.get('Link', '')
                    
                    msg_content = (
                        f"**{group_val} {todaydate} **工作分配\n"
                        f"Assigned By : {assigned_by_str}\n"
                        f"Assigned To : {mention_str}\n"
                        f"Task : **{task_name}**\n"
                        f"Task Information : **{task_inform_val}**\n"
                        f"Due Date : **{due_disp}**\n"
                        f"請將文件/簡報上傳至{link_val}\n"
                    )
                    
                    try:
                        await target_channel.send(msg_content)
                        
                        # 5. Update Status
                        
                        # Determine new status based on current status
                        # Sent -> Actived (Restart Cycle)
                        new_status = 'Sent'
                        if status == 'Sent':
                            new_status = 'Actived'

                        db.update_task_status_by_row(row_index, new_status)
                            
                    except discord.Forbidden:
                         print(f"❌ 403 Forbidden: I do not have permission to send messages in channel '{target_channel.name}' (ID: {target_channel.id}). Checking alternatives...")
                         
                         fallback_success = False
                         if allowed_ids:
                             for alt_id in allowed_ids:
                                 # Skip if it's the same channel we just tried
                                 if str(target_channel.id) == str(alt_id):
                                     continue
                                 
                                 # Try fetching alternative
                                 alt_channel = None
                                 if alt_id.isdigit():
                                     alt_channel = self.bot.get_channel(int(alt_id))
                                 else:
                                     alt_channel = discord.utils.get(self.bot.get_all_channels(), name=alt_id)
                                 
                                 if alt_channel:
                                     print(f"🔄 Attempting fallback to allowed channel: {alt_channel.name} (ID: {alt_channel.id})...")
                                     try:
                                         await alt_channel.send(msg_content)
                                         print(f"✅ Fallback successful!")
                                         
                                         # Determine new status based on current status
                                         # Sent -> Actived (Restart Cycle)
                                         new_status = 'Sent'
                                         if status == 'Sent':
                                             new_status = 'Actived'

                                         db.update_task_status_by_row(row_index, new_status)
                                         fallback_success = True
                                         break # Stop trying
                                     except Exception as ex:
                                          print(f"❌ Fallback failed for {alt_channel.name}: {ex}")
                         
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
