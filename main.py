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
from datetime import datetime, timezone

#Imported to utilize Supabase
from supabase import create_client

#Loading in variable from the dotenv file
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

db = create_client(supabase_url, supabase_key)

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

#I don't know if this fixes anything but I just pray to god that it does
active_scheduled = set()

active_reminders = {}

#The command prefix line to activate the bot
#the prefix is different in the bot testing purely so that I don't activate the main one instead
bot = commands.Bot(command_prefix='m!', intents=intents, help_command=None)

# Helper functions
def add_scheduled_user(user_id: int, interval: str):
    db.table('scheduled_users').upsert({'user_id': user_id, 'interval': interval}).execute()

def remove_scheduled_user(user_id: int):
    db.table('scheduled_users').delete().eq('user_id', user_id).execute()

def get_scheduled_user(user_id: int):
    result = db.table('scheduled_users').select('interval').eq('user_id', user_id).execute()
    return result.data[0]['interval'] if result.data else None

def get_all_scheduled_users():
    result = db.table('scheduled_users').select('user_id, interval').execute()
    return [(row['user_id'], row['interval']) for row in result.data]

# Timezone helpers
def set_user_timezone(user_id: int, tz: str):
    db.table('user_timezones').upsert({'user_id': user_id, 'timezone': tz}).execute()

def get_user_timezone(user_id: int):
    result = db.table('user_timezones').select('timezone').eq('user_id', user_id).execute()
    return result.data[0]['timezone'] if result.data else None

# Reminder helpers
def add_reminder(user_id: int, reminder_time: str, reminder_text: str, tz: str):
    result = db.table('reminders').insert({
        'user_id': user_id,
        'reminder_time': reminder_time,
        'reminder_text': reminder_text,
        'timezone': tz
    }).execute()
    reminder_id = result.data[0]['id']
    return reminder_id

def get_pending_reminders():
    result = db.table('reminders').select('id, user_id, reminder_time, reminder_text, timezone').execute()
    return [(row['id'], row['user_id'], row['reminder_time'], row['reminder_text'], row['timezone']) for row in result.data]

def get_user_reminder_count(user_id: int):
    result = db.table('reminders').select('id').eq('user_id', user_id).execute()
    return len(result.data)

def remove_reminder(reminder_id: int):
    db.table('reminders').delete().eq('id', reminder_id).execute()



@bot.event
async def on_ready():
    print(f"I am online, {bot.user.name}")

    for user_id, interval in get_all_scheduled_users():
        user = await bot.fetch_user(user_id)
        if user:
            bot.loop.create_task(send_scheduled(user, interval))

    for reminder_id, user_id, reminder_time_str, reminder_text, user_tz in get_pending_reminders():
        user = await bot.fetch_user(user_id)
        if user:
            reminder_time = datetime.fromisoformat(reminder_time_str)
            now = datetime.now(timezone.utc)
            wait_seconds = (reminder_time - now).total_seconds()
            if wait_seconds > 0:
                bot.loop.create_task(fire_reminder(user, reminder_id, reminder_text, wait_seconds, user_tz))
            else:
                bot.loop.create_task(fire_reminder(user, reminder_id, reminder_text, 0, user_tz))
    
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

#this took me for fucking ever to figure out 

# Will change this to remindme instead of reminder since remindme is a more common command
@bot.command()
async def remindme(ctx, *, time_str: str):

    if get_user_reminder_count(ctx.author.id) >= 5:
        await ctx.author.send("You already have 5 pending reminders! Please cancel one with `m!cancelremindme` before adding a new one.")
        return

    user_tz = get_user_timezone(ctx.author.id)

    if not user_tz:
        await ctx.send("You haven't set your timezone yet! Please use `m!settimezone` first.")
        return

    reminder_time = dateparser.parse(time_str.strip(), settings={
        'RETURN_AS_TIMEZONE_AWARE': True,
        'TIMEZONE': user_tz
    })

    if not reminder_time:
        await ctx.send("Couldn't understand the time sorry")
        return

    now = datetime.now(timezone.utc)
    wait_seconds = (reminder_time - now).total_seconds()

    if wait_seconds <= 0:
        await ctx.send("That time is already in the past...")
        return

    await ctx.send("What would you like to be reminded about?")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        reminder_text = msg.content
    except asyncio.TimeoutError:
        await ctx.send("Timed out, please try the command again!")
        return

    

    reminder_id = add_reminder(ctx.author.id, reminder_time.isoformat(), reminder_text, user_tz)
    active_reminders[reminder_id] = asyncio.create_task(sendreminders(ctx, reminder_time, reminder_text, wait_seconds, reminder_id))

    # It seems unnessesary for the bot to say the timezone for the user so that will be removed

    await ctx.send(f"Reminder set for **{reminder_time.strftime('%B %d, %Y at %I:%M %p')} **!")
    
async def sendreminders(ctx, reminder_time, reminder_text, wait_seconds, reminder_id):

    await asyncio.sleep(wait_seconds)

    embed = discord.Embed(
        title="Your Reminder is up!",
        description=reminder_text,
        color=discord.Color.pink()
    )
    embed.set_image(url=random.choice(gif_list))
    await ctx.author.send(embed=embed)

    # Updated to use Supabase instead of get_db() Also I flat out kinda gave up with this line

    result = db.table('reminders').select('id').eq('user_id', ctx.author.id).eq('reminder_text', reminder_text).eq('reminder_time', reminder_time.isoformat()).execute()
    if result.data:
        remove_reminder(result.data[0]['id'])
        
        # checks to see if the reminder is still in memory and removes it
        if reminder_id in active_reminders:
            del active_reminders[reminder_id]



@bot.command()
async def settimezone(ctx):
    await ctx.send("What time is it for you right now? (e.g. `3:45 PM`)")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        time_user = msg.content.strip().upper()

        if "AM" in time_user or "PM" in time_user:
            time_str = msg.content.strip()
        else:
            await ctx.send("Is that in AM or PM? [type AM or PM]")
            ampm_msg = await bot.wait_for('message', check=check, timeout=30.0)
            ampm = ampm_msg.content.strip().upper()
        
            if ampm not in ("AM", "PM") :
                await ctx.send("Please type AM or PM.")
                return

            time_str = f"{msg.content.strip()} {ampm}"

        user_time = dateparser.parse(time_str)

        if not user_time:
            await ctx.send("Couldn't understand that time, please try again!")
            return

        utc_now = datetime.now(timezone.utc)
        user_hour = user_time.hour
        utc_hour = utc_now.hour
        offset = (user_hour - utc_hour) % 24
        if offset > 12:
            offset -= 24
        user_tz = f"Etc/GMT{-offset:+d}"
        set_user_timezone(ctx.author.id, user_tz)
        await ctx.send(f"Got it! I'll use UTC{offset:+d} for your reminders!")

    except asyncio.TimeoutError:
        await ctx.send("Timed out, please try again!")

# Fire reminder function is fixed so that the reminder text will say it's late when the time is actually 
# down.

async def fire_reminder(user, reminder_id: int, reminder_text: str, wait_seconds: float, user_tz: str):

    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)
        
        embed = discord.Embed(
            title="Your Reminder is up",
            description=reminder_text,
            color=discord.Color.pink()
        )
       
        embed.set_image(url=random.choice(gif_list))
        await user.send(embed=embed)
        remove_reminder(reminder_id)
        
        # Removes reminder from Memory
        if reminder_id in active_reminders :
            del active_reminders[reminder_id]
    
    else : 
        
        embed = discord.Embed(
            title="Your Reminder is up sorry the bot was down and missed your time",
            description=reminder_text,
            color=discord.Color.pink()
        )

        embed.set_image(url="https://media2.giphy.com/media/v1.Y2lkPTZjMDliOTUyN2c2eTAwajFnMGVybnMwb3Ixa3JqY3FjOHZiNWN0NnE4cTVkemV3ZyZlcD12MV9naWZzX3NlYXJjaCZjdD1n/C49VVBIByntnxbuCJ7/source.gif")
        await user.send(embed=embed)
        remove_reminder(reminder_id)
        
        # Removes reminder from Memory
        if reminder_id in active_reminders : 
            del active_reminders[reminder_id]

#A cancel reminders script this needs to be looked at further since it's pure ai slop
# edited the name to be 'delremindme' instead.

@bot.command()
async def delremindme(ctx):

    #Also lowkey gave up here, thank you claude for carrying me so much here
    
    result = db.table('reminders').select('id, reminder_time, reminder_text').eq('user_id', ctx.author.id).execute()
    results = [(row['id'], row['reminder_time'], row['reminder_text']) for row in result.data]

    if not results:
        await ctx.send("You have no pending reminders!")
        return

    # Show the user their pending reminders
    reminder_list = ""
    for i, (reminder_id, reminder_time, reminder_text) in enumerate(results, 1):
        parsed_time = datetime.fromisoformat(reminder_time)
        reminder_list += f"**{i}.** {parsed_time.strftime('%B %d, %Y at %I:%M %p')} - {reminder_text}\n"

    # changing this so that the bot sends it to the author privately so the whole server isn't exposed to the users
    # reminders

    await ctx.author.send(f"Your pending reminders:\n{reminder_list}\nReply with the number of the reminder you want to cancel:")

    # I might just move this outside the function since it might come in handy for other functions as well

    def check(m):
        return m.author == ctx.author

    try:
        msg = await bot.wait_for('message', check=check, timeout=30.0)
        choice = int(msg.content.strip())

        if choice < 1 or choice > len(results):
            await ctx.author.send("Invalid number, please try again!")
            return

        reminder_id = results[choice - 1][0]
        remove_reminder(reminder_id)

        # Removes reminder from Memory
        if reminder_id in active_reminders : 
            active_reminders[reminder_id].cancel()
            del active_reminders[reminder_id]

        await ctx.author.send(f"Reminder cancelled!")

    except ValueError:
        await ctx.author.send("Please enter a valid number!")
    except asyncio.TimeoutError:
        await ctx.author.send("Timed out, please try again!")

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

    # Includes some data about the image, I might get rid of the requested user tag because the bot 
    # replies to you anyways
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
        color=discord.Color.purple()
    )

#!kyosaya
@bot.command()
async def kyosaya(ctx):
    await booru_embed(
        ctx,
        tags="sakura_kyouko+miki_sayaka+2girls",
        title="KyoSaya",
        color=discord.Color.blue()
    )

# This is to track users who enter the command multiple times to prevent a bug

@bot.command()
async def hourly(ctx):
    if get_scheduled_user(ctx.author.id) == "hourly":
        remove_scheduled_user(ctx.author.id)
        await ctx.message.add_reaction("❎")
        await ctx.send("Hourly images disabled")
    else:
        if get_scheduled_user(ctx.author.id) == "daily":
            remove_scheduled_user(ctx.author.id)
            # Clears the old loop
            active_scheduled.discard(ctx.author.id)
            await ctx.send("Switched from daily to hourly images!")
        add_scheduled_user(ctx.author.id, "hourly")
        await ctx.message.add_reaction("✅")
        await ctx.send("Hourly images enabled")
        if ctx.author.id not in active_scheduled:
            await send_scheduled(ctx.author, "hourly")

@bot.command()
async def daily(ctx):
    if get_scheduled_user(ctx.author.id) == "daily":
        remove_scheduled_user(ctx.author.id)
        await ctx.message.add_reaction("❎")
        await ctx.send("Daily images disabled")
    else:
        if get_scheduled_user(ctx.author.id) == "hourly":
            remove_scheduled_user(ctx.author.id)
            # Clears the old loop
            active_scheduled.discard(ctx.author.id)
            await ctx.send("Switched from hourly to daily images!")
        add_scheduled_user(ctx.author.id, "daily")
        await ctx.message.add_reaction("✅")
        await ctx.send("Daily images enabled")
        if ctx.author.id not in active_scheduled:
            await send_scheduled(ctx.author, "daily")

# The main function for hourly and daily images, Probably could be better coded to not just repeat the same code
# as the main function for character posts, at the moment madoka is the only tag used. 

async def send_scheduled(user, interval: str):
    active_scheduled.add(user.id)
    sleep_time = 3600  if interval == "hourly" else 86400
    title = "Hourly Image!" if interval == "hourly" else "Daily Image!"

    while get_scheduled_user(user.id) == interval:
        random_page = random.randint(0, 500)
        # changed the tag to just be all of mahou_shoujo_madoka_magica, makes wayy more sense
        url = f"https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=100&pid={random_page}&tags=mahou_shoujo_madoka_magica"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json(content_type=None)
                    if data:
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
                            color=discord.Color.pink()
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
                            text=f"Width: {width_image} Height {height_image}"
                        )
                        await user.send(embed=embed)

        await asyncio.sleep(sleep_time)
    
    #Removes from the active loop when done
    #This prevents the process from doubling because it's being ran through sqlite and memory
    active_scheduled.discard(user.id)

#!dm
@bot.command()
async def dm(ctx):
    await ctx.author.send(
        "Here are the current commands so far on this bot!\n"
        "\n"
        "m!hello - send a hello message to yourself or to another user\n"
        "\n"
        "m!daily or hourly - send a random picture of madoka to you every day or every hour\n"
        "\n"
        "m!remindme - will send you a reminder message at a specific time or date you set it to, it will prompt you for the current time\n"
        "\n"
        "m!cancelremindme - will let you cancel any reminder that you've previously made\n"
        "\n"
        "m!settimezone - you can set what time it is for you at the moment\n"
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
        "There are some secret commands as well, if you can find them let me know cuz that's pretty cool\n"
        "\n"
        "And lastly send bugs you find to me, would gladly appreciate that! This bot is still a work in progress"
        )
    
keep_alive()
bot.run(token, log_handler=handler, log_level=logging.DEBUG)