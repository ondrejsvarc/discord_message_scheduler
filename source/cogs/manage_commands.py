import discord
from discord.ext import commands
from discord import app_commands
import os
from datetime import datetime
import pytz

from source.config import TIMEZONE, ATTACHMENT_DIR


class ManageCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            await interaction.response.send_message("This command can only be used in DMs with me.", ephemeral=True)

    @app_commands.command(name="remove", description="Remove one of your scheduled messages.")
    @app_commands.dm_only()
    async def remove(self, interaction: discord.Interaction):
        user_tasks = await self.bot.db.get_user_schedules(interaction.user.id)
        if not user_tasks:
            await interaction.response.send_message("You have no messages scheduled.")
            return

        embed = discord.Embed(title="Select a Message to Remove",
                              description="Type the number of the message you want to remove, or `exit` to cancel.",
                              color=discord.Color.orange())
        for i, task in enumerate(user_tasks, 1):
            guild = self.bot.get_guild(task['guild_id'])
            guild_name = guild.name if guild else "Unknown Server"
            preview = task['message_content'][:40] + '...' if len(task['message_content']) > 40 else task[
                'message_content']
            embed.add_field(name=f"#{i} - {guild_name}", value=f"`{preview}`", inline=False)

        await interaction.response.send_message(embed=embed)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=120.0)
            if msg.content.lower() == 'exit':
                await interaction.followup.send("Cancelled.")
                return

            choice = int(msg.content) - 1
            if 0 <= choice < len(user_tasks):
                task_to_delete = user_tasks[choice]
                await interaction.followup.send(f"Are you sure you want to delete message `#{choice + 1}`? (yes/no)")

                confirm_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                if confirm_msg.content.lower() == 'yes':
                    await self.bot.db.delete_schedule_by_id(task_to_delete["_id"])
                    if task_to_delete.get("attachment_path") and os.path.exists(task_to_delete["attachment_path"]):
                        os.remove(task_to_delete["attachment_path"])
                    await interaction.followup.send("✅ Message removed successfully.")
                else:
                    await interaction.followup.send("Deletion cancelled.")
            else:
                await interaction.followup.send("❌ Invalid number.")
        except (TimeoutError, ValueError):
            await interaction.followup.send("⏰ Timed out or invalid input. Action cancelled.")

    @app_commands.command(name="edit", description="Edit one of your scheduled messages.")
    @app_commands.dm_only()
    async def edit(self, interaction: discord.Interaction):
        user_tasks = await self.bot.db.get_user_schedules(interaction.user.id)
        if not user_tasks:
            await interaction.response.send_message("You have no messages scheduled.")
            return

        embed = discord.Embed(title="Select a Message to Edit",
                              description="Type the number of the message to edit, or `exit`.",
                              color=discord.Color.blue())
        for i, task in enumerate(user_tasks, 1):
            guild = self.bot.get_guild(task['guild_id'])
            guild_name = guild.name if guild else "Unknown Server"
            preview = task['message_content'][:40] + '...' if len(task['message_content']) > 40 else task[
                'message_content']
            embed.add_field(name=f"#{i} - {guild_name}", value=f"`{preview}`", inline=False)

        await interaction.response.send_message(embed=embed)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=120.0)
            if msg.content.lower() == 'exit':
                await interaction.followup.send("Cancelled.")
                return

            choice = int(msg.content) - 1
            if not (0 <= choice < len(user_tasks)):
                await interaction.followup.send("❌ Invalid number.")
                return

            task_to_edit = user_tasks[choice]
            updates = {}

            while True:
                edit_embed = discord.Embed(title=f"Editing Message #{choice + 1}", color=discord.Color.purple())
                edit_embed.add_field(name="1️⃣ Edit Time", value="Change the delivery time.", inline=False)
                edit_embed.add_field(name="2️⃣ Edit Text", value="Change the message content.", inline=False)
                edit_embed.add_field(name="3️⃣ Edit Attachment", value="Change or remove the attachment.", inline=False)
                edit_embed.set_footer(text="Type a number to select an option, or type 'save' to finish.")
                await interaction.followup.send(embed=edit_embed)

                action_msg = await self.bot.wait_for('message', check=check, timeout=180.0)
                action = action_msg.content.lower()

                if action == 'save':
                    if updates:
                        await self.bot.db.update_schedule_by_id(task_to_edit["_id"], updates)
                        await interaction.followup.send("✅ Changes saved successfully!")
                    else:
                        await interaction.followup.send("No changes were made. Exiting.")
                    break

                elif action == '1':
                    await interaction.followup.send("Enter the new date and time (`dd.MM.yyyy hh:mm` in CET).")
                    new_dt_msg = await self.bot.wait_for('message', check=check, timeout=120.0)
                    try:
                        local_dt = datetime.strptime(new_dt_msg.content, "%d.%m.%Y %H:%M")
                        aware_dt = TIMEZONE.localize(local_dt)
                        utc_dt = aware_dt.astimezone(pytz.utc)
                        if utc_dt < datetime.now(pytz.utc):
                            await interaction.followup.send("❌ Time is in the past. Try again.")
                            continue
                        updates['send_timestamp'] = utc_dt
                        await interaction.followup.send("✅ Time updated.")
                    except ValueError:
                        await interaction.followup.send("❌ Invalid format.")

                elif action == '2':
                    await interaction.followup.send("Enter the new message content.")
                    new_content_msg = await self.bot.wait_for('message', check=check, timeout=300.0)
                    updates['message_content'] = new_content_msg.content
                    await interaction.followup.send("✅ Text updated.")

                elif action == '3':
                    await interaction.followup.send("Upload a new file, or type `none` to remove the current one.")
                    new_attach_msg = await self.bot.wait_for('message', check=check, timeout=120.0)

                    if task_to_edit.get("attachment_path") and os.path.exists(task_to_edit["attachment_path"]):
                        os.remove(task_to_edit["attachment_path"])

                    if new_attach_msg.attachments:
                        attachment = new_attach_msg.attachments[0]
                        filename = f"{int(datetime.now().timestamp())}_{attachment.filename}"
                        new_path = os.path.join(ATTACHMENT_DIR, filename)
                        await attachment.save(new_path)
                        updates['attachment_path'] = new_path
                        await interaction.followup.send("✅ New attachment saved.")
                    else:
                        updates['attachment_path'] = None
                        await interaction.followup.send("✅ Attachment removed.")
                else:
                    await interaction.followup.send("❌ Invalid option.")

        except (TimeoutError, ValueError):
            await interaction.followup.send("⏰ Timed out or invalid input. Action cancelled.")


async def setup(bot: commands.Bot):
    await bot.add_cog(ManageCommands(bot))