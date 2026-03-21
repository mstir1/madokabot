import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
import aiohttp
import random

#Dummy Server to satisfy the conditions for render
from flask import Flask
from threading import Thread

#Loading in variable from the dotenv file
load_dotenv()
token = os.getenv('DISCORD_TOKEN')

#Dummy webpage with minimal requirements for render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

#The command prefix line to activate the bot
bot = commands.Bot(command_prefix='m!', intents=intents)

#A terminal message notifying me when the bot is online
@bot.event
async def on_ready():
    print(f"I am online, {bot.user.name}")

#This function scans messages posted where the bot has access to post
@bot.event
async def on_message(message):
    if message.author == bot.user :
        return
    
    await bot.process_commands(message)

#!hello
#Adding extra gifs within the script to be used, uses a random index and selects it
@bot.command()
async def hello(ctx):
    gif_list = [
        "https://giffiles.alphacoders.com/349/34921.gif", 
        "https://giffiles.alphacoders.com/157/157971.gif", 
        "https://giffiles.alphacoders.com/157/157963.gif", 
        "https://giffiles.alphacoders.com/156/156529.gif",
        "https://giffiles.alphacoders.com/158/158253.gif"
    ]
    embed=discord.Embed(
        title=f"Hello, {ctx.author.display_name}!",
        color=discord.Color.pink()
    )
    embed.set_image(url=random.choice(gif_list))

    await ctx.reply(embed=embed)

#This function scans safebooru based on the tags from the other bot commands
@bot.command()
async def booru_embed(ctx, tags: str, title: str, color: discord.Color = discord.Color.pink()):
    
    #Because madoka and homura have much more art they have a much bigger range
    if tags in ("kaname_madoka", "akemi_homura"):
        random_page = random.randint(0, 200)
    else:
        random_page = random.randint(0, 50)

    url = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=100&pid={random_page}&tags={tags}"

    #tbh this might be pointless because both Safebooru and Discord use cloudflare..
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                await ctx.send("Couldn't reach Safebooru right now, try again later!")
                return

            data = await response.json(content_type=None)

    if not data :
        await ctx.send("No images found for that tag!")
        return

    # Pick a random post from the results
    post = random.choice(data)

    # Build the image URL from the directory and image fields
    image_url = f"https://safebooru.org/images/{post['directory']}/{post['image']}"
    post_url = f"https://safebooru.org/index.php?page=post&s=view&id={post['id']}"
    source_url = post.get('source', '').strip()
    width_image = post.get('width', '')
    height_image = post.get('height', '')

    embed = discord.Embed(
        title=title,
        url=post_url, 
        color=color
    )
    embed.set_image(url=image_url)

    embed.add_field(
        name="Source",
        value=f"[Link]({source_url})"
        if source_url
        else "No Source Provided",
        inline=True
    )
    embed.set_footer(
        text=f"Requested by {ctx.author.display_name} Width: {width_image} Height {height_image}"
    )

    await ctx.reply(embed=embed)

#!madoka
@bot.command()
async def madoka(ctx):
    await booru_embed(
        ctx, 
        tags="kaname_madoka", 
        title="Madoka Kaname", 
        color=discord.Color.pink()
    )

#!homura
@bot.command()
async def homura(ctx):
    await booru_embed(
        ctx, 
        tags="akemi_homura", 
        title="Akemi Homura", 
        color=discord.Color.purple()
    )

#!sayaka
@bot.command()
async def sayaka(ctx):
    await booru_embed(
        ctx,
        tags="miki_sayaka",
        title="Sayaka Miki",
        color=discord.Color.blue()
    )

#!mami
@bot.command()
async def mami(ctx):
    await booru_embed(
        ctx,
        tags="tomoe_mami",
        title="Mami Tomoe",
        color=discord.Color.yellow()
    )

#!kyoko 
# The most common spelling for her name is Kyoko, however safebooru has her listened as sakura_kyouto instead
@bot.command()
async def kyoko(ctx):
    await booru_embed(
        ctx,
        tags="sakura_kyouko",
        title="Kyoko Sakura",
        color=discord.Color.red()
    )

#!dm
@bot.command()
async def dm(ctx):
    await ctx.author.send(
        "Here are the current commands so far on this bot!\n"
        "\n"
        "m!hello - send a hello message\n"
        "\n"
        "m!madoka - post a random madoka image\n"
        "\n"
        "m!homura - post a picture of homura\n"
        "\n"
        "m!sayaka - post a picture of sayaka\n" 
        "\n"
        "m!mami - post a picture of mami\n"
        "\n"
        "m!kyoko - post a picture of kyoko"
        )
    
keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)