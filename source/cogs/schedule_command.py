import traceback

import discord
from discord.ext import commands
from discord import app_commands
import os
from datetime import datetime
import pytz

# Import config from the source folder
from source.config import TIMEZONE, ATTACHMENT_DIR, MAX_SCHEDULES_PER_GUILD


class ScheduleCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="schedule_message", description="Schedule a message to be sent in this channel/thread.")
    async def schedule_message(self, interaction: discord.Interaction):
        current_count = await self.bot.db.count_schedules_in_guild(interaction.guild.id)
        if current_count >= MAX_SCHEDULES_PER_GUILD:
            await interaction.response.send_message(
                f"❌ **Limit Reached!** This server already has {current_count}/{MAX_SCHEDULES_PER_GUILD} messages scheduled. "
                "Please use `/remove` to delete an old one before adding another.",
                ephemeral=True
            )
            return

        user = interaction.user
        try:
            await interaction.response.send_message("I've sent you a DM to schedule your message! 📬", ephemeral=True)
            dm_channel = await user.create_dm()
        except discord.Forbidden:
            await interaction.response.send_message("I can't DM you! Please enable DMs from server members.",
                                                    ephemeral=True)
            return

        def check(m):
            return m.author == user and m.channel == dm_channel

        try:
            await dm_channel.send(
                "📅 **Step 1: Date & Time**\nPlease enter the date and time (`dd.MM.yyyy hh:mm` in CET).")
            dt_msg = await self.bot.wait_for('message', check=check, timeout=300.0)
            local_dt = datetime.strptime(dt_msg.content, "%d.%m.%Y %H:%M")
            aware_dt = TIMEZONE.localize(local_dt)
            utc_dt = aware_dt.astimezone(pytz.utc)
            if utc_dt < datetime.now(pytz.utc):
                await dm_channel.send("❌ The specified time is in the past. Please start over.")
                return

            await dm_channel.send("📝 **Step 2: Message Content**\nPlease enter your message.")
            content_msg = await self.bot.wait_for('message', check=check, timeout=600.0)

            await dm_channel.send("📎 **Step 3: Attachment**\nUpload a file or type `none`.")
            attach_msg = await self.bot.wait_for('message', check=check, timeout=300.0)

            attachment_path = None
            if attach_msg.attachments:
                attachment = attach_msg.attachments[0]
                filename = f"{int(datetime.now().timestamp())}_{attachment.filename}"
                attachment_path = os.path.join(ATTACHMENT_DIR, filename)
                await attachment.save(attachment_path)

            new_schedule = {
                "user_id": user.id, "guild_id": interaction.guild.id,
                "channel_id": interaction.channel.id, "send_timestamp": utc_dt,
                "message_content": content_msg.content, "attachment_path": attachment_path
            }
            await self.bot.db.add_schedule(new_schedule)

            guild_name = self.bot.get_guild(interaction.guild.id).name
            embed = discord.Embed(title="✅ Message Scheduled!", color=discord.Color.green())
            embed.add_field(name="Server", value=guild_name, inline=True)
            embed.add_field(name="Channel", value=f"<#{interaction.channel.id}>", inline=True)
            embed.add_field(name="Time (CET)", value=aware_dt.strftime('%d.%m.%Y %H:%M'), inline=False)
            embed.add_field(name="Message", value=f"_{content_msg.content[:1000]}_", inline=False)
            if attachment_path:
                embed.set_footer(text=f"Attachment: {os.path.basename(attachment_path)}")
            await dm_channel.send(embed=embed)


        except TimeoutError:
            await dm_channel.send("⏰ You took too long to respond. Please start over.")
        except ValueError:
            await dm_channel.send("❌ Invalid date/time format. Please use `dd.MM.yyyy hh:mm`. Start over.")
        except Exception as e:
            print("--- AN UNEXPECTED ERROR OCCURRED IN SCHEDULE COMMAND ---")
            traceback.print_exc()
            print("----------------------------------------------------")
            if dm_channel:
                await dm_channel.send(
                    "❌ **An unexpected error occurred!** I couldn't complete the scheduling process. "
                    "The administrator has been notified of the error."
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(ScheduleCommand(bot))