from discord.ext import commands
import discord

class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def assign(self, ctx, member: discord.Member, time_str: str, *, description: str):
        """
        Assigns a task to a user.
        Usage: !assign @User "tomorrow at 5pm" Buy milk
        """
        import dateparser
        from database import db
        import datetime

        due_date = dateparser.parse(time_str, settings={'PREFER_DATES_FROM': 'future'})
        if not due_date:
            await ctx.send(f"Could not parse time: '{time_str}'. Try something like 'in 10m', '1h', 'tomorrow'.")
            return
        
        # Ensure future date
        if due_date < datetime.datetime.now():
             # Sometimes dateparser parses '10m' as 10 minutes ago if not careful, 
             # but usually it defaults favorably or we can set settings. 
             # Let's assume user inputs 'in 10m' or we force future.
             # Actually '10m' might parse as 10 minutes ago depending on config.
             # Let's use strict settings or check. 
             # For simpler usage, let's trust dateparser defaults for now but handle past dates.
             # If it's in the past, maybe they meant 'tomorrow at X'? 
             # For now, just warn.
             await ctx.send("Warning: The parsed date is in the past. I'll save it anyway.")

        try:
            # add_task(description, assignee_id, author_id, due_date, channel_id, jump_url)
            db.add_task(description, member.id, ctx.author.id, due_date, ctx.channel.id, ctx.message.jump_url)
            await ctx.send(f"✅ Task assigned to {member.mention}: **{description}**\n📅 Due: {due_date}")
        except Exception as e:
            await ctx.send(f"Failed to assign task: {e}")

    @commands.command(name="tasks")
    async def list_tasks(self, ctx):
        """List all pending tasks."""
        from database import db
        tasks = db.get_pending_tasks()
        
        if not tasks:
            await ctx.send("No tasks found.")
            return

        msg = "**Pending Tasks:**\n"
        for t in tasks:
            # Schema: Status, Group, Assigned By, Assigned To, Due Date, Task Name, Task Inform, Link
            status = t.get('Status', '')
            if status != 'Pending':
                continue
                
            desc = t.get('Task Name')
            due = t.get('Due Date')
            assignee = t.get('Assigned To')
            # Link = t.get('Link')
            
            msg += f"• {desc} (Due: {due}) - <@{assignee}>\n"
        
        await ctx.send(msg)

async def setup(bot):
    await bot.add_cog(Tasks(bot))
