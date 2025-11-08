import os
import discord
from discord import app_commands
from discord.ext import commands
from db import get_db

GUILD_ID = int(os.getenv("GUILD_ID", "0"))
APPLICATIONS_CHANNEL_NAME = "applications"


def is_admin(member: discord.Member, bot: commands.Bot) -> bool:
    admin_id = getattr(bot, "core_roles", {}).get("admin")
    return bool(admin_id and any(r.id == admin_id for r in member.roles))


class ApplyModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot):
        super().__init__(title="DevForge BG Application")
        self.bot = bot

        self.full_name = discord.ui.TextInput(
            label="Име и фамилия",
            max_length=100,
            required=True,
        )
        self.university = discord.ui.TextInput(
            label="Специалност / курс (пример: КСТ, 1-ви курс)",
            max_length=100,
            required=True,
        )
        self.github = discord.ui.TextInput(
            label="GitHub потребителско име (задължително)",
            max_length=100,
            required=True,
        )
        self.experience = discord.ui.TextInput(
            label="Кратко за опит (проекти, езици, интереси)",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=True,
        )

        self.add_item(self.full_name)
        self.add_item(self.university)
        self.add_item(self.github)
        self.add_item(self.experience)

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "Това трябва да се използва в сървъра.", ephemeral=True
            )
            return

        # Ensure applications channel
        apps_channel = discord.utils.get(
            guild.text_channels, name=APPLICATIONS_CHANNEL_NAME
        )
        if apps_channel is None:
            apps_channel = await guild.create_text_channel(APPLICATIONS_CHANNEL_NAME)

        content = (
            f"**Нова кандидатура от {interaction.user.mention}**\n"
            f"**Име:** {self.full_name.value}\n"
            f"**Университет:** {self.university.value}\n"
            f"**GitHub:** {self.github.value}\n"
            f"**Опит:** {self.experience.value}"
        )
        await apps_channel.send(content)

        # Save to DB
        db = await get_db()
        await db.execute(
            """
            INSERT OR REPLACE INTO users (id, github_username, is_student)
            VALUES (
                ?,
                ?,
                COALESCE((SELECT is_student FROM users WHERE id = ?), 0)
            )
            """,
            (interaction.user.id, self.github.value.strip(), interaction.user.id),
        )
        await db.commit()

        # Add Pending role
        pending_id = self.bot.core_roles.get("pending")
        if pending_id:
            pending_role = guild.get_role(pending_id)
            if pending_role and pending_role not in interaction.user.roles:
                await interaction.user.add_roles(pending_role)

        await interaction.response.send_message(
            "Кандидатурата ти е изпратена. Ако си сериозен, ще разбереш. 🙂",
            ephemeral=True,
        )


class Onboarding(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="apply",
        description="Кандидатстване за DevForge BG менторската програма.",
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def apply(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ApplyModal(self.bot))

    @app_commands.command(
        name="approve",
        description="Одобряване на кандидат (Admin only).",
    )
    @app_commands.describe(user="Кой потребител да бъде одобрен.")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def approve(self, interaction: discord.Interaction, user: discord.Member):
        if not is_admin(interaction.user, self.bot):
            await interaction.response.send_message("Нямаш права.", ephemeral=True)
            return

        guild = interaction.guild
        pending_id = self.bot.core_roles.get("pending")
        student_id = self.bot.core_roles.get("student")

        pending = guild.get_role(pending_id) if pending_id else None
        student = guild.get_role(student_id) if student_id else None

        if pending and pending in user.roles:
            await user.remove_roles(pending)
        if student and student not in user.roles:
            await user.add_roles(student)

        db = await get_db()
        await db.execute(
            "UPDATE users SET is_student = 1 WHERE id = ?",
            (user.id,),
        )
        await db.commit()

        await interaction.response.send_message(
            f"{user.mention} вече е 🎓 Student.", ephemeral=False
        )

        try:
            await user.send(
                "Одобрен си за DevForge BG. Запознай се със структурата на сървъра и се дръж като човек, който иска да стане инженер."
            )
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Onboarding(bot))
