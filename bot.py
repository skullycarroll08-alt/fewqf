# FULL UPDATED BOT - /giveaway-info INCLUDED
# This is a full copy of the existing bot with the giveaway-info command explicitly marked.

print("BOT FILE STARTED")

import os
import asyncio
import json
import random
from datetime import datetime, timezone, timedelta

import discord
from discord import app_commands
from discord.ext import commands
OWNER_ID = 1533109227709665423
INVITE_CHANNEL_ID = 1534340963189919965


# ============================================================
# SETTINGS
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")

ADMIN_ROLE_NAME = "Admin"
MOD_LOG_CHANNEL_NAME = "mod-logs"

SCHEDULE_FILE = "scheduled_messages.json"
WARNINGS_FILE = "warnings.json"
XP_FILE = "xp.json"
GIVEAWAYS_FILE = "giveaways.json"
XP_COOLDOWN_SECONDS = 10
XP_MIN = 10
XP_MAX = 20


# ============================================================
# BOT SETUP
# ============================================================

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

active_giveaways = {}
scheduled_messages = {}
warnings = {}
giveaway_records = {}

# Users blocked from winning giveaways.
# Format: {"USER_ID": {"reason": "...", "blocked_by": USER_ID}}
GIVEAWAY_BLOCKS_FILE = "giveaway_blocks.json"
giveaway_blocks = {}


# ============================================================
# FILE HELPERS
# ============================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as e:

        print(
            f"Could not load {filename}: {e}"
        )

        return default


def save_json(filename, data):

    try:

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )

    except Exception as e:

        print(
            f"Could not save {filename}: {e}"
        )


scheduled_messages = load_json(
    SCHEDULE_FILE,
    {}
)

if not isinstance(scheduled_messages, dict):
    print("⚠️ scheduled_messages.json was not a dictionary. Resetting it.")
    scheduled_messages = {}
    save_json(
        SCHEDULE_FILE,
        scheduled_messages
    )

warnings = load_json(
    WARNINGS_FILE,
    {}
)

user_xp = load_json(
    XP_FILE,
    {}
)

giveaway_records = load_json(
    GIVEAWAYS_FILE,
    {}
)

if not isinstance(giveaway_records, dict):
    giveaway_records = {}
    save_json(GIVEAWAYS_FILE, giveaway_records)

if not isinstance(user_xp, dict):
    user_xp = {}
    save_json(XP_FILE, user_xp)

xp_cooldowns = {}


# Load persistent giveaway winner blocks after the JSON helpers exist.
giveaway_blocks = load_json(GIVEAWAY_BLOCKS_FILE, {})

def save_giveaway_blocks():
    save_json(GIVEAWAY_BLOCKS_FILE, giveaway_blocks)

def get_giveaway_block(user_id):
    return giveaway_blocks.get(str(user_id))

def get_eligible_giveaway_entries(view, exclude_ids=None):
    excluded = set(exclude_ids or [])
    return [
        user_id
        for user_id in view.entries
        if user_id not in excluded and get_giveaway_block(user_id) is None
    ]

# ============================================================
# ============================================================
# ADMIN ROLE CHECK
# ============================================================

def is_admin_role():

    async def predicate(
        interaction: discord.Interaction
    ):

        if interaction.guild is None:

            raise app_commands.CheckFailure(
                "This command can only be used in a server."
            )

        member = interaction.user

        if not isinstance(
            member,
            discord.Member
        ):

            raise app_commands.CheckFailure(
                "Could not determine your server roles."
            )

        if member.id == interaction.guild.owner_id:
            return True

        for role in member.roles:

            if role.name.lower() == ADMIN_ROLE_NAME.lower():
                return True

        raise app_commands.CheckFailure(
            "You need the Admin role to use this command."
        )

    return app_commands.check(
        predicate
    )

# ============================================================
# /bulkrole

# ============================================================

bulkrole_group = app_commands.Group(
    name="bulkrole",
    description="Manage a role for all members"
)


@bulkrole_group.command(
    name="add",
    description="Add a role to all members"
)
@app_commands.describe(
    role="Role to give to all members"
)
@is_admin_role()
async def bulkrole_add(
    interaction: discord.Interaction,
    role: discord.Role
):
    if role.is_default():
        await interaction.response.send_message(
            "❌ You can't add the @everyone role.",
            ephemeral=True
        )
        return

    if role.managed:
        await interaction.response.send_message(
            "❌ You can't manually assign a managed/integration role.",
            ephemeral=True
        )
        return

    bot_member = interaction.guild.me

    if bot_member is None:
        await interaction.response.send_message(
            "❌ I couldn't determine my role.",
            ephemeral=True
        )
        return

    if role >= bot_member.top_role:
        await interaction.response.send_message(
            "❌ That role is equal to or higher than my highest role.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    added = 0
    skipped = 0

    members = [
        member
        async for member in interaction.guild.fetch_members(limit=None)
    ]

    for member in members:
        if member.bot:
            skipped += 1
            continue

        if role in member.roles:
            skipped += 1
            continue

        if member.top_role >= bot_member.top_role:
            skipped += 1
            continue

        try:
            await member.add_roles(
                role,
                reason=f"Bulk role add by {interaction.user}"
            )
            added += 1
        except (discord.Forbidden, discord.HTTPException):
            skipped += 1

    await interaction.followup.send(
        f"✅ Added {role.mention} to **{added}** members.\n"
        f"⚠️ Skipped **{skipped}** members."
    )


@bulkrole_group.command(
    name="remove",
    description="Remove a role from all members"
)
@app_commands.describe(
    role="Role to remove from all members"
)
@is_admin_role()
async def bulkrole_remove(
    interaction: discord.Interaction,
    role: discord.Role
):
    if role.is_default():
        await interaction.response.send_message(
            "❌ You can't remove the @everyone role.",
            ephemeral=True
        )
        return

    if role.managed:
        await interaction.response.send_message(
            "❌ You can't manually remove a managed/integration role.",
            ephemeral=True
        )
        return

    bot_member = interaction.guild.me

    if bot_member is None:
        await interaction.response.send_message(
            "❌ I couldn't determine my role.",
            ephemeral=True
        )
        return

    if role >= bot_member.top_role:
        await interaction.response.send_message(
            "❌ That role is equal to or higher than my highest role.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    removed = 0
    skipped = 0

    members = [
        member
        async for member in interaction.guild.fetch_members(limit=None)
    ]

    for member in members:
        if member.bot:
            skipped += 1
            continue

        if role not in member.roles:
            continue

        if member.id == interaction.guild.owner_id:
            skipped += 1
            continue

        if member.top_role >= bot_member.top_role:
            skipped += 1
            continue

        try:
            await member.remove_roles(
                role,
                reason=f"Bulk role remove by {interaction.user}"
            )
            removed += 1
        except (discord.Forbidden, discord.HTTPException):
            skipped += 1

    await interaction.followup.send(
        f"✅ Removed {role.mention} from **{removed}** members.\n"
        f"⚠️ Skipped **{skipped}** members."
    )


bot.tree.add_command(bulkrole_group)


# ============================================================
# /say
# ============================================================

@bot.tree.command(
    name="say",
    description="Send a message as Vkingvx Bot"
)
@app_commands.describe(
    channel="Channel where the message should be sent",
    message="Message to send (use \n for line breaks)"
)
@is_admin_role()
async def say(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message: str
):

    try:

        # Convert typed \n into actual line breaks
        message = message.replace("\\n", "\n")

        await channel.send(
            message,
            allowed_mentions=discord.AllowedMentions(
                everyone=True,
                users=True,
                roles=True,
                replied_user=False
            )
        )

        await interaction.response.send_message(
            f"✅ Message sent to {channel.mention}!",
            ephemeral=True
        )

        await mod_log(
            interaction.guild,
            "📢 Message Sent",
            f"**Moderator:** {interaction.user.mention}\n"
            f"**Channel:** {channel.mention}\n"
            f"**Message:** {message}",
            discord.Color.blurple()
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I don't have permission to send messages there.",
            ephemeral=True
        )

    except discord.HTTPException as e:

        await interaction.response.send_message(
            f"❌ Discord rejected the message: {e}",
            ephemeral=True
        )


# ============================================================
# /kick
# ============================================================

@bot.tree.command(
    name="kick",
    description="Kick a member from the server"
)
@app_commands.describe(
    member="Member to kick",
    reason="Reason for the kick"
)
@is_admin_role()
async def kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str | None = None
):

    if member == interaction.user:

        await interaction.response.send_message(
            "❌ You can't kick yourself.",
            ephemeral=True
        )

        return

    if member == interaction.guild.owner:

        await interaction.response.send_message(
            "❌ You can't kick the server owner.",
            ephemeral=True
        )

        return

    if (
        member.top_role >= interaction.user.top_role
        and interaction.user.id != interaction.guild.owner_id
    ):

        await interaction.response.send_message(
            "❌ You can't kick someone with an equal or higher role.",
            ephemeral=True
        )

        return

    bot_member = interaction.guild.me

    if bot_member is None:

        await interaction.response.send_message(
            "❌ I couldn't determine my permissions.",
            ephemeral=True
        )

        return

    if member.top_role >= bot_member.top_role:

        await interaction.response.send_message(
            "❌ My highest role is not high enough to kick that member.",
            ephemeral=True
        )

        return

    try:

        await member.kick(
            reason=reason
        )

        await interaction.response.send_message(
            f"✅ {member} was kicked.",
            ephemeral=True
        )

        await mod_log(
            interaction.guild,
            "🔨 Member Kicked",
            f"**Member:** {member.mention}\n"
            f"**Moderator:** {interaction.user.mention}\n"
            f"**Reason:** {reason or 'No reason provided'}",
            discord.Color.orange()
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I don't have permission to kick that member.",
            ephemeral=True
        )

    except discord.HTTPException as e:

        await interaction.response.send_message(
            f"❌ Discord error: {e}",
            ephemeral=True
        )


# ============================================================
# /ban
# ============================================================

@bot.tree.command(
    name="ban",
    description="Ban a member from the server"
)
@app_commands.describe(
    member="Member to ban",
    reason="Reason for the ban"
)
@is_admin_role()
async def ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str | None = None
):

    if member == interaction.user:

        await interaction.response.send_message(
            "❌ You can't ban yourself.",
            ephemeral=True
        )

        return

    if member == interaction.guild.owner:

        await interaction.response.send_message(
            "❌ You can't ban the server owner.",
            ephemeral=True
        )

        return

    if (
        member.top_role >= interaction.user.top_role
        and interaction.user.id != interaction.guild.owner_id
    ):

        await interaction.response.send_message(
            "❌ You can't ban someone with an equal or higher role.",
            ephemeral=True
        )

        return

    bot_member = interaction.guild.me

    if bot_member is None:

        await interaction.response.send_message(
            "❌ I couldn't determine my permissions.",
            ephemeral=True
        )

        return

    if member.top_role >= bot_member.top_role:

        await interaction.response.send_message(
            "❌ My highest role is not high enough to ban that member.",
            ephemeral=True
        )

        return

    try:

        await member.ban(
            reason=reason,
            delete_message_seconds=0
        )

        await interaction.response.send_message(
            f"✅ {member} was banned.",
            ephemeral=True
        )

        await mod_log(
            interaction.guild,
            "🔨 Member Banned",
            f"**Member:** {member.mention}\n"
            f"**Moderator:** {interaction.user.mention}\n"
            f"**Reason:** {reason or 'No reason provided'}",
            discord.Color.red()
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I don't have permission to ban that member.",
            ephemeral=True
        )

    except discord.HTTPException as e:

        await interaction.response.send_message(
            f"❌ Discord error: {e}",
            ephemeral=True
        )


# ============================================================
# /warn
# ============================================================

@bot.tree.command(
    name="warn",
    description="Warn a member"
)
@app_commands.describe(
    member="Member to warn",
    reason="Reason for the warning"
)
@is_admin_role()
async def warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str
):

    if member == interaction.user:

        await interaction.response.send_message(
            "❌ You can't warn yourself.",
            ephemeral=True
        )

        return

    if member == interaction.guild.owner:

        await interaction.response.send_message(
            "❌ You can't warn the server owner.",
            ephemeral=True
        )

        return

    if member.bot:

        await interaction.response.send_message(
            "❌ You can't warn a bot.",
            ephemeral=True
        )

        return

    guild_id = str(
        interaction.guild.id
    )

    user_id = str(
        member.id
    )

    if guild_id not in warnings:
        warnings[guild_id] = {}

    if user_id not in warnings[guild_id]:
        warnings[guild_id][user_id] = []

    warning_number = (
        len(warnings[guild_id][user_id]) + 1
    )

    warning_data = {
        "reason": reason,
        "moderator_id": interaction.user.id,
        "moderator_name": str(interaction.user),
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat()
    }

    warnings[guild_id][user_id].append(
        warning_data
    )

    save_json(
        WARNINGS_FILE,
        warnings
    )

    warning_count = len(
        warnings[guild_id][user_id]
    )

    await interaction.response.send_message(
        f"⚠️ **{member}** has been warned.\n\n"
        f"**Warning:** #{warning_number}\n"
        f"**Reason:** {reason}\n"
        f"**Total warnings:** {warning_count}",
        ephemeral=True
    )

    await mod_log(
        interaction.guild,
        "⚠️ Member Warned",
        f"**Member:** {member.mention}\n"
        f"**Moderator:** {interaction.user.mention}\n"
        f"**Warning:** #{warning_number}\n"
        f"**Reason:** {reason}\n"
        f"**Total warnings:** {warning_count}",
        discord.Color.orange()
    )

    try:

        await member.send(
            f"⚠️ **You have been warned in {interaction.guild.name}.**\n\n"
            f"**Reason:** {reason}\n"
            f"**Total warnings:** {warning_count}"
        )

    except discord.HTTPException:
        pass


# ============================================================
# /warnings
# ============================================================

@bot.tree.command(
    name="warnings",
    description="View a member's warnings"
)
@app_commands.describe(
    member="Member whose warnings you want to view"
)
@is_admin_role()
async def warnings_command(
    interaction: discord.Interaction,
    member: discord.Member
):

    guild_id = str(
        interaction.guild.id
    )

    user_id = str(
        member.id
    )

    user_warnings = warnings.get(
        guild_id,
        {}
    ).get(
        user_id,
        []
    )

    if not user_warnings:

        await interaction.response.send_message(
            f"✅ **{member}** has no warnings.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title=f"⚠️ Warnings — {member}",
        color=discord.Color.orange()
    )

    for index, warning_data in enumerate(
        user_warnings,
        start=1
    ):

        reason = warning_data.get(
            "reason",
            "No reason provided"
        )

        moderator = warning_data.get(
            "moderator_name",
            "Unknown"
        )

        timestamp = warning_data.get(
            "timestamp"
        )

        if timestamp:

            try:

                dt = datetime.fromisoformat(
                    timestamp
                )

                time_text = discord.utils.format_dt(
                    dt,
                    style="R"
                )

            except Exception:

                time_text = "Unknown time"

        else:

            time_text = "Unknown time"

        embed.add_field(
            name=f"Warning #{index}",
            value=(
                f"**Reason:** {reason}\n"
                f"**Moderator:** {moderator}\n"
                f"**When:** {time_text}"
            ),
            inline=False
        )

    embed.set_footer(
        text=f"Total warnings: {len(user_warnings)}"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# /removewarn
# ============================================================

@bot.tree.command(
    name="removewarn",
    description="Remove a warning from a member"
)
@app_commands.describe(
    member="Member whose warning you want to remove",
    warning_number="Warning number to remove"
)
@is_admin_role()
async def removewarn(
    interaction: discord.Interaction,
    member: discord.Member,
    warning_number: int
):

    if warning_number < 1:

        await interaction.response.send_message(
            "❌ Warning number must be 1 or higher.",
            ephemeral=True
        )

        return

    guild_id = str(
        interaction.guild.id
    )

    user_id = str(
        member.id
    )

    user_warnings = warnings.get(
        guild_id,
        {}
    ).get(
        user_id,
        []
    )

    if not user_warnings:

        await interaction.response.send_message(
            f"❌ **{member}** has no warnings.",
            ephemeral=True
        )

        return

    if warning_number > len(user_warnings):

        await interaction.response.send_message(
            f"❌ **{member}** only has "
            f"{len(user_warnings)} warning(s).",
            ephemeral=True
        )

        return

    removed_warning = user_warnings.pop(
        warning_number - 1
    )

    warnings[guild_id][user_id] = user_warnings

    save_json(
        WARNINGS_FILE,
        warnings
    )

    reason = removed_warning.get(
        "reason",
        "No reason provided"
    )

    await interaction.response.send_message(
        f"✅ Removed **Warning #{warning_number}** "
        f"from **{member}**.\n\n"
        f"**Reason was:** {reason}\n"
        f"**Remaining warnings:** {len(user_warnings)}",
        ephemeral=True
    )

    await mod_log(
        interaction.guild,
        "🗑️ Warning Removed",
        f"**Member:** {member.mention}\n"
        f"**Moderator:** {interaction.user.mention}\n"
        f"**Warning:** #{warning_number}\n"
        f"**Reason:** {reason}\n"
        f"**Remaining warnings:** {len(user_warnings)}",
        discord.Color.green()
    )


# ============================================================
# /timeout
# ============================================================

@bot.tree.command(
    name="timeout",
    description="Timeout a member"
)
@app_commands.describe(
    member="Member to timeout",
    minutes="How many minutes to timeout them",
    reason="Reason for the timeout"
)
@is_admin_role()
async def timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    minutes: int,
    reason: str | None = None
):

    if member == interaction.user:

        await interaction.response.send_message(
            "❌ You can't timeout yourself.",
            ephemeral=True
        )

        return

    if member == interaction.guild.owner:

        await interaction.response.send_message(
            "❌ You can't timeout the server owner.",
            ephemeral=True
        )

        return

    if member.bot:

        await interaction.response.send_message(
            "❌ You can't timeout a bot.",
            ephemeral=True
        )

        return

    if minutes < 1:

        await interaction.response.send_message(
            "❌ Timeout must be at least 1 minute.",
            ephemeral=True
        )

        return

    if minutes > 40320:

        await interaction.response.send_message(
            "❌ Timeout can't be longer than 28 days.",
            ephemeral=True
        )

        return

    if (
        member.top_role >= interaction.user.top_role
        and interaction.user.id != interaction.guild.owner_id
    ):

        await interaction.response.send_message(
            "❌ You can't timeout someone with an equal or higher role.",
            ephemeral=True
        )

        return

    bot_member = interaction.guild.me

    if bot_member is None:

        await interaction.response.send_message(
            "❌ I couldn't determine my permissions.",
            ephemeral=True
        )

        return

    if member.top_role >= bot_member.top_role:

        await interaction.response.send_message(
            "❌ My highest role is not high enough to timeout that member.",
            ephemeral=True
        )

        return

    try:

        timeout_until = (
            discord.utils.utcnow()
            + timedelta(minutes=minutes)
        )

        await member.timeout(
            timeout_until,
            reason=reason
        )

        await interaction.response.send_message(
            f"🔇 **{member}** has been timed out for "
            f"**{minutes} minute(s)**.",
            ephemeral=True
        )

        await mod_log(
            interaction.guild,
            "🔇 Member Timed Out",
            f"**Member:** {member.mention}\n"
            f"**Moderator:** {interaction.user.mention}\n"
            f"**Duration:** {minutes} minute(s)\n"
            f"**Reason:** {reason or 'No reason provided'}",
            discord.Color.orange()
        )

        try:

            await member.send(
                f"🔇 You have been timed out in "
                f"**{interaction.guild.name}**.\n\n"
                f"**Duration:** {minutes} minute(s)\n"
                f"**Reason:** {reason or 'No reason provided'}"
            )

        except discord.HTTPException:
            pass

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I don't have permission to timeout that member.",
            ephemeral=True
        )

    except discord.HTTPException as e:

        await interaction.response.send_message(
            f"❌ Discord error: {e}",
            ephemeral=True
        )


# ============================================================
# /untimeout
# ============================================================

@bot.tree.command(
    name="untimeout",
    description="Remove a member's timeout"
)
@app_commands.describe(
    member="Member to remove timeout from",
    reason="Reason for removing the timeout"
)
@is_admin_role()
async def untimeout(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str | None = None
):

    if member == interaction.guild.owner:

        await interaction.response.send_message(
            "❌ The server owner cannot be timed out.",
            ephemeral=True
        )

        return

    if (
        member.top_role >= interaction.user.top_role
        and interaction.user.id != interaction.guild.owner_id
    ):

        await interaction.response.send_message(
            "❌ You can't remove a timeout from someone with an equal or higher role.",
            ephemeral=True
        )

        return

    bot_member = interaction.guild.me

    if bot_member is None:

        await interaction.response.send_message(
            "❌ I couldn't determine my permissions.",
            ephemeral=True
        )

        return

    if member.top_role >= bot_member.top_role:

        await interaction.response.send_message(
            "❌ My highest role is not high enough to manage that member.",
            ephemeral=True
        )

        return

    if member.timed_out_until is None:

        await interaction.response.send_message(
            f"✅ **{member}** is not currently timed out.",
            ephemeral=True
        )

        return

    try:

        await member.timeout(
            None,
            reason=reason or "Timeout removed"
        )

        await interaction.response.send_message(
            f"🔊 **{member}**'s timeout has been removed.",
            ephemeral=True
        )

        await mod_log(
            interaction.guild,
            "🔊 Timeout Removed",
            f"**Member:** {member.mention}\n"
            f"**Moderator:** {interaction.user.mention}\n"
            f"**Reason:** {reason or 'No reason provided'}",
            discord.Color.green()
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I don't have permission to remove that timeout.",
            ephemeral=True
        )

    except discord.HTTPException as e:

        await interaction.response.send_message(
            f"❌ Discord error: {e}",
            ephemeral=True
        )

# ============================================================
# /endgiveaway
# ============================================================

@bot.tree.command(
    name="endgiveaway",
    description="End an active giveaway immediately"
)
@app_commands.describe(
    message_id="The message ID of the giveaway"
)
@is_admin_role()
async def endgiveaway(
    interaction: discord.Interaction,
    message_id: str
):

    try:

        giveaway_id = int(
            message_id
        )

    except ValueError:

        await interaction.response.send_message(
            "❌ Invalid message ID.",
            ephemeral=True
        )

        return

    view = active_giveaways.get(
        giveaway_id
    )

    # Support giveaways created before a bot restart/update.
    if view is None:
        old_message = None

        for channel in interaction.guild.text_channels:
            try:
                old_message = await channel.fetch_message(giveaway_id)
                break
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                continue

        if old_message is None:
            await interaction.response.send_message(
                "❌ I couldn't find that giveaway message in this server.",
                ephemeral=True
            )
            return

        disabled_view = discord.ui.View(timeout=None)
        disabled_view.add_item(
            discord.ui.Button(
                label="🎉 Giveaway Ended",
                style=discord.ButtonStyle.secondary,
                custom_id=f"vkingvx_ended_{giveaway_id}",
                disabled=True
            )
        )

        old_embed = (
            old_message.embeds[0]
            if old_message.embeds
            else discord.Embed(
                title="🎉 GIVEAWAY ENDED 🎉",
                color=discord.Color.red()
            )
        )
        old_embed.color = discord.Color.red()
        old_embed.add_field(
            name="🔴 Status",
            value="**Ended early by a moderator.**",
            inline=False
        )
        old_embed.set_footer(
            text=f"Giveaway ended early • ID: {giveaway_id}"
        )

        try:
            await old_message.edit(
                embed=old_embed,
                view=disabled_view
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"❌ I found the giveaway, but couldn't edit it: {e}",
                ephemeral=True
            )
            return

        await interaction.response.send_message(
            f"✅ Giveaway `{giveaway_id}` was ended early.\n"
            f"🔗 [Jump to Giveaway]({old_message.jump_url})",
            ephemeral=True
        )
        return

    if view.finished:

        await interaction.response.send_message(
            "❌ That giveaway has already ended.",
            ephemeral=True
        )

        return

    view.finished = True

    for item in view.children:

        item.disabled = True

    winner_text = None

    eligible_entries = get_eligible_giveaway_entries(view)

    if eligible_entries:

        winner_id = random.choice(
            eligible_entries
        )

        view.winner_id = winner_id

        winner = interaction.guild.get_member(
            winner_id
        )

        if winner:

            winner_text = winner.mention

        else:

            winner_text = f"<@{winner_id}>"

        result_embed = discord.Embed(
            title="🎉 GIVEAWAY ENDED 🎉",
            description=(
                f"## 🎁 {view.prize}\n\n"
                f"🏆 **Winner:** {winner_text}\n\n"
                f"🎟️ **Total entries:** "
                f"{len(view.entries)}"
            ),
            color=discord.Color.green()
        )

    else:

        result_embed = discord.Embed(
            title="🎉 GIVEAWAY ENDED 🎉",
            description=(
                f"## 🎁 {view.prize}\n\n"
                "😢 **Nobody entered this giveaway.**"
            ),
            color=discord.Color.red()
        )

    result_embed.add_field(
        name="👑 Host",
        value=view.host.mention,
        inline=True
    )

    result_embed.add_field(
        name="🎟️ Entries",
        value=f"**{len(view.entries)}**",
        inline=True
    )

    if view.photo:

        result_embed.set_image(
            url=view.photo
        )

    try:

        await view.message.edit(
            embed=result_embed,
            view=view
        )

    except discord.HTTPException as e:

        print(
            f"❌ Failed to update giveaway message: {e}"
        )

    active_giveaways.pop(
        giveaway_id,
        None
    )

    delete_giveaway_record(giveaway_id)

    await interaction.response.send_message(
        "✅ Giveaway ended!",
        ephemeral=True
    )

    await mod_log(
        interaction.guild,
        "🏁 Giveaway Manually Ended",
        f"**Prize:** {view.prize}\n"
        f"**Moderator:** {interaction.user.mention}\n"
        f"**Entries:** {len(view.entries)}\n"
        f"**Winner:** {winner_text or 'Nobody entered'}",
        discord.Color.gold()
    )

    if winner_text:

        try:

            await interaction.channel.send(
                f"🎉 Congratulations {winner_text}!\n"
                f"You won **{view.prize}**! 🏆",
                allowed_mentions=discord.AllowedMentions(
                    users=True
                )
            )

        except discord.HTTPException:

            pass

# ============================================================
# /userinfo
# ============================================================

@bot.tree.command(
    name="userinfo",
    description="View information about a member"
)
@app_commands.describe(
    member="Member whose information you want to view"
)
@is_admin_role()
async def userinfo(
    interaction: discord.Interaction,
    member: discord.Member
):

    created_at = discord.utils.format_dt(
        member.created_at,
        style="F"
    )

    joined_at = (
        discord.utils.format_dt(
            member.joined_at,
            style="F"
        )
        if member.joined_at
        else "Unknown"
    )

    roles = [
        role.mention
        for role in member.roles
        if role != interaction.guild.default_role
    ]

    if roles:

        roles_text = " ".join(
            roles
        )

        if len(roles_text) > 1000:
            roles_text = (
                f"{len(roles)} roles"
            )

    else:

        roles_text = "None"

    if member.timed_out_until:

        timeout_text = discord.utils.format_dt(
            member.timed_out_until,
            style="R"
        )

    else:

        timeout_text = "Not timed out"

    status = str(
        member.status
    ).title()

    embed = discord.Embed(
        title=f"👤 User Information — {member}",
        color=member.color
        if member.color != discord.Color.default()
        else discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="👤 User",
        value=(
            f"{member.mention}\n"
            f"**Username:** `{member}`\n"
            f"**Display Name:** `{member.display_name}`"
        ),
        inline=False
    )

    embed.add_field(
        name="🆔 IDs",
        value=(
            f"**User ID:** `{member.id}`\n"
            f"**Server ID:** `{interaction.guild.id}`"
        ),
        inline=False
    )

    embed.add_field(
        name="📅 Dates",
        value=(
            f"**Account Created:** {created_at}\n"
            f"**Joined Server:** {joined_at}"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 Status",
        value=(
            f"**Status:** `{status}`\n"
            f"**Bot:** `{member.bot}`\n"
            f"**Timeout:** {timeout_text}"
        ),
        inline=False
    )

    embed.add_field(
        name=f"🎭 Roles ({len(roles)})",
        value=roles_text,
        inline=False
    )

    embed.set_footer(
        text=f"Requested by {interaction.user}"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )

# ============================================================
# /ping
# ============================================================

@bot.tree.command(
    name="ping",
    description="Ping a member a limited number of times"
)
@app_commands.describe(
    member="Member to ping",
    amount="Number of times to ping (1-50)"
)
@is_admin_role()
async def ping(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: int
):

    if amount < 1 or amount > 50:

        await interaction.response.send_message(
            "❌ Amount must be between **1 and 50**.",
            ephemeral=True
        )

        return

    if member.bot:

        await interaction.response.send_message(
            "❌ You can't ping a bot with this command.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        f"✅ Pinging {member.mention} **{amount}** time(s).",
        ephemeral=True
    )

    for _ in range(amount):

        try:

            await interaction.channel.send(
                member.mention,
                allowed_mentions=discord.AllowedMentions(
                    users=[member],
                    replied_user=False
                )
            )

            if amount > 1:
                await asyncio.sleep(0.1)

        except discord.Forbidden:

            break

        except discord.HTTPException as e:

            print(
                f"❌ Ping command error: {e}"
            )

            break

    await mod_log(
        interaction.guild,
        "📣 Member Ping",
        f"**Member:** {member.mention}\n"
        f"**Moderator:** {interaction.user.mention}\n"
        f"**Amount:** {amount}\n"
        f"**Channel:** {interaction.channel.mention}",
        discord.Color.blurple()
    )

# ============================================================
# ============================================================
# /fakeban
# ============================================================

@bot.tree.command(
    name="fakeban",
    description="Pretend to ban a member"
)
@app_commands.describe(
    member="Member to fake ban",
    reason="Fake ban reason"
)
@is_admin_role()
async def fakeban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str | None = None
):

    if member == interaction.user:

        await interaction.response.send_message(
            "❌ You can't fake ban yourself.",
            ephemeral=True
        )

        return

    if member.bot:

        await interaction.response.send_message(
            "❌ You can't fake ban a bot.",
            ephemeral=True
        )

        return

    fake_reason = reason or "Breaking the server rules"

    await interaction.response.send_message(
        f"🔨 **{member.mention} has been banned from the server.**\n\n"
        f"**Reason:** {fake_reason}",
        allowed_mentions=discord.AllowedMentions(
            users=[member],
            replied_user=False
        )
    )

    await asyncio.sleep(3)

    try:

        await member.send(
            f"😭 **SIKE!**\n\n"
            f"You were **NOT actually banned** from "
            f"**{interaction.guild.name}**. 💀\n\n"
            f"That was a fake ban prank 😂"
        )

    except discord.Forbidden:

        print(
            f"❌ Could not DM {member} because their DMs are closed."
        )

    except discord.HTTPException as e:

        print(
            f"❌ Failed to send fake ban DM: {e}"
        )

    await mod_log(
        interaction.guild,
        "😂 Fake Ban",
        f"**Member:** {member.mention}\n"
        f"**Moderator:** {interaction.user.mention}\n"
        f"**Fake Reason:** {fake_reason}",
        discord.Color.gold()
    )
# ============================================================
# GIVEAWAY WINNER BLOCKS
# ============================================================

@bot.tree.command(
    name="block-giveaway-winner",
    description="Block a member from winning giveaways"
)
@app_commands.describe(
    member="The member to block from winning giveaways",
    reason="Why this member is blocked"
)
@is_admin_role()
async def block_giveaway_winner(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str
):
    reason = reason.strip()

    if not reason:
        await interaction.response.send_message(
            "❌ You must provide a reason.",
            ephemeral=True
        )
        return

    giveaway_blocks[str(member.id)] = {
        "reason": reason,
        "blocked_by": interaction.user.id
    }
    save_giveaway_blocks()

    await interaction.response.send_message(
        f"🚫 **{member.mention} is now blocked from winning giveaways.**\n"
        f"**Reason:** {reason}",
        ephemeral=True
    )

    await mod_log(
        interaction.guild,
        "🚫 Giveaway Winner Blocked",
        f"**Member:** {member.mention}\n"
        f"**Blocked by:** {interaction.user.mention}\n"
        f"**Reason:** {reason}",
        discord.Color.red()
    )


@bot.tree.command(
    name="unblock-giveaway-winner",
    description="Allow a member to win giveaways again"
)
@app_commands.describe(
    member="The member to unblock"
)
@is_admin_role()
async def unblock_giveaway_winner(
    interaction: discord.Interaction,
    member: discord.Member
):
    if str(member.id) not in giveaway_blocks:
        await interaction.response.send_message(
            f"ℹ️ {member.mention} is not blocked from winning giveaways.",
            ephemeral=True
        )
        return

    giveaway_blocks.pop(str(member.id), None)
    save_giveaway_blocks()

    await interaction.response.send_message(
        f"✅ **{member.mention} can win giveaways again.**",
        ephemeral=True
    )

    await mod_log(
        interaction.guild,
        "✅ Giveaway Winner Unblocked",
        f"**Member:** {member.mention}\n"
        f"**Unblocked by:** {interaction.user.mention}",
        discord.Color.green()
    )


@bot.tree.command(
    name="giveaway-blocks",
    description="View members blocked from winning giveaways"
)
@is_admin_role()
async def giveaway_blocks_command(
    interaction: discord.Interaction
):
    if not giveaway_blocks:
        await interaction.response.send_message(
            "✅ **Nobody is currently blocked from winning giveaways.**",
            ephemeral=True
        )
        return

    lines = []
    for user_id, data in giveaway_blocks.items():
        member = interaction.guild.get_member(int(user_id))
        name = member.mention if member else f"<@{user_id}>"
        reason = data.get("reason", "No reason provided.")
        lines.append(f"🚫 {name} — **{reason}**")

    chunks = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > 3800:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)

    await interaction.response.send_message(
        embed=discord.Embed(
            title="🚫 Giveaway Winner Blocks",
            description=chunks[0],
            color=discord.Color.red()
        ),
        ephemeral=True
    )

    for chunk in chunks[1:]:
        await interaction.followup.send(
            embed=discord.Embed(
                title="🚫 Giveaway Winner Blocks",
                description=chunk,
                color=discord.Color.red()
            ),
            ephemeral=True
        )


# ============================================================
# GIVEAWAY VIEW
# ============================================================

def save_giveaway_record(view, giveaway_id, channel_id, guild_id):

    giveaway_records[str(giveaway_id)] = {
        "guild_id": guild_id,
        "channel_id": channel_id,
        "message_id": giveaway_id,
        "prize": view.prize,
        "host_id": view.host.id,
        "photo": view.photo,
        "end_time": view.end_time.isoformat() if view.end_time else None,
        "entries": list(view.entries),
        "finished": view.finished,
        "winner_id": view.winner_id
    }
    save_json(GIVEAWAYS_FILE, giveaway_records)


def delete_giveaway_record(giveaway_id):
    giveaway_records.pop(str(giveaway_id), None)
    save_json(GIVEAWAYS_FILE, giveaway_records)


async def restore_saved_giveaways():

    for giveaway_id_text, record in list(giveaway_records.items()):
        try:
            giveaway_id = int(giveaway_id_text)
            guild = bot.get_guild(int(record["guild_id"]))
            if guild is None:
                continue

            channel = guild.get_channel(int(record["channel_id"]))
            if channel is None:
                channel = await bot.fetch_channel(int(record["channel_id"]))

            message = await channel.fetch_message(giveaway_id)

            if record.get("finished"):
                delete_giveaway_record(giveaway_id)
                continue

            host = guild.get_member(int(record["host_id"]))
            if host is None:
                host = await guild.fetch_member(int(record["host_id"]))

            end_time = (
                datetime.fromisoformat(record["end_time"])
                if record.get("end_time")
                else discord.utils.utcnow()
            )

            view = GiveawayView(
                record.get("prize", "Unknown Prize"),
                host,
                record.get("photo"),
                end_time
            )
            view.entries = set(int(x) for x in record.get("entries", []))
            view.message = message
            view.finished = False
            view.winner_id = record.get("winner_id")

            active_giveaways[giveaway_id] = view
            bot.add_view(view, message_id=giveaway_id)

            print(f"✅ Restored giveaway {giveaway_id} with {len(view.entries)} entries.")

            if end_time <= discord.utils.utcnow():
                continue

            view.finish_task = asyncio.create_task(
                schedule_giveaway_finish(view, giveaway_id, guild)
            )

        except Exception as e:
            print(f"⚠️ Could not restore giveaway {giveaway_id_text}: {e}")


class GiveawayView(discord.ui.View):

    def __init__(
        self,
        prize,
        host,
        photo=None,
        end_time=None
    ):

        super().__init__(
            timeout=None
        )

        self.prize = prize
        self.host = host
        self.photo = photo
        self.end_time = end_time
        self.entries = set()
        self.message = None
        self.finished = False
        self.winner_id = None
        self.finish_task = None

    @discord.ui.button(
        label="🎉 Enter Giveaway",
        style=discord.ButtonStyle.green,
        custom_id="vkingvx_giveaway_enter"
    )
    async def enter(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if self.finished:

            await interaction.response.send_message(
                "❌ This giveaway has already ended.",
                ephemeral=True
            )

            return

        user_id = interaction.user.id

        giveaway_block = get_giveaway_block(user_id)
        if giveaway_block is not None:
            reason = giveaway_block.get("reason", "No reason was provided.")
            await interaction.response.send_message(
                "🚫 **You are blocked from winning giveaways.**\n\n"
                f"**Reason:** {reason}",
                ephemeral=True
            )
            return

        if user_id in self.entries:

            await interaction.response.send_message(
                "⚠️ You're already entered! You only get 1 entry.",
                ephemeral=True
            )

            return

        self.entries.add(
            user_id
        )

        if self.message:
            try:
                save_giveaway_record(
                    self,
                    self.message.id,
                    self.message.channel.id,
                    self.message.guild.id
                )
            except Exception as e:
                print(f"⚠️ Could not save giveaway entry: {e}")

        if self.message:

            try:

                embed = self.message.embeds[0]

                for index, field in enumerate(
                    embed.fields
                ):

                    if field.name == "🎟️ Entries":

                        embed.set_field_at(
                            index,
                            name="🎟️ Entries",
                            value=f"**{len(self.entries)}**",
                            inline=True
                        )

                        break

                await self.message.edit(
                    embed=embed,
                    view=self
                )

            except Exception:
                pass

        await interaction.response.send_message(
            f"🎉 You're entered!\n"
            f"🎟️ Your entries: **1**\n"
            f"👥 Total entries: **{len(self.entries)}**",
            ephemeral=True
        )



async def schedule_giveaway_finish(view, giveaway_id, guild):
    try:
        while not view.finished:
            delay = max(0, (view.end_time - discord.utils.utcnow()).total_seconds())
            if delay > 0:
                await asyncio.sleep(delay)

            if view.finished or giveaway_id not in active_giveaways:
                return

            view.finished = True

            for item in view.children:
                item.disabled = True

            winner_text = None

            eligible_entries = get_eligible_giveaway_entries(view)

            if eligible_entries:
                view.winner_id = random.choice(eligible_entries)
                winner = guild.get_member(view.winner_id)
                winner_text = winner.mention if winner else f"<@{view.winner_id}>"

            result_embed = discord.Embed(
                title="🎉 GIVEAWAY ENDED 🎉",
                description=(
                    f"## 🎁 {view.prize}\n\n"
                    + (
                        f"🏆 **Winner:** {winner_text}\n\n"
                        f"🎟️ **Total entries:** **{len(view.entries)}**"
                        if winner_text
                        else "😢 **Nobody entered this giveaway.**"
                    )
                ),
                color=discord.Color.green() if winner_text else discord.Color.red()
            )

            result_embed.add_field(
                name="👑 Host",
                value=view.host.mention,
                inline=True
            )
            result_embed.add_field(
                name="🎟️ Entries",
                value=f"**{len(view.entries)}**",
                inline=True
            )

            if view.photo:
                result_embed.set_image(url=view.photo)

            if view.message:
                try:
                    await view.message.edit(
                        embed=result_embed,
                        view=view
                    )
                except discord.HTTPException:
                    pass

            await mod_log(
                guild,
                "🏁 Giveaway Ended",
                f"**Prize:** {view.prize}\n"
                f"**Host:** {view.host.mention}\n"
                f"**Entries:** {len(view.entries)}\n"
                f"**Winner:** {winner_text or 'Nobody entered'}",
                discord.Color.green()
            )

            if winner_text and view.message:
                try:
                    await view.message.channel.send(
                        f"🎉 Congratulations {winner_text}!\n"
                        f"You won **{view.prize}**! 🏆",
                        allowed_mentions=discord.AllowedMentions(users=True)
                    )
                except discord.HTTPException:
                    pass

            active_giveaways.pop(giveaway_id, None)
            delete_giveaway_record(giveaway_id)
            return

    except asyncio.CancelledError:
        return
    except Exception as e:
        print(f"⚠️ Giveaway {giveaway_id} finish task failed: {e}")


# ============================================================
# ============================================================
# NEW COMMAND: /giveaway-info
# ============================================================

@bot.tree.command(
    name="giveaway-info",
    description="View information about an active or completed giveaway"
)
@app_commands.describe(
    message_id="The message ID of the giveaway"
)
@is_admin_role()
async def giveaway_info(
    interaction: discord.Interaction,
    message_id: str
):
    try:
        giveaway_id = int(message_id)
    except ValueError:
        await interaction.response.send_message(
            "❌ Invalid giveaway ID.",
            ephemeral=True
        )
        return

    view = active_giveaways.get(giveaway_id)

    if view is None or view.message is None:
        await interaction.response.send_message(
            "❌ I couldn't find that giveaway.",
            ephemeral=True
        )
        return

    status = "🔴 Ended" if view.finished else "🟢 Active"

    if view.finished:
        end_value = "Ended"
    elif view.end_time:
        end_value = discord.utils.format_dt(
            view.end_time,
            style="R"
        )
    else:
        end_value = "Unknown"

    winner_value = "None yet"

    if view.winner_id:
        winner = interaction.guild.get_member(view.winner_id)
        winner_value = (
            winner.mention
            if winner
            else f"<@{view.winner_id}>"
        )

    embed = discord.Embed(
        title="🎉 Giveaway Information",
        description=(
            f"🎁 **Prize:** {view.prize}\n"
            f"🆔 **Giveaway ID:** `{giveaway_id}`"
        ),
        color=(
            discord.Color.red()
            if view.finished
            else discord.Color.green()
        )
    )

    embed.add_field(
        name="📊 Status",
        value=status,
        inline=True
    )

    embed.add_field(
        name="🎟️ Entries",
        value=f"**{len(view.entries)}**",
        inline=True
    )

    embed.add_field(
        name="⏰ Time",
        value=end_value,
        inline=True
    )

    embed.add_field(
        name="👑 Host",
        value=view.host.mention,
        inline=True
    )

    embed.add_field(
        name="🏆 Winner",
        value=winner_value,
        inline=True
    )

    embed.add_field(
        name="🔗 Giveaway Message",
        value=f"[Jump to Giveaway]({view.message.jump_url})",
        inline=True
    )

    embed.set_footer(
        text="Vkingvx Bot • Giveaway Info"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# /giveaway-entries
# ============================================================

@bot.tree.command(
    name="giveaway-entries",
    description="View everyone entered in a giveaway"
)
@app_commands.describe(
    message_id="The message ID of the giveaway"
)
@is_admin_role()
async def giveaway_entries(
    interaction: discord.Interaction,
    message_id: str
):
    try:
        giveaway_id = int(message_id)
    except ValueError:
        await interaction.response.send_message(
            "❌ Invalid giveaway ID.",
            ephemeral=True
        )
        return

    view = active_giveaways.get(giveaway_id)

    # If the giveaway was restored after a restart, it should already be
    # in active_giveaways with its saved entries.
    if view is None or view.message is None:
        await interaction.response.send_message(
            "❌ I couldn't find that giveaway. Make sure you're using the giveaway message ID.",
            ephemeral=True
        )
        return

    if not view.entries:
        await interaction.response.send_message(
            f"🎟️ **Giveaway `{giveaway_id}` has no entries yet.**",
            ephemeral=True
        )
        return

    entry_ids = sorted(view.entries)
    lines = []

    for number, user_id in enumerate(entry_ids, start=1):
        member = interaction.guild.get_member(user_id)
        if member:
            lines.append(f"**{number}.** {member.mention} — `{member}`")
        else:
            lines.append(f"**{number}.** <@{user_id}> — `{user_id}`")

    # Discord embed descriptions are limited to 4096 characters, so split
    # large entry lists across multiple embeds/messages.
    chunks = []
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > 3800:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line

    if current:
        chunks.append(current)

    await interaction.response.send_message(
        embed=discord.Embed(
            title="🎟️ Giveaway Entries",
            description=(
                f"🎁 **Prize:** {view.prize}\n"
                f"🆔 **Giveaway ID:** `{giveaway_id}`\n"
                f"📊 **Total entries:** **{len(view.entries)}**\n\n"
                + chunks[0]
            ),
            color=discord.Color.green() if not view.finished else discord.Color.red()
        ),
        ephemeral=True
    )

    for chunk in chunks[1:]:
        await interaction.followup.send(
            embed=discord.Embed(
                title=f"🎟️ Giveaway Entries — `{giveaway_id}`",
                description=chunk,
                color=discord.Color.green() if not view.finished else discord.Color.red()
            ),
            ephemeral=True
        )


# ============================================================
# /edit-giveaway
# ============================================================

@bot.tree.command(
    name="edit-giveaway",
    description="Edit an active giveaway"
)
@app_commands.describe(
    message_id="The message ID of the giveaway",
    minutes="New time from now in minutes",
    prize="New giveaway prize",
    host="New giveaway host",
    photo="New image URL, or type none to remove the image"
)
@is_admin_role()
async def edit_giveaway(
    interaction: discord.Interaction,
    message_id: str,
    minutes: int | None = None,
    prize: str | None = None,
    host: discord.Member | None = None,
    photo: str | None = None
):
    try:
        giveaway_id = int(message_id)
    except ValueError:
        await interaction.response.send_message(
            "❌ Invalid giveaway ID.",
            ephemeral=True
        )
        return

    view = active_giveaways.get(giveaway_id)

    if view is None or view.message is None:
        await interaction.response.send_message(
            "❌ I couldn't find that active giveaway.",
            ephemeral=True
        )
        return

    if view.finished:
        await interaction.response.send_message(
            "❌ That giveaway has already ended.",
            ephemeral=True
        )
        return

    if minutes is None and prize is None and host is None and photo is None:
        await interaction.response.send_message(
            "❌ Give me at least one thing to edit: `minutes`, `prize`, `host`, or `photo`.",
            ephemeral=True
        )
        return

    if minutes is not None:
        if minutes < 1:
            await interaction.response.send_message(
                "❌ Giveaway time must be at least 1 minute.",
                ephemeral=True
            )
            return
        if minutes > 10080:
            await interaction.response.send_message(
                "❌ Giveaway cannot be longer than 7 days.",
                ephemeral=True
            )
            return

    if prize is not None:
        if not prize.strip():
            await interaction.response.send_message(
                "❌ The prize cannot be empty.",
                ephemeral=True
            )
            return
        view.prize = prize

    if host is not None:
        view.host = host

    if photo is not None:
        if photo.lower().strip() in {"none", "remove", "no"}:
            view.photo = None
        else:
            view.photo = photo

    if minutes is not None:
        view.end_time = discord.utils.utcnow() + timedelta(minutes=minutes)

        if view.finish_task and not view.finish_task.done():
            view.finish_task.cancel()

        view.finish_task = asyncio.create_task(
            schedule_giveaway_finish(
                view,
                giveaway_id,
                interaction.guild
            )
        )

    embed = view.message.embeds[0] if view.message.embeds else discord.Embed(
        title="🎉  GIVEAWAY  🎉"
    )

    embed.description = (
        f"## 🎁 {view.prize}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✨ **How to enter**\n"
        "Click the **🎉 Enter Giveaway** button below to join!\n\n"
        "🎟️ **1 entry per person**\n"
        "🏆 **One lucky winner will be selected!**\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    found_host = False
    found_time = False
    found_entries = False

    for index, field in enumerate(embed.fields):
        if field.name == "👑 Host":
            embed.set_field_at(
                index,
                name="👑 Host",
                value=view.host.mention,
                inline=True
            )
            found_host = True
        elif field.name == "⏰ Ends":
            embed.set_field_at(
                index,
                name="⏰ Ends",
                value=discord.utils.format_dt(view.end_time, style="R"),
                inline=True
            )
            found_time = True
        elif field.name == "🎟️ Entries":
            embed.set_field_at(
                index,
                name="🎟️ Entries",
                value=f"**{len(view.entries)}**",
                inline=True
            )
            found_entries = True

    if not found_host:
        embed.add_field(name="👑 Host", value=view.host.mention, inline=True)
    if not found_time:
        embed.add_field(
            name="⏰ Ends",
            value=discord.utils.format_dt(view.end_time, style="R"),
            inline=True
        )
    if not found_entries:
        embed.add_field(
            name="🎟️ Entries",
            value=f"**{len(view.entries)}**",
            inline=True
        )

    embed.set_image(url=view.photo) if view.photo else embed.clear_fields() if False else None

    if view.photo:
        embed.set_image(url=view.photo)
    else:
        embed._image = None

    try:
        await view.message.edit(
            embed=embed,
            view=view
        )
    except discord.HTTPException as e:
        await interaction.response.send_message(
            f"❌ I couldn't update the giveaway message: {e}",
            ephemeral=True
        )
        return

    save_giveaway_record(
        view,
        giveaway_id,
        view.message.channel.id,
        interaction.guild.id
    )

    changes = []
    if minutes is not None:
        changes.append(f"⏰ **Time:** {minutes} minutes from now")
    if prize is not None:
        changes.append(f"🎁 **Prize:** {view.prize}")
    if host is not None:
        changes.append(f"👑 **Host:** {view.host.mention}")
    if photo is not None:
        changes.append("🖼️ **Image:** " + ("Removed" if view.photo is None else "Updated"))

    await interaction.response.send_message(
        "✅ **Giveaway updated!**\n\n" + "\n".join(changes),
        ephemeral=True
    )

    await mod_log(
        interaction.guild,
        "✏️ Giveaway Edited",
        f"**Giveaway:** `{giveaway_id}`\n"
        f"**Edited by:** {interaction.user.mention}\n"
        + "\n".join(changes),
        discord.Color.blurple()
    )


# ============================================================
# /giveaway
# ============================================================

@bot.tree.command(
    name="giveaway",
    description="Create a giveaway"
)
@app_commands.describe(
    minutes="How long the giveaway lasts",
    prize="Giveaway prize",
    host="Giveaway host",
    photo="Optional image URL"
)
@is_admin_role()
async def giveaway(
    interaction: discord.Interaction,
    minutes: int,
    prize: str,
    host: discord.Member,
    photo: str | None = None
):

    if minutes < 1:

        await interaction.response.send_message(
            "❌ Giveaway time must be at least 1 minute.",
            ephemeral=True
        )

        return

    if minutes > 10080:

        await interaction.response.send_message(
            "❌ Giveaway cannot be longer than 7 days.",
            ephemeral=True
        )

        return

    end_time = (
        discord.utils.utcnow()
        + timedelta(minutes=minutes)
    )

    view = GiveawayView(
        prize,
        host,
        photo,
        end_time
    )

    embed = discord.Embed(
        title="🎉  GIVEAWAY  🎉",
        description=(
            f"## 🎁 {prize}\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✨ **How to enter**\n"
            "Click the **🎉 Enter Giveaway** button below to join!\n\n"
            "🎟️ **1 entry per person**\n"
            "🏆 **One lucky winner will be selected!**\n"
            "━━━━━━━━━━━━━━━━━━━━"
        ),
        color=discord.Color.from_rgb(88, 101, 242)
    )

    embed.add_field(
        name="👑 Host",
        value=host.mention,
        inline=True
    )

    embed.add_field(
        name="⏰ Ends",
        value=discord.utils.format_dt(
            end_time,
            style="R"
        ),
        inline=True
    )

    embed.add_field(
        name="🎟️ Entries",
        value="**0**",
        inline=True
    )

    embed.set_footer(
        text="🍀 Good luck to everyone! • Vkingvx Giveaways"
    )
    embed.timestamp = discord.utils.utcnow()

    if photo:
        embed.set_image(
            url=photo
        )

    await interaction.response.send_message(
        "✅ Giveaway sent!",
        ephemeral=True
    )

    giveaway_message = await interaction.channel.send(
        embed=embed,
        view=view
    )

    view.message = giveaway_message

    active_giveaways[
        giveaway_message.id
    ] = view

    save_giveaway_record(
        view,
        giveaway_message.id,
        giveaway_message.channel.id,
        interaction.guild.id
    )

    await mod_log(
        interaction.guild,
        "🎉 Giveaway Created",
        f"**Prize:** {prize}\n"
        f"**Host:** {host.mention}\n"
        f"**Created by:** {interaction.user.mention}\n"
        f"**Duration:** {minutes} minutes\n"
        f"**Channel:** {interaction.channel.mention}",
        discord.Color.blurple()
    )

    view.finish_task = asyncio.create_task(
        schedule_giveaway_finish(
            view,
            giveaway_message.id,
            interaction.guild
        )
    )


# ============================================================
# /reroll
# ============================================================

@bot.tree.command(
    name="reroll",
    description="Reroll a completed giveaway"
)
@app_commands.describe(
    message_id="Optional giveaway message ID"
)
@is_admin_role()
async def reroll(
    interaction: discord.Interaction,
    message_id: str | None = None
):

    view = None

    if message_id:

        try:

            giveaway_id = int(
                message_id
            )

        except ValueError:

            await interaction.response.send_message(
                "❌ Invalid message ID.",
                ephemeral=True
            )

            return

        view = active_giveaways.get(
            giveaway_id
        )

    else:

        channel_giveaways = []

        for giveaway_id, giveaway_view in active_giveaways.items():

            if giveaway_view.message is None:
                continue

            if giveaway_view.message.channel.id != interaction.channel.id:
                continue

            if not giveaway_view.finished:
                continue

            channel_giveaways.append(
                giveaway_view
            )

        if channel_giveaways:

            channel_giveaways.sort(
                key=lambda x: x.message.id,
                reverse=True
            )

            view = channel_giveaways[0]

    if view is None:

        await interaction.response.send_message(
            "❌ I couldn't find that giveaway.",
            ephemeral=True
        )

        return

    if not view.finished:

        await interaction.response.send_message(
            "❌ That giveaway hasn't ended yet.",
            ephemeral=True
        )

        return

    if not view.entries:

        await interaction.response.send_message(
            "❌ Nobody entered that giveaway.",
            ephemeral=True
        )

        return

    eligible_users = set(
        get_eligible_giveaway_entries(
            view,
            exclude_ids={view.winner_id} if view.winner_id else set()
        )
    )

    if not eligible_users:

        await interaction.response.send_message(
            "❌ There are no other eligible entrants.",
            ephemeral=True
        )

        return

    old_winner_id = view.winner_id

    new_winner_id = random.choice(
        list(eligible_users)
    )

    view.winner_id = new_winner_id

    winner_text = f"<@{new_winner_id}>"

    embed = discord.Embed(
        title="🎉 GIVEAWAY REROLLED 🎉",
        description=(
            f"## 🎁 {view.prize}\n\n"
            f"🏆 **New Winner:** {winner_text}\n\n"
            f"🎟️ **Total entries:** {len(view.entries)}"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="👑 Host",
        value=view.host.mention,
        inline=True
    )

    embed.add_field(
        name="🎟️ Entries",
        value=f"**{len(view.entries)}**",
        inline=True
    )

    if view.photo:
        embed.set_image(
            url=view.photo
        )

    try:

        await view.message.edit(
            embed=embed,
            view=view
        )

    except discord.HTTPException:
        pass

    await interaction.response.send_message(
        "✅ Giveaway rerolled!",
        ephemeral=True
    )

    await mod_log(
        interaction.guild,
        "🔄 Giveaway Rerolled",
        f"**Prize:** {view.prize}\n"
        f"**Moderator:** {interaction.user.mention}\n"
        f"**Previous winner:** "
        f"<@{old_winner_id}>\n"
        f"**New winner:** {winner_text}\n"
        f"**Entries:** {len(view.entries)}",
        discord.Color.gold()
    )

    try:

        await interaction.channel.send(
            f"🎉 Congratulations {winner_text}!\n"
            f"You won the rerolled giveaway for "
            f"**{view.prize}**! 🏆",
            allowed_mentions=discord.AllowedMentions(
                users=True
            )
        )

    except discord.HTTPException:
        pass


# ============================================================
# /schedule_say
# ============================================================

@bot.tree.command(
    name="schedule_say",
    description="Schedule a message for a UTC time"
)
@app_commands.describe(
    channel="Channel where the message will be sent",
    time="UTC time: YYYY-MM-DD HH:MM",
    message="Message to send"
)
@is_admin_role()
async def schedule_say(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    time: str,
    message: str
):

    try:

        scheduled_time = datetime.strptime(
            time,
            "%Y-%m-%d %H:%M"
        ).replace(
            tzinfo=timezone.utc
        )

    except ValueError:

        await interaction.response.send_message(
            "❌ Invalid time. Use `YYYY-MM-DD HH:MM` in UTC.",
            ephemeral=True
        )

        return

    now = datetime.now(
        timezone.utc
    )

    if scheduled_time <= now:

        await interaction.response.send_message(
            "❌ That time has already passed.",
            ephemeral=True
        )

        return

    # Convert typed \n into real Discord line breaks.
    message = message.replace("\\n", "\n")

    schedule_id = str(
        random.randint(
            100000,
            999999
        )
    )

    while schedule_id in scheduled_messages:

        schedule_id = str(
            random.randint(
                100000,
                999999
            )
        )

    scheduled_messages[schedule_id] = {
        "guild_id": interaction.guild.id,
        "channel_id": channel.id,
        "message": message,
        "time": scheduled_time.isoformat()
    }

    save_json(
        SCHEDULE_FILE,
        scheduled_messages
    )

    await interaction.response.send_message(
        f"✅ Scheduled!\n\n"
        f"**ID:** `{schedule_id}`\n"
        f"**Channel:** {channel.mention}\n"
        f"**UTC:** `{time}`\n"
        f"**Message:** {message}",
        ephemeral=True
    )

    await mod_log(
        interaction.guild,
        "⏰ Scheduled Message Created",
        f"**ID:** `{schedule_id}`\n"
        f"**Moderator:** {interaction.user.mention}\n"
        f"**Channel:** {channel.mention}\n"
        f"**Time UTC:** `{time}`\n"
        f"**Message:** {message}",
        discord.Color.blurple()
    )


# ============================================================
# /scheduled
# ============================================================

@bot.tree.command(
    name="scheduled",
    description="View scheduled messages"
)
@is_admin_role()
async def scheduled(
    interaction: discord.Interaction
):

    guild_id = interaction.guild.id

    guild_schedules = {
        schedule_id: data
        for schedule_id, data
        in scheduled_messages.items()
        if data.get("guild_id") == guild_id
    }

    if not guild_schedules:

        await interaction.response.send_message(
            "📭 There are no scheduled messages.",
            ephemeral=True
        )

        return

    embed = discord.Embed(
        title="⏰ Scheduled Messages",
        color=discord.Color.blurple()
    )

    for schedule_id, data in guild_schedules.items():

        channel = interaction.guild.get_channel(
            data["channel_id"]
        )

        channel_text = (
            channel.mention
            if channel
            else "Unknown channel"
        )

        try:

            dt = datetime.fromisoformat(
                data["time"]
            )

            time_text = discord.utils.format_dt(
                dt,
                style="F"
            )

        except Exception:

            time_text = data["time"]

        embed.add_field(
            name=f"ID: {schedule_id}",
            value=(
                f"**Channel:** {channel_text}\n"
                f"**Time:** {time_text}\n"
                f"**Message:** {data['message']}"
            ),
            inline=False
        )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# /cancel_scheduled
# ============================================================

@bot.tree.command(
    name="cancel_scheduled",
    description="Cancel a scheduled message"
)
@app_commands.describe(
    schedule_id="Scheduled message ID"
)
@is_admin_role()
async def cancel_scheduled(
    interaction: discord.Interaction,
    schedule_id: str
):

    data = scheduled_messages.get(
        schedule_id
    )

    if data is None:

        await interaction.response.send_message(
            "❌ I couldn't find that scheduled message.",
            ephemeral=True
        )

        return

    if data.get("guild_id") != interaction.guild.id:

        await interaction.response.send_message(
            "❌ That scheduled message belongs to another server.",
            ephemeral=True
        )

        return

    scheduled_messages.pop(
        schedule_id
    )

    save_json(
        SCHEDULE_FILE,
        scheduled_messages
    )

    await interaction.response.send_message(
        f"✅ Scheduled message `{schedule_id}` was cancelled.",
        ephemeral=True
    )

    await mod_log(
        interaction.guild,
        "❌ Scheduled Message Cancelled",
        f"**ID:** `{schedule_id}`\n"
        f"**Moderator:** {interaction.user.mention}\n"
        f"**Message:** {data.get('message', 'Unknown')}",
        discord.Color.red()
    )


# ============================================================
# SCHEDULE CHECKER
# ============================================================

async def scheduled_message_checker():

    await bot.wait_until_ready()

    while not bot.is_closed():

        now = datetime.now(
            timezone.utc
        )

        changed = False

        for schedule_id, data in list(
            scheduled_messages.items()
        ):

            try:

                scheduled_time = datetime.fromisoformat(
                    data["time"]
                )

            except Exception:

                scheduled_messages.pop(
                    schedule_id,
                    None
                )

                changed = True

                continue

            if scheduled_time > now:
                continue

            channel = bot.get_channel(
                data["channel_id"]
            )

            if channel:

                try:

                    await channel.send(
                        data["message"],
                        allowed_mentions=discord.AllowedMentions(
                            everyone=True,
                            users=True,
                            roles=True,
                            replied_user=False
                        )
                    )

                    print(
                        f"⏰ Sent scheduled message {schedule_id}"
                    )

                    guild = bot.get_guild(
                        data.get("guild_id")
                    )

                    if guild:

                        await mod_log(
                            guild,
                            "⏰ Scheduled Message Sent",
                            f"**ID:** `{schedule_id}`\n"
                            f"**Channel:** {channel.mention}\n"
                            f"**Message:** {data['message']}",
                            discord.Color.green()
                        )

                except discord.HTTPException as e:

                    print(
                        f"❌ Scheduled message failed: {e}"
                    )

            else:

                print(
                    f"❌ Channel {data['channel_id']} not found."
                )

            scheduled_messages.pop(
                schedule_id,
                None
            )

            changed = True

        if changed:

            save_json(
                SCHEDULE_FILE,
                scheduled_messages
            )

        await asyncio.sleep(
            5
        )


# ============================================================
# TICKET MESSAGE
# ============================================================

TICKET_MESSAGE = (
    "👋 **Thank you for contacting support!**\n\n"
    "Please pick an option below:\n\n"
    "🎉 **Giveaway Winner** — You won a giveaway and need to claim your prize.\n\n"
    "🛠️ **General Support** — You need help with an issue or have a question.\n\n"
    "🎁 **Host a Giveaway** — You want permission to host a giveaway in the server.\n\n"
    "🎥 **Twitch Moderator** — You are a Twitch moderator and need the Discord Moderator role.\n\n"
    "📋 **Staff Application** — You want to apply for a staff position.\n\n"
    "🚨 **Report a Member** — You need to report a member for breaking the rules.\n\n"
    "🐛 **Bug Report** — You found a bug or something isn't working correctly.\n\n"
    "💰 **Prize / Payment Issue** — You have an issue with a giveaway prize, payment, or reward.\n\n"
    "👤 **Account / Role Issue** — You have an issue with your roles or Discord permissions.\n\n"
    "⚖️ **Appeal** — You believe you were wrongly warned, muted, kicked, or banned.\n\n"
    "💡 **Suggestion** — You have an idea or suggestion for improving the server.\n\n"
    "❓ **Other** — Your issue doesn't fit any of the options above.\n\n"
    "📩 **Please explain your issue and a staff member will assist you shortly.**"
)


# ============================================================
# CLOSED TICKET MESSAGE
# ============================================================

CLOSED_TICKET_MESSAGE = (
    "🔒 **Ticket Closed**\n\n"
    "Thank you for contacting support!\n\n"
    "This ticket has been closed.\n\n"
    "If you still need help, please open a new ticket "
    "and our staff team will be happy to assist you.\n\n"
    "💙 **Thank you for being part of our community!**"
)


# ============================================================
# NEW TICKET DETECTION
# ============================================================

@bot.event
async def on_guild_channel_create(
    channel
):

    if not isinstance(
        channel,
        discord.TextChannel
    ):
        return

    if not channel.name.startswith(
        "ticket-"
    ):
        return

    await asyncio.sleep(
        3
    )

    try:

        await channel.send(
            TICKET_MESSAGE
        )

        print(
            f"✅ Sent ticket message in #{channel.name}"
        )

    except discord.Forbidden:

        print(
            f"❌ No permission in #{channel.name}"
        )

    except discord.HTTPException as e:

        print(
            f"❌ Ticket message error: {e}"
        )


# ============================================================
# CLOSED TICKET DETECTION
# ============================================================

@bot.event
async def on_guild_channel_update(
    before,
    after
):

    if not isinstance(
        after,
        discord.TextChannel
    ):
        return

    if before.name == after.name:
        return

    if not after.name.startswith(
        "closed-"
    ):
        return

    await asyncio.sleep(
        3
    )

    try:

        await after.send(
            CLOSED_TICKET_MESSAGE
        )

        print(
            f"🔒 Sent closed ticket message in #{after.name}"
        )

    except discord.Forbidden:

        print(
            f"❌ No permission in #{after.name}"
        )

    except discord.HTTPException as e:

        print(
            f"❌ Closed ticket message error: {e}"
        )


# ============================================================
# /delete_threads
# ============================================================

@bot.tree.command(
    name="delete_threads",
    description="Delete all threads in the server"
)
@is_admin_role()
async def delete_threads(
    interaction: discord.Interaction
):

    await interaction.response.defer(ephemeral=True)

    deleted = 0
    failed = 0

    for channel in interaction.guild.channels:

        try:
            if isinstance(channel, discord.TextChannel):
                active_threads = list(channel.threads)
                for thread in active_threads:
                    try:
                        await thread.delete(reason=f"All threads deleted by {interaction.user}")
                        deleted += 1
                    except (discord.Forbidden, discord.HTTPException):
                        failed += 1

                archived = []
                try:
                    async for thread in channel.archived_threads(limit=None):
                        archived.append(thread)
                except (discord.Forbidden, discord.HTTPException):
                    pass

                for thread in archived:
                    if thread.id in {t.id for t in active_threads}:
                        continue
                    try:
                        await thread.delete(reason=f"All threads deleted by {interaction.user}")
                        deleted += 1
                    except (discord.Forbidden, discord.HTTPException):
                        failed += 1

        except Exception as e:
            print(f"Thread cleanup error in #{getattr(channel, 'name', 'unknown')}: {e}")

    result = f"🗑️ Deleted **{deleted}** thread(s)."

    if failed:
        result += f"\n⚠️ Failed to delete **{failed}** thread(s)."

    await interaction.followup.send(
        result,
        ephemeral=True
    )


# ============================================================
# /robloxavatar
# ============================================================

@bot.tree.command(
    name="robloxavatar",
    description="Show a Roblox user's avatar"
)
@app_commands.describe(
    username="Roblox username"
)
async def robloxavatar(
    interaction: discord.Interaction,
    username: str
):

    await interaction.response.defer()

    import urllib.request
    import urllib.error

    try:

        payload = json.dumps({
            "usernames": [username],
            "excludeBannedUsers": False
        }).encode("utf-8")

        request = urllib.request.Request(
            "https://users.roblox.com/v1/usernames/users",
            data=payload,
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:
            user_result = json.loads(
                response.read().decode("utf-8")
            )

        if not user_result.get("data"):
            await interaction.followup.send(
                f"❌ I couldn't find the Roblox user **{username}**."
            )
            return

        user_data = user_result["data"][0]
        user_id = user_data["id"]
        roblox_username = user_data["name"]
        display_name = user_data["displayName"]

        avatar_url = (
            "https://thumbnails.roblox.com/v1/users/avatar"
            f"?userIds={user_id}"
            "&size=420x420"
            "&format=Png"
            "&isCircular=false"
        )

        with urllib.request.urlopen(
            avatar_url,
            timeout=10
        ) as response:
            avatar_result = json.loads(
                response.read().decode("utf-8")
            )

        avatar_image = None

        if avatar_result.get("data"):
            avatar_image = avatar_result["data"][0].get("imageUrl")

        embed = discord.Embed(
            title="🧑 Roblox Avatar",
            description=(
                f"**Username:** `{roblox_username}`\n"
                f"**Display Name:** {display_name}\n"
                f"**User ID:** `{user_id}`"
            ),
            color=discord.Color.blurple()
        )

        if avatar_image:
            embed.set_image(url=avatar_image)

        embed.add_field(
            name="🔗 Profile",
            value=(
                f"[View Roblox Profile]("
                f"https://www.roblox.com/users/{user_id}/profile"
                f")"
            ),
            inline=False
        )

        await interaction.followup.send(embed=embed)

    except urllib.error.HTTPError as e:

        print(f"Roblox API HTTP error: {e}")

        await interaction.followup.send(
            "❌ Roblox's API rejected the request. Try again in a moment."
        )

    except urllib.error.URLError as e:

        print(f"Roblox API connection error: {e}")

        await interaction.followup.send(
            "❌ I couldn't connect to Roblox right now."
        )

    except Exception as e:

        print(f"Roblox avatar error: {e}")

        await interaction.followup.send(
            "❌ Something went wrong while getting that Roblox avatar."
        )


# ============================================================
# XP / LEVEL SYSTEM
# ============================================================

def xp_for_level(level: int):

    if level <= 1:
        return 0

    return 100 * (level - 1) ** 2 + 100 * (level - 1)


def level_from_xp(xp: int):

    level = 1

    while xp >= xp_for_level(level + 1):
        level += 1

    return level


def get_xp_data(guild_id: int, user_id: int):

    guild_key = str(guild_id)
    user_key = str(user_id)

    if guild_key not in user_xp:
        user_xp[guild_key] = {}

    if user_key not in user_xp[guild_key]:
        user_xp[guild_key][user_key] = {
            "xp": 0,
            "level": 1
        }

    return user_xp[guild_key][user_key]


@bot.event
async def on_message(message: discord.Message):

    if message.author.bot:
        return

    if message.guild is None:
        return

    guild_id = message.guild.id
    user_id = message.author.id
    cooldown_key = (guild_id, user_id)
    now = asyncio.get_running_loop().time()

    last_xp = xp_cooldowns.get(cooldown_key, 0)

    if now - last_xp < XP_COOLDOWN_SECONDS:
        return

    xp_cooldowns[cooldown_key] = now

    data = get_xp_data(
        guild_id,
        user_id
    )

    old_level = data.get("level", 1)
    gained = random.randint(
        XP_MIN,
        XP_MAX
    )

    data["xp"] = data.get("xp", 0) + gained

    new_level = level_from_xp(
        data["xp"]
    )

    data["level"] = new_level

    save_json(
        XP_FILE,
        user_xp
    )

    if new_level > old_level:

        try:

            await message.channel.send(
                f"🎉 {message.author.mention} leveled up to **Level {new_level}!**"
            )

        except discord.HTTPException:
            pass



# ============================================================
# XP / LEVEL ADMIN COMMANDS
# ============================================================

@bot.tree.command(
    name="addxp",
    description="Give XP to a member"
)
@app_commands.describe(
    member="Member to give XP to",
    amount="Amount of XP to give"
)
@is_admin_role()
async def addxp(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 1, 1000000]
):
    data = get_xp_data(interaction.guild.id, member.id)
    old_level = level_from_xp(data.get("xp", 0))

    data["xp"] = data.get("xp", 0) + amount
    data["level"] = level_from_xp(data["xp"])
    save_json(XP_FILE, user_xp)

    new_level = data["level"]

    await interaction.response.send_message(
        f"✅ Gave {member.mention} **{amount:,} XP**.\n"
        f"⭐ Level: **{old_level} → {new_level}**\n"
        f"✨ Total XP: **{data['xp']:,}**"
    )


@bot.tree.command(
    name="removexp",
    description="Remove XP from a member"
)
@app_commands.describe(
    member="Member to remove XP from",
    amount="Amount of XP to remove"
)
@is_admin_role()
async def removexp(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 1, 1000000]
):
    data = get_xp_data(interaction.guild.id, member.id)
    old_level = level_from_xp(data.get("xp", 0))

    data["xp"] = max(0, data.get("xp", 0) - amount)
    data["level"] = level_from_xp(data["xp"])
    save_json(XP_FILE, user_xp)

    new_level = data["level"]

    await interaction.response.send_message(
        f"✅ Removed **{amount:,} XP** from {member.mention}.\n"
        f"⭐ Level: **{old_level} → {new_level}**\n"
        f"✨ Total XP: **{data['xp']:,}**"
    )


@bot.tree.command(
    name="setxp",
    description="Set a member's exact XP"
)
@app_commands.describe(
    member="Member whose XP to set",
    amount="Exact XP amount"
)
@is_admin_role()
async def setxp(
    interaction: discord.Interaction,
    member: discord.Member,
    amount: app_commands.Range[int, 0, 10000000]
):
    data = get_xp_data(interaction.guild.id, member.id)

    old_xp = data.get("xp", 0)
    old_level = level_from_xp(old_xp)

    data["xp"] = amount
    data["level"] = level_from_xp(amount)
    save_json(XP_FILE, user_xp)

    await interaction.response.send_message(
        f"✅ Set {member.mention}'s XP to **{amount:,}**.\n"
        f"⭐ Level: **{old_level} → {data['level']}**"
    )


@bot.tree.command(
    name="setlevel",
    description="Set a member's exact level"
)
@app_commands.describe(
    member="Member whose level to set",
    level="Exact level to set"
)
@is_admin_role()
async def setlevel(
    interaction: discord.Interaction,
    member: discord.Member,
    level: app_commands.Range[int, 1, 100]
):
    data = get_xp_data(interaction.guild.id, member.id)

    old_level = level_from_xp(data.get("xp", 0))
    new_xp = xp_for_level(level)

    data["xp"] = new_xp
    data["level"] = level
    save_json(XP_FILE, user_xp)

    await interaction.response.send_message(
        f"✅ Set {member.mention}'s level to **Level {level}**.\n"
        f"⭐ Level: **{old_level} → {level}**\n"
        f"✨ XP: **{new_xp:,}**"
    )


# ============================================================
# /rank
# ============================================================

@bot.tree.command(
    name="rank",
    description="View your XP and level"
)
@app_commands.describe(
    member="Optional member to check"
)
async def rank(
    interaction: discord.Interaction,
    member: discord.Member | None = None
):

    target = member or interaction.user

    data = get_xp_data(
        interaction.guild.id,
        target.id
    )

    xp = data.get("xp", 0)
    level = level_from_xp(xp)
    current_level_xp = xp_for_level(level)
    next_level_xp = xp_for_level(level + 1)
    progress = xp - current_level_xp
    needed = next_level_xp - current_level_xp

    embed = discord.Embed(
        title="🏆 XP Rank",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(
        url=target.display_avatar.url
    )

    embed.add_field(
        name="👤 Member",
        value=target.mention,
        inline=True
    )

    embed.add_field(
        name="⭐ Level",
        value=f"**{level}**",
        inline=True
    )

    embed.add_field(
        name="✨ XP",
        value=f"**{xp:,}**",
        inline=True
    )

    if level >= 100:
        progress_text = "MAX LEVEL"
    else:
        progress_text = f"{progress:,} / {needed:,} XP"

    embed.add_field(
        name="📈 Progress",
        value=progress_text,
        inline=False
    )

    embed.set_footer(
        text="Earn XP by chatting"
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# /level
# ============================================================

@bot.tree.command(
    name="level",
    description="Check a member's level"
)
@app_commands.describe(
    member="Member whose level you want to check"
)
async def level(
    interaction: discord.Interaction,
    member: discord.Member
):

    data = get_xp_data(
        interaction.guild.id,
        member.id
    )

    xp = data.get("xp", 0)
    current_level = level_from_xp(xp)

    await interaction.response.send_message(
        f"⭐ **{member.display_name}** is **Level {current_level}** "
        f"with **{xp:,} XP**."
    )


# ============================================================
# /leaderboard
# ============================================================

@bot.tree.command(
    name="leaderboard",
    description="Show the server XP leaderboard"
)
async def leaderboard(
    interaction: discord.Interaction
):

    guild_data = user_xp.get(
        str(interaction.guild.id),
        {}
    )

    if not guild_data:

        await interaction.response.send_message(
            "📊 Nobody has earned XP yet!"
        )

        return

    ranked = sorted(
        guild_data.items(),
        key=lambda item: item[1].get("xp", 0),
        reverse=True
    )

    lines = []

    for position, (user_id, data) in enumerate(
        ranked[:10],
        start=1
    ):

        member = interaction.guild.get_member(
            int(user_id)
        )

        if member is None:
            name = f"<@{user_id}>"
        else:
            name = member.display_name

        xp = data.get("xp", 0)
        level = level_from_xp(xp)

        medals = {
            1: "🥇",
            2: "🥈",
            3: "🥉"
        }

        prefix = medals.get(
            position,
            f"**{position}.**"
        )

        lines.append(
            f"{prefix} **{name}** — Level **{level}** · **{xp:,} XP**"
        )

    embed = discord.Embed(
        title="🏆 XP Leaderboard",
        description="\n".join(lines),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text="Top 10 XP earners"
    )

    await interaction.response.send_message(
        embed=embed
    )



# ============================================================
# /poll
# ============================================================

@bot.tree.command(
    name="poll",
    description="Create a poll"
)
@app_commands.describe(
    question="The poll question",
    option1="First option",
    option2="Second option",
    option3="Optional third option",
    option4="Optional fourth option"
)
@is_admin_role()
async def poll(
    interaction: discord.Interaction,
    question: str,
    option1: str,
    option2: str,
    option3: str | None = None,
    option4: str | None = None
):

    options = [option1, option2]

    if option3:
        options.append(option3)

    if option4:
        options.append(option4)

    letters = ["🇦", "🇧", "🇨", "🇩"]

    embed = discord.Embed(
        title="📊 Poll",
        description=f"**{question}**",
        color=discord.Color.blurple()
    )

    option_text = ""

    for index, option in enumerate(options):
        option_text += f"{letters[index]} **{option}**\n\n"

    embed.add_field(
        name="Choices",
        value=option_text,
        inline=False
    )

    embed.set_footer(
        text=f"Poll by {interaction.user}"
    )

    await interaction.response.send_message(
        embed=embed
    )

    message = await interaction.original_response()

    for index in range(len(options)):
        try:
            await message.add_reaction(letters[index])
        except discord.HTTPException:
            pass


# ============================================================
# /announce
# ============================================================

@bot.tree.command(
    name="announce",
    description="Send an announcement"
)
@app_commands.describe(
    channel="Channel to send the announcement in",
    title="Announcement title",
    message="Announcement message",
    everyone="Mention @everyone"
)
@is_admin_role()
async def announce(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    title: str,
    message: str,
    everyone: bool = False
):

    embed = discord.Embed(
        title=f"📢 {title}",
        description=message,
        color=discord.Color.blurple()
    )

    embed.set_footer(
        text=f"Announcement by {interaction.user}"
    )

    content = "@everyone" if everyone else None

    try:

        await channel.send(
            content=content,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(
                everyone=everyone
            )
        )

        await interaction.response.send_message(
            f"✅ Announcement sent to {channel.mention}.",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I don't have permission to send messages there.",
            ephemeral=True
        )

    except discord.HTTPException as e:

        await interaction.response.send_message(
            f"❌ Discord error: {e}",
            ephemeral=True
        )


# ============================================================
# COMMAND ERROR HANDLER
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error
):

    if isinstance(
        error,
        app_commands.errors.CheckFailure
    ):

        message = str(
            error
        )

        if not message:

            message = (
                "❌ You need the **Admin** role "
                "to use this command."
            )

    else:

        print(
            f"Command error: {error}"
        )

        message = (
            f"❌ Error: `{error}`"
        )

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                message,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    except discord.HTTPException:
        pass


# ============================================================
# BOT READY

# ============================================================

@bot.event
async def on_ready():

    print(
        f"✅ Logged in as {bot.user} ({bot.user.id})"
    )

    try:

        synced = await bot.tree.sync()

        print(
            f"✅ Synced {len(synced)} slash command(s)"
        )

    except Exception as e:

        print(
            f"❌ Slash command sync error: {e}"
        )

    if not hasattr(
        bot,
        "giveaways_restored"
    ):
        bot.giveaways_restored = True
        await restore_saved_giveaways()

    if not hasattr(
        bot,
        "scheduler_started"
    ):

        bot.scheduler_started = True

        asyncio.create_task(
            scheduled_message_checker()
        )

        print(
            "⏰ Scheduled message system started."
        )



    # ========================================================
    # SEND SERVER INVITE TO OWNER
    # ========================================================

    try:

        channel = bot.get_channel(
            INVITE_CHANNEL_ID
        )

        if channel is None:

            channel = await bot.fetch_channel(
                INVITE_CHANNEL_ID
            )

        invite = await channel.create_invite(
            max_age=0,
            max_uses=0,
            unique=True
        )

        owner = await bot.fetch_user(
            OWNER_ID
        )

        await owner.send(
            f"🔗 **Vkingvx Server Invite**\n\n"
            f"{invite.url}\n\n"
            f"📌 Copy this and send it to the streamer to pin."
        )

        print(
            "✅ Server invite sent to owner."
        )

    except Exception as e:

        print(
            f"❌ Invite DM error: {e}"
        )

# ============================================================
# START BOT
# ============================================================

if not TOKEN:

    print("")
    print("❌ DISCORD_TOKEN IS NOT SET.")
    print("")
    print("Set your token before starting the bot.")
    print("")

    raise RuntimeError(
        "DISCORD_TOKEN is not set."
    )


print(
    "🔌 Connecting to Discord..."
)

# /serverinfo
# ============================================================

@bot.tree.command(
    name="serverinfo",
    description="Show information about the server"
)
async def serverinfo(interaction: discord.Interaction):

    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    total_members = guild.member_count or 0

    humans = 0
    bots = 0

    for member in guild.members:
        if member.bot:
            bots += 1
        else:
            humans += 1

    embed = discord.Embed(
        title=f"📊 {guild.name}",
        description="Server information",
        color=discord.Color.blurple()
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(
        name="👥 Members",
        value=(
            f"**Total:** {total_members}\n"
            f"**Humans:** {humans}\n"
            f"**Bots:** {bots}"
        ),
        inline=True
    )

    embed.add_field(
        name="📁 Channels",
        value=(
            f"**Text:** {len(guild.text_channels)}\n"
            f"**Voice:** {len(guild.voice_channels)}\n"
            f"**Categories:** {len(guild.categories)}"
        ),
        inline=True
    )

    embed.add_field(
        name="🎭 Server",
        value=(
            f"**Roles:** {max(0, len(guild.roles) - 1)}\n"
            f"**Emojis:** {len(guild.emojis)}\n"
            f"**Stickers:** {len(guild.stickers)}"
        ),
        inline=True
    )

    embed.add_field(
        name="👑 Owner",
        value=guild.owner.mention if guild.owner else "Unknown",
        inline=True
    )

    embed.add_field(
        name="🆔 Server ID",
        value=f"`{guild.id}`",
        inline=True
    )

    embed.add_field(
        name="📅 Created",
        value=discord.utils.format_dt(
            guild.created_at,
            style="F"
        ),
        inline=True
    )

    embed.add_field(
        name="🚀 Boosts",
        value=(
            f"**Level:** {guild.premium_tier}\n"
            f"**Boosts:** {guild.premium_subscription_count or 0}"
        ),
        inline=True
    )

    embed.set_footer(
        text=f"Requested by {interaction.user}"
    )

    await interaction.response.send_message(
        embed=embed
    )

@bot.tree.command(name="clear-invites", description="Delete all active server invites")
@discord.app_commands.checks.has_permissions(manage_guild=True)
async def clear_invites(interaction: discord.Interaction):
    guild = interaction.guild

    if guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    invites = await guild.invites()

    deleted = 0
    failed = 0

    for invite in invites:
        try:
            await invite.delete(reason=f"Invites cleared by {interaction.user}")
            deleted += 1
        except discord.Forbidden:
            failed += 1
        except discord.HTTPException:
            failed += 1

    await interaction.response.send_message(
        f"🧹 **Invites cleared!**\n"
        f"Deleted: **{deleted}**\n"
        f"Failed: **{failed}**",
        ephemeral=True
    )

# ============================================================
# /fakeban-all
# ============================================================

@bot.tree.command(
    name="fakeban-all",
    description="Post a fake ban-all prank announcement"
)
@app_commands.describe(
    reason="Fake ban reason"
)
@is_admin_role()
async def fakeban_all(
    interaction: discord.Interaction,
    reason: str | None = None
):
    fake_reason = reason or "Breaking the server rules"

    embed = discord.Embed(
        title="🔨 SERVER BAN NOTICE",
        description=(
            "🚨 **EVERYONE HAS BEEN BANNED!** 🚨\n\n"
            f"**Reason:** {fake_reason}\n\n"
            "😭 **SIKE!**\n"
            "Nobody was actually banned. This was a fake ban prank! 💀😂"
        ),
        color=discord.Color.gold()
    )

    embed.set_footer(
        text=f"Fake ban prank by {interaction.user}"
    )

    await interaction.response.send_message(
        embed=embed
    )

    await mod_log(
        interaction.guild,
        "😂 Fake Ban All",
        f"**Moderator:** {interaction.user.mention}\n"
        f"**Fake Reason:** {fake_reason}\n"
        f"**Channel:** {interaction.channel.mention}",
        discord.Color.gold()
    )



# ============================================================
# /playvc
# ============================================================

VC_AUDIO_FILE = "Rick Astley - Never Gonna Give You Up (Official Video) (4K Remaster).mp3"


@bot.tree.command(
    name="playvc",
    description="Join your voice channel and play the bot audio file"
)
@is_admin_role()
async def playvc(interaction: discord.Interaction):

    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    member = interaction.user

    if not isinstance(member, discord.Member) or member.voice is None or member.voice.channel is None:
        await interaction.response.send_message(
            "❌ You need to be in a voice channel first.",
            ephemeral=True
        )
        return

    audio_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        VC_AUDIO_FILE
    )

    if not os.path.isfile(audio_path):
        await interaction.response.send_message(
            f"❌ Audio file not found:\n`{VC_AUDIO_FILE}`\n\n"
            "Put the MP3 in the same folder as the bot file.",
            ephemeral=True
        )
        return

    voice_channel = member.voice.channel
    voice_client = interaction.guild.voice_client

    try:
        await interaction.response.defer(ephemeral=True)

        if voice_client is None:
            voice_client = await voice_channel.connect()
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)

        if voice_client.is_playing():
            voice_client.stop()

        source = discord.FFmpegPCMAudio(audio_path)

        def after_playing(error):
            if error:
                print(f"❌ Voice playback error: {error}")
            else:
                print("✅ Voice audio finished playing.")

        voice_client.play(source, after=after_playing)

        await interaction.followup.send(
            f"🔊 Joined **{voice_channel.name}** and started playing the audio.",
            ephemeral=True
        )

    except discord.ClientException as e:
        await interaction.followup.send(
            f"❌ Voice connection error: {e}",
            ephemeral=True
        )
    except Exception as e:
        print(f"❌ /playvc error: {e}")
        await interaction.followup.send(
            f"❌ Could not play the audio: {e}",
            ephemeral=True
        )


# ============================================================
# /stopvc
# ============================================================

@bot.tree.command(
    name="stopvc",
    description="Stop the audio and leave the voice channel"
)
@is_admin_role()
async def stopvc(interaction: discord.Interaction):

    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    voice_client = interaction.guild.voice_client

    if voice_client is None:
        await interaction.response.send_message(
            "❌ I'm not in a voice channel.",
            ephemeral=True
        )
        return

    try:
        if voice_client.is_playing():
            voice_client.stop()

        await voice_client.disconnect()

        await interaction.response.send_message(
            "⏹️ Stopped the audio and left the voice channel.",
            ephemeral=True
        )

    except Exception as e:
        print(f"❌ /stopvc error: {e}")
        await interaction.response.send_message(
            f"❌ Could not leave the voice channel: {e}",
            ephemeral=True
        )


# ============================================================
# RUN BOT
# ============================================================

bot.run(TOKEN)