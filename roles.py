import discord

async def ensure_role(
    guild: discord.Guild,
    name: str,
    color: discord.Color = discord.Color.default(),
    permissions: discord.Permissions | None = None,
    mentionable: bool = True
) -> discord.Role:
    role = discord.utils.get(guild.roles, name=name)
    if role:
        return role

    if permissions is None:
        permissions = discord.Permissions.none()

    role = await guild.create_role(
        name=name,
        colour=color,
        permissions=permissions,
        mentionable=mentionable,
        reason=f"DevForge BG core role '{name}' auto-created."
    )
    return role
