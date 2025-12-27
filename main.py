import os
import discord
from discord.ext import commands
import random

# -------------------- BOT SETUP --------------------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# -------------------- LOGGING FUNCTION --------------------
def get_log_channel(guild):
    # Replace 'logs' with your logging channel name
    return discord.utils.get(guild.text_channels, name="logs")

async def log_action(guild, message):
    channel = get_log_channel(guild)
    if channel:
        await channel.send(message)

# -------------------- MODERATION COMMANDS --------------------
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"⚡ {member.name} has been kicked from the Solar System.")
    await log_action(ctx.guild, f"⚡ {ctx.author.name} kicked {member.name}. Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"⚡ {member.name} has been banned from the Solar System.")
    await log_action(ctx.guild, f"⚡ {ctx.author.name} banned {member.name}. Reason: {reason}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 Cleared {amount} messages!", delete_after=5)
    await log_action(ctx.guild, f"🧹 {ctx.author.name} cleared {amount} messages in #{ctx.channel.name}")

# -------------------- UTILITY COMMANDS --------------------
@bot.command()
async def choose(ctx, *options):
    if not options:
        await ctx.send("❌ No options provided!")
    else:
        await ctx.send(f"✅ I choose **{random.choice(options)}**!")

@bot.command()
async def poll(ctx, *, question):
    msg = await ctx.send(f"📊 Poll: {question}\nReact with 👍 or 👎")
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(
        f"👤 User Info:\n"
        f"Name: {member.name}\n"
        f"ID: {member.id}\n"
        f"Joined: {member.joined_at}"
    )

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    await ctx.send(
        f"🌐 Server Info:\n"
        f"Name: {guild.name}\n"
        f"Members: {guild.member_count}\n"
        f"Created: {guild.created_at}"
    )

# -------------------- FUN / SYSTEM-THEMED COMMANDS --------------------
@bot.command()
async def compliment(ctx):
    compliments = [
        "🌟 You’re a shining part of the Solar System!",
        "💖 Your presence makes everything brighter!",
        "✨ Nobody organizes fun like you!"
    ]
    await ctx.send(random.choice(compliments))

@bot.command()
async def mood(ctx, mood_type: str):
    moods = {
        "happy": "😄 All systems running smoothly!",
        "sad": "😢 Seems like a glitch… hope you feel better soon!",
        "playful": "😏 Time to orbit some fun!",
        "love": "💖 Sending system-wide love!"
    }
    await ctx.send(moods.get(mood_type.lower(), "⚠️ Mood not recognized."))

@bot.command()
async def orbit(ctx):
    actions = [
        "spins around gracefully 💫",
        "jumps into orbit 🚀",
        "twirls playfully 🌟",
        "glides smoothly through the system ✨"
    ]
    await ctx.send(f"{ctx.author.name} {random.choice(actions)}")

# -------------------- REACTION ROLE SYSTEM --------------------
reaction_roles = {}

@bot.command()
@commands.has_permissions(manage_roles=True)
async def add_reaction_role(ctx, message_id: int, emoji: str, role_name: str):
    message = await ctx.channel.fetch_message(message_id)
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"⚠️ Role '{role_name}' not found!")
        return

    if message.id not in reaction_roles:
        reaction_roles[message.id] = {}
    reaction_roles[message.id][emoji] = role.name
    await message.add_reaction(emoji)
    await ctx.send(f"✅ Reaction role added: {emoji} -> {role.name}")
    await log_action(ctx.guild, f"🛠 {ctx.author.name} added reaction role: {emoji} -> {role.name}")

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

# -------------------- RUN BOT --------------------
bot.run(os.environ['TOKEN'])
