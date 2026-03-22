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

#Imported to use for date reminders
import dateparser
import asyncio
from datetime import datetime

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
#the prefix is different in the bot testing purely so that I don't activate the main one instead
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

#Adding extra gifs within the script to be used, uses a random index and selects it
#Removed the gif_list from inside the specific function so it can be used in other functions if needed
gif_list = [
    "https://giffiles.alphacoders.com/349/34921.gif", 
    "https://giffiles.alphacoders.com/157/157971.gif", 
    "https://giffiles.alphacoders.com/157/157963.gif", 
    "https://giffiles.alphacoders.com/156/156529.gif",
    "https://i.redd.it/vrzpzstb080a1.gif",
    "https://giffiles.alphacoders.com/349/34935.gif",
    "https://i.redd.it/nbrln53m6dlc1.gif",
    "https://i.imgur.com/QdrN5eN.gif",
    "https://64.media.tumblr.com/e18a3ee4ed23f1e2786a236cb1af16bd/b51ba43930b74197-d6/s500x750/806aa13be69a06bea2b096aa7123f5eefb1bdbb2.gif",
    "https://i.redd.it/6591xk5vz70a1.gif",
    "https://animewithjisan.wordpress.com/wp-content/uploads/2021/02/homura_attack_golf_club.gif",
    "https://animewithjisan.wordpress.com/wp-content/uploads/2021/02/giphy.gif"
    ]

#This is a set variable to track which users have the daily set activated
daily_users = set()

#This is a set variable for hourly 
hourly_users = set()

#!hello
#Added a member field so users can send hello messages to each other
@bot.command()
async def hello(ctx, member: discord.Member = None):

    target = member if member else ctx.author

    embed=discord.Embed(
        title=f"Hello, {target.display_name}!",
        color=discord.Color.pink()
    )
    embed.set_image(url=random.choice(gif_list))

    await ctx.send(target.mention, embed=embed)

#!reminder
#A very ambitous script that will remind people of whatever they want, I will figure it out later
"""
@bot.command()
async def reminder(ctx, *, time_str: str):
    reminder_time = dateparser.parse(time_str.strip())

    embed=discord.Embed(
        title=f"Your Reminder is up!",
        color=discord.Color.pink()
    )
    embed.set_image(url=random.choice(gif_list))

    if not reminder_time:
        await ctx.send("Couldn't understand the time sorry")
        return
    
    now = datetime.now()
    wait_seconds = (reminder_time - now).total_seconds()

    if wait_seconds <= 0:
        await ctx.send("That time is already in the past...")
        return
    
    await ctx.send(f"Reminder set for {reminder_time.strftime('%B %d, %Y at %I:%M %p')}")
    await asyncio.sleep(wait_seconds)
    await ctx.author.send(embed=embed)
"""


#This function scans safebooru based on the tags from the other bot commands
@bot.command()
async def booru_embed(ctx, tags: str, title: str, color: discord.Color = discord.Color.pink()):
    
    #Because madoka and homura have much more art they have a much bigger range
    if tags in ("kaname_madoka", "akemi_homura"):
        random_page = random.randint(0, 200)
    elif tags in ("kaname_madoka+akemi_homura+2girls" , "kinomoto_sakura"):
        random_page = random.randint(0, 40)
    elif tags in ("sakura_kyouko+miki_sayaka+2girls"):
        random_page = random.randint(0, 15)
    else:
        random_page = random.randint(0, 100)

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

#!sakura
# A little thing for me 
@bot.command()
async def sakura(ctx):
    await booru_embed(
        ctx,
        tags="kinomoto_sakura",
        title="Sakura Kinomoto",
        color=discord.Color.from_str("#f58549")
    )

#!madohomu
# added yuri to the bot
@bot.command()
async def madohomu(ctx):
    await booru_embed(
        ctx,
        tags="kaname_madoka+akemi_homura+2girls",
        title="Madohomu",
        color=discord.Color.from_str("#c084b0")
    )

#!kyosaya
@bot.command()
async def kyosaya(ctx):
    await booru_embed(
        ctx,
        tags="sakura_kyouko+miki_sayaka+2girls",
        title="KyoSaya",
        color=discord.Color.from_str("#7B52AB")
    )


@bot.command()
async def hourly(ctx):
    if ctx.author.id in hourly_users:
        hourly_users.remove(ctx.author.id)
        await ctx.message.add_reaction("❎")
        await ctx.send("Hourly images disabled")
    else:
        # Remove from daily if active
        if ctx.author.id in daily_users:
            daily_users.remove(ctx.author.id)
            await ctx.send("Switched from daily to hourly images!")
        hourly_users.add(ctx.author.id)
        await ctx.message.add_reaction("✅")
        await ctx.send("Hourly images enabled")
        await send_scheduled(ctx.author, "hourly")

@bot.command()
async def daily(ctx):
    if ctx.author.id in daily_users:
        daily_users.remove(ctx.author.id)
        await ctx.message.add_reaction("❎")
        await ctx.send("Daily images disabled")
    else:
        # Remove from hourly if active
        if ctx.author.id in hourly_users:
            hourly_users.remove(ctx.author.id)
            await ctx.send("Switched from hourly to daily images!")
        daily_users.add(ctx.author.id)
        await ctx.message.add_reaction("✅")
        await ctx.send("Daily images enabled")
        await send_scheduled(ctx.author, "daily")

async def send_scheduled(user, interval: str):
    active_set = hourly_users if interval == "hourly" else daily_users
    sleep_time = 3600  if interval == "hourly" else 86400
    title = "Hourly Image!" if interval == "hourly" else "Daily Image!"

    while user.id in active_set:
        random_page = random.randint(0, 200)
        url = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=100&pid={random_page}&tags=kaname_madoka"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    if data:
                        post = random.choice(data)
                        image_url = f"https://safebooru.org/images/{post['directory']}/{post['image']}"
                        post_url = f"https://safebooru.org/index.php?page=post&s=view&id={post['id']}"
                        source_url = post.get('source', '').strip()

                        embed = discord.Embed(title=title, url=post_url, color=discord.Color.pink())
                        embed.set_image(url=image_url)
                        embed.add_field(
                            name="Source",
                            value=f"[Link]({source_url})" if source_url else "No source provided",
                            inline=True
                        )
                        await user.send(embed=embed)

        await asyncio.sleep(sleep_time)

#!dm
@bot.command()
async def dm(ctx):
    await ctx.author.send(
        "Here are the current commands so far on this bot!\n"
        "\n"
        "m!hello - send a hello message to yourself or to another user\n"
        "\n"
        "m!daily or hourly - send a random picture of madoka to you every day or every hour"
        "\n"
        "m!madoka - post a random madoka image\n"
        "\n"
        "m!homura - post a picture of homura\n"
        "\n"
        "m!sayaka - post a picture of sayaka\n" 
        "\n"
        "m!mami - post a picture of mami\n"
        "\n"
        "m!kyoko - post a picture of kyoko\n"
        "\n"
        "There are some secret commands as well, if you can find them let me know cuz that's pretty cool"
        )
    
keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)