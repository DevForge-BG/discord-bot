import os
import asyncio
from dotenv import load_dotenv
import discord
from discord.ext import commands
from db import get_db, close_db
from roles import ensure_role

load_dotenv()
INTENTS = discord.Intents.default()
INTENTS.members = True
INTENTS.message_content = True
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

class DevForgeBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)
        self.core_roles = {}

    async def setup_hook(self):
        await get_db()
        guild = self.get_guild(GUILD_ID) or await self.fetch_guild(GUILD_ID)
        await self._ensure_core_roles(guild)

        await self.load_extension("cogs.onboarding")
        await self.load_extension("cogs.students")
        await self.load_extension("cogs.projects")
        await self.load_extension("cogs.github_integration")
        await self.load_extension("cogs.moderation")

        await self.tree.sync(guild=discord.Object(id=GUILD_ID))

    async def _ensure_core_roles(self, guild: discord.Guild):
        admin = await ensure_role(guild, "👑 Admin", permissions=discord.Permissions(administrator=True))
        student = await ensure_role(guild, "🎓 Student", color=discord.Color.blue())
        pending = await ensure_role(guild, "⏳ Pending", color=discord.Color.light_grey())
        inactive = await ensure_role(guild, "🚫 Inactive", color=discord.Color.dark_grey())
        mentor = await ensure_role(guild, "👨‍🏫 Mentor", color=discord.Color.gold())
        web = await ensure_role(guild, "🌐 Web")
        backend = await ensure_role(guild, "⚙️ Backend")
        systems = await ensure_role(guild, "🧠 Systems / Low-level")
        mobile = await ensure_role(guild, "📱 Mobile")
        desktop = await ensure_role(guild, "🖥️ Desktop")
        self.core_roles = {
            "admin": admin.id, "student": student.id, "pending": pending.id,
            "inactive": inactive.id, "mentor": mentor.id, "web": web.id,
            "backend": backend.id, "systems": systems.id,
            "mobile": mobile.id, "desktop": desktop.id
        }

    async def close(self):
        await close_db()
        await super().close()

def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Missing DISCORD_TOKEN")
    bot = DevForgeBot()
    bot.run(token)

if __name__ == "__main__":
    main()
