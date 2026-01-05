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

            for task in pending_tasks:
                status = task.get('Status', '')
                
                # Logic 1: Immediate trigger if Status is 'Actived'
                # Logic 2: Due date trigger if Status is 'Pending' (Optional, keeping purely valid Pending logic)
                
                trigger = False
                
                if status == 'Actived':
                    trigger = True
                
                # Check due date for Pending tasks (optional, but good to keep)
                # If user strictly wants Status trigger, we can comment this out, 
                # but usually a Reminder bot should remind on time too.
                # However, the user said "Status will trigger", so let's prioritize that for now.
                # Let's support both: 'Actived' sends immediately. 'Pending' checks time.
                elif status == 'Pending':
                    due_str = task.get('Due Date', '')
                    if due_str:
                        due_date = dateparser.parse(due_str)
                        if due_date and due_date <= now:
                           trigger = True

                if trigger:
                    # 1. Resolve Channel (Task Information)
                    target_channel = None
                    inform_val = str(task.get('Task Information', '')).strip()
                    
                    if inform_val.isdigit():
                        target_channel = self.bot.get_channel(int(inform_val))
                    else:
                        # Try to find by name (exact)
                        target_channel = discord.utils.get(self.bot.get_all_channels(), name=inform_val)
                        
                        # Try case-insensitive if not found
                        if not target_channel:
                             # Discord text channels are usually lowercase.
                             target_channel = discord.utils.get(self.bot.get_all_channels(), name=inform_val.lower())
                    
                    if not target_channel:
                         print(f"❌ Channel '{inform_val}' not found for task '{task.get('Task Name')}'")
                         # Debug: List available channels
                         print("Available channels:", [c.name for c in self.bot.get_all_channels()])
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
                    group_val = task.get('Group', '')
                    task_name = task.get('Task Name', 'Unnamed Task')
                    due_disp = task.get('Due Date', 'No due date')
                    task_inform_val = task.get('Task Information', '')
                    link_val = task.get('Link', '')
                    
                    msg_content = (
                        f"Group : **{group_val}**\n"
                        f"Assigned By : {assigned_by_str}\n"
                        f"Assigned To : {mention_str}\n"
                        f"Task : **{task_name}**\n"
                        f"Task Information : **{task_inform_val}**\n"
                        f"Due Date : **{due_disp}**\n"
                        f"Link : {link_val}\n"
                    )
                    
                    await target_channel.send(msg_content)
                    
                    # 5. Update Status
                    link_id = task.get('Link')
                    if not link_id:
                        print("Error: No Link ID provided for task update.")
                    else:
                        db.update_task_status(link_id, 'Sent')


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
