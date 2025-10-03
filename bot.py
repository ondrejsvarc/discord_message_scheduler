# bot.py
import discord
from discord.ext import commands
import os
import asyncio

# Import components from our source folder
from source.config import BOT_TOKEN, ATTACHMENT_DIR
from source.utils.database import DatabaseHandler


class SchedulerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        self.db = DatabaseHandler()

    async def setup_hook(self):
        """This is called when the bot is setting up."""
        print("--- Loading Cogs ---")
        for filename in os.listdir('./source/cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'source.cogs.{filename[:-3]}')
                    print(f"✅ Loaded cog: {filename}")
                except Exception as e:
                    print(f"❌ Failed to load cog {filename}: {e}")
        print("--------------------")

    async def on_ready(self):
        """Event that runs when the bot is ready."""
        print(f'✅ Logged in as {self.user.name}')
        if not os.path.exists(ATTACHMENT_DIR):
            os.makedirs(ATTACHMENT_DIR)

        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")


async def main():
    bot = SchedulerBot()
    await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())