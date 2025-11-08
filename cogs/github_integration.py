import json
from aiohttp import web
import discord
from discord.ext import commands
from db import get_db

GITHUB_WEBHOOK_PORT = 8000  # adjust if needed


class GitHubIntegration(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_post("/github", self.handle_github)
        self.runner = web.AppRunner(self.app)
        self.bot.loop.create_task(self.start_server())

    async def start_server(self):
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", GITHUB_WEBHOOK_PORT)
        await site.start()
        print(f"[INFO] GitHub webhook server listening on :{GITHUB_WEBHOOK_PORT}/github")

    async def cog_unload(self):
        await self.runner.cleanup()

    async def handle_github(self, request: web.Request):
        event = request.headers.get("X-GitHub-Event", "")
        if event != "push":
            return web.Response(text="ignored")

        body = await request.text()
        data = json.loads(body)

        repo_full_name = data["repository"]["full_name"]
        commits = data.get("commits", [])

        db = await get_db()
        cur = await db.execute(
            "SELECT channel_id FROM repos WHERE repo_full_name = ?",
            (repo_full_name,),
        )
        row = await cur.fetchone()
        if not row:
            return web.Response(text="no mapping")

        channel_id = row[0]
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return web.Response(text="no channel")

        for c in commits:
            msg = c.get("message", "").strip()
            url = c.get("url")
            author = c.get("author", {}).get("username") or c.get("author", {}).get(
                "name"
            )
            await channel.send(f"`{author}` → `{msg}`\n<{url}>")

        return web.Response(text="ok")


async def setup(bot: commands.Bot):
    await bot.add_cog(GitHubIntegration(bot))
