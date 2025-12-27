import discord
from discord.ext import commands

# Intents setup (needed for some bot features)
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
client = commands.Bot(command_prefix='!', intents=intents)

# Event: Bot is ready
@client.event
async def on_ready():
    print(f'Logged in as {client.user}!')

# Event: Respond to messages
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.lower() == "hello":
        await message.channel.send("Hello, Moon-kun! 💖")
    
    # Make sure commands still work
    await client.process_commands(message)

# Example command
@client.command()
async def ping(ctx):
    await ctx.send("Pong! 💕")

# === ADD YOUR TOKEN HERE ===
client.run("MTQ1NDIwNjE4NjM0OTAwMjg5NA.GXrSEQ.rbecaadQvOwFDdHsN4lVWQRMh0zqpeuJXQYmIo")
