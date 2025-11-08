import os
import discord
from discord.ext import commands

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
HELP_CHANNEL_NAMES = {"help", "questions", "q-and-a"}


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild or message.guild.id != GUILD_ID:
            return

        content = message.content.strip().lower()
        if content in {"hi", "hey", "hello", "zdr", "zdrasti"}:
            if (
                message.channel.name in HELP_CHANNEL_NAMES
                or "proj-" in message.channel.name
            ):
                try:
                    await message.delete()
                except discord.HTTPException:
                    pass
                await message.channel.send(
                    f"{message.author.mention} "
                    "тук работим асинхронно. Пиши целия въпрос: контекст, очакван резултат, реален резултат, код. "
                    "Един 'hi' не е въпрос.",
                    delete_after=20,
                )


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
