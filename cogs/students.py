import os
import discord
from discord import app_commands
from discord.ext import commands
from db import get_db

GUILD_ID = int(os.getenv("GUILD_ID", "0"))


def is_admin(member: discord.Member, bot: commands.Bot) -> bool:
    admin_id = getattr(bot, "core_roles", {}).get("admin")
    return bool(admin_id and any(r.id == admin_id for r in member.roles))


class Students(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="student_init",
        description="Създай категория и лично пространство за студент.",
    )
    @app_commands.describe(user="Студентът")
    @app_commands.guilds(discord.Object(id=GUILD_ID))
    async def student_init(self, interaction: discord.Interaction, user: discord.Member):
        if not is_admin(interaction.user, self.bot):
            await interaction.response.send_message("Нямаш права.", ephemeral=True)
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Грешка с guild.", ephemeral=True)
            return

        cat_name = f"student-{user.name}".lower()
        category = discord.utils.get(guild.categories, name=cat_name)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
        }

        if category is None:
            category = await guild.create_category(cat_name, overwrites=overwrites)
        else:
            await category.edit(overwrites=overwrites)

        profile = discord.utils.get(category.text_channels, name="profile")
        if profile is None:
            profile = await guild.create_text_channel("profile", category=category)

        await profile.send(
            f"{user.mention}, това е твоето лично пространство.\n"
            f"Напиши тук:\n"
            f"- какъв опит имаш\n"
            f"- какво искаш да учиш / строиш\n"
            f"- колко часа седмично можеш да отделяш\n"
            f"- линк към GitHub."
        )

        db = await get_db()
        await db.execute(
            "INSERT OR IGNORE INTO users (id, is_student) VALUES (?, 1)",
            (user.id,),
        )
        await db.commit()

        await interaction.response.send_message(
            f"Инициализирано пространство за {user.mention}.",
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Students(bot))
