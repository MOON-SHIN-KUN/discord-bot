import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='!', intents=intents)

@client.event
async def on_ready():
    print(f'Logged in as {client.user}!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if message.content.lower() == "hello":
        await message.channel.send("Hello, Moon-kun! 💖")
    
    await client.process_commands(message)

@client.command()
async def ping(ctx):
    await ctx.send("Pong! 💕")

# ✅ Use the secret here
client.run(os.environ['TOKEN'])
