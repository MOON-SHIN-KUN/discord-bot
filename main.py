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
    await bot.tree.sync()
    print(f"{bot.user} is online and slash commands synced!")

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
@bot.tree.command(name="userinfo", description="Get user information")
@app_commands.describe(member="User to get info about (optional)")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    await interaction.response.send_message(
        f"👤 User Info:\n"
        f"Name: {member.name}\n"
        f"ID: {member.id}\n"
        f"Joined: {member.joined_at}"
    )

@bot.tree.command(name="serverinfo", description="Get server information")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    await interaction.response.send_message(
        f"🌐 Server Info:\n"
        f"Name: {guild.name}\n"
        f"Members: {guild.member_count}\n"
        f"Created: {guild.created_at}"
    )

@bot.tree.command(name="choose", description="Choose from multiple options")
@app_commands.describe(options="Provide options separated by space")
async def choose(interaction: discord.Interaction, options: str):
    opts = options.split()
    if not opts:
        await interaction.response.send_message("❌ No options provided!", ephemeral=True)
    else:
        await interaction.response.send_message(f"✅ I choose **{random.choice(opts)}**!")

@bot.tree.command(name="poll", description="Create a poll")
@app_commands.describe(question="Poll question")
async def poll(interaction: discord.Interaction, question: str):
    msg = await interaction.channel.send(f"📊 Poll: {question}\nReact with 👍 or 👎")
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    await interaction.response.send_message("✅ Poll created!", ephemeral=True)

@bot.tree.command(name="compliment", description="Receive a system-themed compliment")
async def compliment(interaction: discord.Interaction):
    compliments = [
        "🌟 You’re a shining part of the Solar System!",
        "💖 Your presence makes everything brighter!",
        "✨ Nobody organizes fun like you!"
    ]
    await interaction.response.send_message(random.choice(compliments))

@bot.tree.command(name="mood", description="Check your mood status")
@app_commands.describe(mood_type="Mood type: happy, sad, playful, love")
async def mood(interaction: discord.Interaction, mood_type: str):
    moods = {
        "happy": "😄 All systems running smoothly!",
        "sad": "😢 Seems like a glitch… hope you feel better soon!",
        "playful": "😏 Time to orbit some fun!",
        "love": "💖 Sending system-wide love"
    }
    await interaction.response.send_message(moods.get(mood_type.lower(), "⚠️ Mood not recognized."))

@bot.tree.command(name="orbit", description="Do a playful orbit action")
async def orbit(interaction: discord.Interaction):
    actions = [
        "spins around gracefully 💫",
        "jumps into orbit 🚀",
        "twirls playfully 🌟",
        "glides smoothly through the system ✨"
    ]
    await interaction.response.send_message(f"{interaction.user.name} {random.choice(actions)}")

# -------------------- HELLO / GREETINGS --------------------
@bot.tree.command(name="hello", description="Say hello in Solar System style")
async def hello(interaction: discord.Interaction):
    greetings = [
        f"👋 Hello {interaction.user.name}! Welcome to the Solar System! 💖",
        f"🌞 Hi {interaction.user.name}! Ready to shine in the system today?",
        f"✨ Hey {interaction.user.name}! Orbiting around to say hello! 😄",
        f"🌟 Greetings {interaction.user.name}! The Solar System welcomes you!"
    ]
    await interaction.response.send_message(random.choice(greetings))

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
