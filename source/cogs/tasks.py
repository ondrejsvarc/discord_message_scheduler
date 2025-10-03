import discord
from discord.ext import commands, tasks
import os


class SchedulerTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_schedule.start()

    def cog_unload(self):
        self.check_schedule.cancel()

    @tasks.loop(seconds=30)
    async def check_schedule(self):
        await self.bot.wait_until_ready()

        due_tasks_cursor = await self.bot.db.get_due_schedules()

        async for task in due_tasks_cursor:
            try:
                channel = self.bot.get_channel(task["channel_id"])
                if not channel:
                    print(f"⚠️ Could not find channel with ID: {task['channel_id']}")
                    await self.bot.db.delete_schedule_by_id(task["_id"])
                    continue

                file_to_send = None
                if task.get("attachment_path") and os.path.exists(task["attachment_path"]):
                    file_to_send = discord.File(task["attachment_path"])

                user_id = task["user_id"]
                original_content = task["message_content"]
                final_content = f"This message was scheduled by <@{user_id}>.\n\n{original_content}"

                await channel.send(content=final_content, file=file_to_send)
                print(f"🚀 Sent scheduled message to channel {channel.name}")

                await self.bot.db.delete_schedule_by_id(task["_id"])
                if task.get("attachment_path") and os.path.exists(task["attachment_path"]):
                    os.remove(task["attachment_path"])

            except Exception as e:
                print(f"❌ Error sending scheduled message (ID: {task['_id']}): {e}")
                await self.bot.db.delete_schedule_by_id(task["_id"])


async def setup(bot: commands.Bot):
    await bot.add_cog(SchedulerTasks(bot))