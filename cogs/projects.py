import os
import re
import discord
from discord import app_commands
from discord.ext import commands
from db import get_db

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
REPO_RE = re.compile(r"github\.com/([^\/\s]+\/[^\/\s]+)")


def is_admin(member: discord.Member, bot: commands.Bot) -> bool:
    admin_id = getattr(bot, "core_roles", {}).get("admin")
    return bool(admin_id and any(r.id == admin_id for r in member.roles))


class Projects(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _ensure_project_channel(
        self, guild: discord.Guild, user: discord.Member, short_name: str
    ) -> discord.TextChannel:
        cat_name = f"student-{user.name}".lower()
        category = discord.utils.get(guild.categories, name=cat_name)
        if category is None:
            raise RuntimeError("Няма категория за този студент. Използвай /student_init.")

        ch_name = f"proj-{short_name}".lower().replace(" ", "-")
        channel = discord.utils.get(category.text_channels, name=ch_name)
        if channel is None:
            overwrites = category.overwrites
            channel = await guild.create_text_channel(
                ch_name, category=category, overwrites=overwrites
            )
        return channel

    @app_commands.command(
        name="project_assign", description="Създай проект за студент."
    )
    @app_commands.describe(
        user="Студентът",
        title="Име на проекта",
        repo_url="GitHub repo URL",
        difficulty="Размер / ниво (S/M/L)",
        focus="Фокус (backend, security, etc.)",
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def project_assign(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        title: str,
        repo_url: str,
        difficulty: str,
        focus: str,
    ):
        if not is_admin(interaction.user, self.bot):
            await interaction.response.send_message("Нямаш права.", ephemeral=True)
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Грешка с guild.", ephemeral=True)
            return

        m = REPO_RE.search(repo_url)
        print(m, repo_url, REPO_RE.pattern)
        if not m:
            await interaction.response.send_message(
                "Невалиден GitHub линк.", ephemeral=True
            )
            return

        repo_full_name = m.group(1)
        short_name = title.split()[0]

        try:
            channel = await self._ensure_project_channel(guild, user, short_name)
        except RuntimeError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Проект: {title}",
            description=(
                f"**Студент:** {user.mention}\n"
                f"**Repo:** {repo_url}\n"
                f"**Difficulty:** {difficulty}\n"
                f"**Focus:** {focus}\n\n"
                f"Цел: продукционно качество. Никакви тъпи commit съобщения."
            ),
            color=discord.Color.blue(),
        )
        embed.add_field(
            name="Acceptance criteria",
            value=(
                "- Стартира с една команда\n"
                "- Смислен README\n"
                "- Нормална структура\n"
                "- Без secrets в кода\n"
                "- Базови тестове или описано тестване\n"
            ),
            inline=False,
        )

        await channel.send(embed=embed)

        db = await get_db()
        cur = await db.execute(
            """
            INSERT INTO projects (student_id, channel_id, title, repo_url, status)
            VALUES (?, ?, ?, ?, 'in_progress')
            """,
            (user.id, channel.id, title, repo_url),
        )
        await db.commit()
        project_id = cur.lastrowid

        await db.execute(
            """
            INSERT OR IGNORE INTO repos (repo_full_name, channel_id)
            VALUES (?, ?)
            """,
            (repo_full_name, channel.id),
        )
        await db.commit()

        await interaction.response.send_message(
            f"Проект `{title}` създаден за {user.mention} в {channel.mention} (id={project_id}).",
            ephemeral=True,
        )

    @app_commands.command(
        name="project_mark_done",
        description="Студент: отбележи проекта като готов за ревю.",
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def project_mark_done(self, interaction: discord.Interaction):
        channel_id = interaction.channel.id
        db = await get_db()
        cur = await db.execute(
            """
            SELECT id FROM projects
            WHERE channel_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (channel_id,),
        )
        row = await cur.fetchone()
        if not row:
            await interaction.response.send_message(
                "Това не е проектен канал.", ephemeral=True
            )
            return

        await db.execute(
            """
            UPDATE projects
            SET status = 'awaiting_review', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (row[0],),
        )
        await db.commit()

        await interaction.response.send_message(
            "Маркирано като 'готово за ревю'. Очаквай обратна връзка.",
            ephemeral=True,
        )

    @app_commands.command(
        name="project_feedback",
        description="Менторски feedback за текущия проектен канал.",
    )
    @app_commands.describe(issues="Проблеми, насоки, следващи стъпки.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def project_feedback(
        self, interaction: discord.Interaction, issues: str
    ):
        if not is_admin(interaction.user, self.bot):
            await interaction.response.send_message("Нямаш права.", ephemeral=True)
            return

        channel_id = interaction.channel.id
        db = await get_db()
        cur = await db.execute(
            """
            SELECT id FROM projects
            WHERE channel_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (channel_id,),
        )
        row = await cur.fetchone()
        if not row:
            await interaction.response.send_message(
                "Това не е проектен канал.", ephemeral=True
            )
            return

        await db.execute(
            """
            UPDATE projects
            SET status = 'in_progress', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (row[0],),
        )
        await db.commit()

        await interaction.channel.send(
            f"**Review от {interaction.user.mention}:**\n{issues}\n\n"
            f"Статус: 🔁 Iteration in progress."
        )
        await interaction.response.send_message(
            "Feedback публикуван.", ephemeral=True
        )

    @app_commands.command(
        name="project_approve",
        description="Маркирай проекта в този канал като production-ready.",
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def project_approve(self, interaction: discord.Interaction):
        if not is_admin(interaction.user, self.bot):
            await interaction.response.send_message("Нямаш права.", ephemeral=True)
            return

        channel_id = interaction.channel.id
        db = await get_db()
        cur = await db.execute(
            """
            SELECT id, student_id, title FROM projects
            WHERE channel_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (channel_id,),
        )
        row = await cur.fetchone()
        if not row:
            await interaction.response.send_message(
                "Това не е проектен канал.", ephemeral=True
            )
            return

        project_id, student_id, title = row

        await db.execute(
            """
            UPDATE projects
            SET status = 'approved', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (project_id,),
        )
        await db.commit()

        guild = interaction.guild
        student = guild.get_member(student_id) if guild else None

        if student:
            await interaction.channel.send(
                f"✅ {student.mention}, проектът **'{title}'** е одобрен като production-ready.\n"
                f"Спокойно го слагай в CV/LinkedIn."
            )

        await interaction.response.send_message(
            "Проектът е маркиран като одобрен.", ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Projects(bot))
