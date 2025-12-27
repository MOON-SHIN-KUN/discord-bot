import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
from datetime import datetime, timedelta

# -------------------- BOT SETUP --------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# -------------------- GLOBAL VARIABLES --------------------
reaction_roles = {}  # {message_id: {emoji: role_name}}
mutes = {}  # {user_id: unmute_time}
GUILD_ID = 123456789012345678  # <-- Replace with your server ID

# -------------------- LOGGING FUNCTION --------------------
def get_log_channel(guild):
    return discord.utils.get(guild.text_channels, name="logs")

async def log_action(guild, message):
    channel = get_log_channel(guild)
    if channel:
        await channel.send(message)

# -------------------- SYNC SLASH COMMANDS --------------------
@bot.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print(f"{bot.user} is online and slash commands synced in the server!")

# -------------------- MODERATION COMMANDS --------------------
@bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.describe(member="User to kick", reason="Reason for kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    await member.kick(reason=reason)
    await interaction.response.send_message(f"⚡ {member.name} was kicked.")
    await log_action(interaction.guild, f"⚡ {interaction.user.name} kicked {member.name}. Reason: {reason}")

@bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.describe(member="User to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    await member.ban(reason=reason)
    await interaction.response.send_message(f"⚡ {member.name} was banned.")
    await log_action(interaction.guild, f"⚡ {interaction.user.name} banned {member.name}. Reason: {reason}")

@bot.tree.command(name="clear", description="Clear messages in a channel")
@app_commands.describe(amount="Number of messages to delete")
async def clear(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 Cleared {amount} messages!", ephemeral=True)
    await log_action(interaction.guild, f"🧹 {interaction.user.name} cleared {amount} messages in #{interaction.channel.name}")

@bot.tree.command(name="mute", description="Mute a member temporarily")
@app_commands.describe(member="User to mute", minutes="Minutes to mute", reason="Reason for mute")
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int = 10, reason: str = None):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await interaction.guild.create_role(name="Muted")
        for channel in interaction.guild.channels:
            await channel.set_permissions(mute_role, speak=False, send_messages=False)
    await member.add_roles(mute_role)
    unmute_time = datetime.utcnow() + timedelta(minutes=minutes)
    mutes[member.id] = unmute_time
    await interaction.response.send_message(f"🔇 {member.name} muted for {minutes} minutes. Reason: {reason}")
    await log_action(interaction.guild, f"🔇 {member.name} muted by {interaction.user.name} for {minutes} minutes. Reason: {reason}")

@bot.tree.command(name="unmute", description="Unmute a member")
@app_commands.describe(member="User to unmute")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role)
        await interaction.response.send_message(f"🔊 {member.name} has been unmuted.")
        await log_action(interaction.guild, f"🔊 {member.name} was unmuted by {interaction.user.name}")
        mutes.pop(member.id, None)
    else:
        await interaction.response.send_message("❌ User is not muted.", ephemeral=True)

# -------------------- REACTION ROLE SYSTEM --------------------
@bot.tree.command(name="add_reaction_role", description="Add a reaction role to a message")
@app_commands.describe(message_id="Message ID", emoji="Emoji to react", role_name="Role name to assign")
async def add_reaction_role(interaction: discord.Interaction, message_id: int, emoji: str, role_name: str):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You don't have permission!", ephemeral=True)
        return
    try:
        message = await interaction.channel.fetch_message(message_id)
    except:
        await interaction.response.send_message("❌ Message not found.", ephemeral=True)
        return
    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if not role:
        await interaction.response.send_message(f"❌ Role '{role_name}' not found!", ephemeral=True)
        return
    if message.id not in reaction_roles:
        reaction_roles[message.id] = {}
    reaction_roles[message.id][emoji] = role.name
    await message.add_reaction(emoji)
    await interaction.response.send_message(f"✅ Reaction role added: {emoji} -> {role.name}")
    await log_action(interaction.guild, f"🛠 {interaction.user.name} added reaction role: {emoji} -> {role.name}")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    if payload.message_id in reaction_roles:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        emoji = str(payload.emoji)
        role_name = reaction_roles[payload.message_id].get(emoji)
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                await member.add_roles(role)
                await log_action(guild, f"🛠 {member.name} received role {role.name} via reaction {emoji}")

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return
    if payload.message_id in reaction_roles:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        emoji = str(payload.emoji)
        role_name = reaction_roles[payload.message_id].get(emoji)
        if role_name:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                await member.remove_roles(role)
                await log_action(guild, f"🛠 {member.name} lost role {role.name} via reaction removal {emoji}")

# -------------------- UTILITY & FUN SLASH COMMANDS --------------------
@bot.tree.command(name="hello", description="Say hello in Solar System style")
async def hello(interaction: discord.Interaction):
    greetings = [
        f"👋 Hello {interaction.user.name}! Welcome to the Solar System! 💖",
        f"🌞 Hi {interaction.user.name}! Ready to shine in the system today?",
        f"✨ Hey {interaction.user.name}! Orbiting around to say hello! 😄",
        f"🌟 Greetings {interaction.user.name}! The Solar System welcomes you!"
    ]
    await interaction.response.send_message(random.choice(greetings))

# ... [Include all previous commands like /compliment, /mood, /orbit, /userinfo, /serverinfo, /choose, /poll here exactly as before] ...

# -------------------- AUTOMATIC UNMUTE TASK --------------------
@tasks.loop(seconds=30)
async def check_mutes():
    now = datetime.utcnow()
    to_unmute = [user_id for user_id, t in mutes.items() if now >= t]
    for user_id in to_unmute:
        for guild in bot.guilds:
            member = guild.get_member(user_id)
            if member:
                mute_role = discord.utils.get(guild.roles, name="Muted")
                if mute_role in member.roles:
                    await member.remove_roles(mute_role)
                    await log_action(guild, f"🔊 {member.name} has been automatically unmuted.")
        mutes.pop(user_id)

check_mutes.start()

# -------------------- RUN BOT --------------------
bot.run(os.environ['TOKEN'])
