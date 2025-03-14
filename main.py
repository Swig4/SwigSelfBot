import subprocess
import sys
import os
import json
import requests
import random
import time
import hashlib
from datetime import datetime, timezone
ReqPackages = [
    'discord.py',
    'google-generativeai',
    'requests'
]

def installPackages(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

for package in ReqPackages:
    try:
        __import__(package)
    except ImportError:
        print(f"Package '{package}' not found. Installing...")
        installPackages(package)

import discord
import google.generativeai as genai
from io import BytesIO
from discord.ext import commands

ConfigFile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
currentScript = sys.argv[0]
currentVersion = "1.1"
repoUrl = "https://raw.githubusercontent.com/Swig4/SwigSelfBot/main/main.py"

def checkVersion():
    try:
        response = requests.get("https://raw.githubusercontent.com/Swig4/SwigSelfBot/refs/heads/main/version")
        latest = response.text.strip()
        if latest != currentVersion:
            print(f"A new version is available: {latest}. Updating...")
            downloadLatest(latest)
    except Exception as e:
        print(f"Error checking version: {e}")

def downloadLatest(latest):
    try:
        print(f"Downloading the latest version ({latest})...")
        response = requests.get(repoUrl)
        if response.status_code == 200:
            with open(currentScript, "wb") as file:
                file.write(response.content)
            print("Download complete. Replacing current script with the latest version.")
            time.sleep(2)
            os.execl(sys.executable, sys.executable, *sys.argv)
        else:
            print(f"Failed to download the latest version. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error downloading latest version: {e}")

def createConfig():
    if not os.path.exists(ConfigFile):
        token = input("Enter token: ").strip()
        prefix = input("Enter prefix (e.g., '!'): ").strip()
        GoogleKeyInput = input("Enter your Google AI API Key (leave blank if you don't have one): ").strip()
        addToStartup = input("Do you want to add this bot to startup? (y/n): ").strip().lower()
        
        config = {
            "token": token,
            "prefix": prefix,
            "GoogleKey": GoogleKeyInput,
            "addToStartup": addToStartup
        }
        
        with open(ConfigFile, "w") as configFile:
            json.dump(config, configFile, indent=4)
        print(f"Config file created at {ConfigFile}.")
        
        if config["addToStartup"] == "y":
            addToStartupFolder()

def loadConfig():
    with open(ConfigFile, "r") as configFile:
        return json.load(configFile)

def addToStartupFolder():
    if config["addToStartup"] == "y":
        startupFolder = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        scriptPath = sys.argv[0]
        
        if not os.path.exists(startupFolder):
            print(f"Could not find the Startup folder at {startupFolder}.")
            return
        
        scriptName = os.path.basename(scriptPath)
        shortcutPath = os.path.join(startupFolder, scriptName + ".bat")
        
        if os.path.exists(shortcutPath):
            print(f"The bot is already in the startup folder: {shortcutPath}")
            return
        with open(shortcutPath, "w") as batFile:
            batFile.write(f'@echo off\npython "{scriptPath}"\n')
    
        print(f"Bot has been added to startup. You can find the shortcut at {shortcutPath}")

checkVersion()

createConfig()
config = loadConfig()

genai.configure(api_key=config['GoogleKey'])
bot = commands.Bot(command_prefix=config['prefix'], self_bot=True, intents=None, help_command=None)

AskCooldown = {}
Commands = {
    "help": "Shows the help message",
    "ask": "Ask the AI a question and get a response",
    "ping": "Checks your latency",
    "crypto": "Display the current price of any crypto",
    "girlfriend": "Provides a users chance of finding love",
    "kiss": "Kisses a user",
    "hentai": "Sends a hentai gif based on choice",
    "rapeable": "Shows a users rapeable percent based on age",
    "token": "1 in 10,000 chance of leaking your discord token",
    "ghostping": "ghost pings a user",
    "cat": "Sends A random Cat",
    "userinfo": "Sends info about the mentioned user",
    "serverinfo": "Sends info about a server",
    "joke": "Says a silly joke",
    "quote": "Inspires those around you"
}

@bot.command('help')
async def HelpCommand(ctx):
    Helptext = "\n".join([f"> `{config['prefix']}{cmd}` : {desc}" for cmd, desc in Commands.items()])
    HelpMsg = f"**Commands:**\n{Helptext}\nMade by: ``swig5`` and ``java.swing``"
    await ctx.send(HelpMsg, reference=ctx.message)
    await ctx.message.delete()

@bot.command("ask")
async def AskCommand(ctx, *, question: str):
    UserID, Time = ctx.author.id, time.time()
    if not config['GoogleKey']:
        await ctx.send("> Please enter your Google AI API key in ``config.json``\n[Click Here To Get Your Key](https://aistudio.google.com/apikey)", reference=ctx.message)
        await ctx.message.delete()
        return

    if UserID in AskCooldown and Time - AskCooldown[UserID] < 20:
        await ctx.send(f"> Please wait `{int(20 - (Time - AskCooldown[UserID]))}` seconds before asking again.", reference=ctx.message)
        await ctx.message.delete()
        return

    Thinking = await ctx.send("> Thinking...")
    try:
        response = genai.GenerativeModel("gemini-1.5-flash").generate_content(f"{question}, Keep the response under 2000 characters")
        await Thinking.delete()
        await ctx.send(f"> {response.text}", reference=ctx.message)
        AskCooldown[UserID] = Time
    except Exception as e:
        await Thinking.delete()
        await ctx.send(f"> There was an error: {e}", reference=ctx.message)
    finally:
        await ctx.message.delete()

@bot.command("ping")
async def PingCommand(ctx):
    await ctx.send(f"> Pong! :ping_pong: Latency: `{round(bot.latency * 1000)}ms`", reference=ctx.message)
    await ctx.message.delete()

CryptoNames = {
    "btc": "bitcoin", "eth": "ethereum", "ltc": "litecoin", "xrp": "xrp", "xmr": "monero",
    "doge": "dogecoin", "ada": "cardano", "dot": "polkadot", "bnb": "binance-coin", "sol": "solana", "avax": "avalanche"
}

@bot.command("crypto")
async def cryptoCommand(ctx, currency: str):
    fullName = CryptoNames.get(currency.lower(), currency.lower())
    rsp = requests.get(f"https://api.coincap.io/v2/assets/{fullName}")

    if rsp.status_code == 200:
        data = rsp.json().get('data', {})
        if 'priceUsd' in data:
            usdPrice = float(data['priceUsd'])
            priceChange = float(data['changePercent24Hr'])
            unixTimestamp = int(data['timestamp'] / 1000)
            await ctx.send(f"`{fullName}` ~ `${usdPrice:,.2f}` <t:{unixTimestamp}:R>\n"
                           f"> 24hr change: `${usdPrice * priceChange / 100:,.2f} ({priceChange:+.2f}%)`\n"
                           f"> chart: <https://coincap.io/assets/{fullName}>", reference=ctx.message)
        else:
            await ctx.send(f"Could not find data for `{currency}`.", reference=ctx.message)
    else:
        await ctx.send(f"Failed to fetch data for `{currency}` from CoinCap.", reference=ctx.message)

    await ctx.message.delete()

@bot.command("girlfriend")
async def girlfriendCommand(ctx, user: discord.Member = None):
    user = user or ctx.author

    accountCreationDate = user.created_at
    daysOnDiscord = (ctx.message.created_at - accountCreationDate).days
    reductionFactor = (daysOnDiscord // 100) * 5
    finalPercentage = max(0, min(100, random.randint(0, 100) - reductionFactor))

    await ctx.send(f"> {user.mention}'s chance of finding a girlfriend is `{finalPercentage}%`", reference=ctx.message)
    await ctx.message.delete()

@bot.command('kiss')
async def kissCommand(ctx, user: discord.Member = None):
    if user is None:
        user = ctx.author
    try:
        response = requests.get("https://api.otakugifs.xyz/gif?reaction=kiss&format=gif")
        GIFUrl = response.json().get('url')
        
        if GIFUrl:
            await ctx.send(f"> {ctx.author.mention} kissed {user.mention}!\n[gif]({GIFUrl})", reference=ctx.message)
            await ctx.message.delete()
        else:
            await ctx.send("Sorry, I couldn't find a kiss gif. Try again later.", reference=ctx.message)
            await ctx.message.delete()
    except Exception as e:
        await ctx.send(f"Error fetching the gif: {e}", reference=ctx.message)
        await ctx.message.delete()


NSFWTypes = [
    "anal", "blowjob", "cum", "fuck", "neko", "pussylick", "solo", 
    "solo_male", "threesome_fff", "threesome_ffm", "threesome_mmf", 
    "yaoi", "yuri"
]

@bot.command("hentai")
async def HentaiCommand(ctx, *, GIFType: str = "None"):
    if GIFType not in NSFWTypes:
        await ctx.send(f"> Invalid type: `{GIFType}`. Supported types are: `{', '.join(NSFWTypes)}`")
        return
    APIUrl = f"https://purrbot.site/api/img/nsfw/{GIFType}/gif"
    try:
        response = requests.get(APIUrl)
        if response.status_code == 200:
            gif_url = response.json().get("link")
            if gif_url:
                await ctx.send(f"{gif_url}", reference=ctx.message)
                await ctx.message.delete()
            else:
                await ctx.send("> Could not fetch a valid gif. Try again later.", reference=ctx.message)
                await ctx.message.delete()
        else:
            await ctx.send(f"> Failed to fetch gif. API responded with status code: {response.status_code}", reference=ctx.message)
            await ctx.message.delete()
    except Exception as e:
        await ctx.send(f"> An error occurred while fetching the gif: {e}", reference=ctx.message)
        await ctx.message.delete()

@bot.command("rapeable")
async def RapeableCommand(ctx, user: discord.Member, age: int):
    if age <= 0:
        await ctx.send("> Please provide a valid age.")
        return
    Percent = 100 if age <= 15 else max(0, min(100, random.randint(0, 100) - (age * 2)))
    await ctx.send(f"> {user.mention}'s rape percent is `{Percent}%`", reference=ctx.message)
    await ctx.message.delete()




@bot.command("userinfo")
async def userinfo(ctx, user: discord.Member = None):
    user = user or ctx.guild.get_member(ctx.author.id)
    HasNitro = "Yes" if hasattr(user, 'premium_since') and user.premium_since else "No"
    status = str(user.status) if isinstance(user, discord.Member) else "N/A"
    CreationDate = user.created_at.strftime("%B %d, %Y")
    if ctx.guild:
        JoinDate = user.joined_at.strftime("%B %d, %Y")
        roles = [role.name for role in user.roles[1:]]
        RolesList = ', '.join(roles) if roles else "``No roles``"
    else:
        JoinDate = "N/A"
        RolesList = "No roles"
    await ctx.send(f"""
    **User Info:**
    > **Name**: ``{user.name}``
    > **ID**: ``{user.id}``
    > **Nitro**: ``{HasNitro}``
    > **Status**: ``{status}``
    > **Account Created**: ``{CreationDate}``
    > **Joined Date**: ``{JoinDate}``
    > **Roles**: {RolesList}
    > **Avatar**: [Click here]({user.avatar})
    """, reference=ctx.message)
    await ctx.message.delete()

@bot.command("serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    if not guild:
        await ctx.send(f"> This command can only be run in servers", reference=ctx.message)
        await ctx.message.delete()
        return
    CreatedAt = guild.created_at.strftime("%B %d, %Y")
    Icon = guild.icon if guild.icon else "No icon"
    RolesList = ', '.join([role.name for role in guild.roles[1:]]) or "No roles"
    await ctx.send(f"""
    **Server Info:**
    > **Name**: ``{guild.name}``
    > **ID**: ``{guild.id}``
    > **Members**: ``{guild.member_count}``
    > **Created At**: ``{CreatedAt}``
    > **Owner**: ``{guild.owner}``
    > **Roles**: {RolesList}
    > **Icon**: [Click here]({Icon})
    """, reference=ctx.message)
    await ctx.message.delete()

@bot.command("token")
async def token(ctx):
    if int(hashlib.sha256(datetime.now(timezone.utc).isoformat().encode()).hexdigest()[:8], 16) % 10000 == 0:
        await ctx.send(f"> Unlucky ``{config[0]}``", reference=ctx.message)
    else:
        await ctx.send("> You got lucky!", reference=ctx.message)
    
    await ctx.message.delete()

@bot.command("ghostping")
async def ghostping(ctx):
    await ctx.message.delete()

@bot.command("cat")
async def cat(ctx):
    APIUrl = "https://cataas.com/cat/gif"
    response = requests.get(APIUrl)
    
    if response.status_code == 200:
        GIFData = BytesIO(response.content)
        await ctx.send(file=discord.File(GIFData, filename="cat.gif"), reference=ctx.message)
    else:
        await ctx.send(f"> Failed to fetch gif. API responded with status code: {response.status_code}", reference=ctx.message)
    await ctx.message.delete()

import requests

@bot.command("joke")
async def joke(ctx):
    response = requests.get("https://official-joke-api.appspot.com/jokes/random")
    response.raise_for_status()
    data = response.json()
    if data:
        joke = f"> {data['setup']} - {data['punchline']}"
    else:
        joke = "> Couldn't fetch a joke at this time."
    await ctx.send(joke, reference=ctx.message)

    await ctx.message.delete()

@bot.command("quote")
async def quote(ctx):
    response = requests.get("https://qapi.vercel.app/api/random")
    response.raise_for_status()
    data = response.json()
    if data:
        quote = f"\"{data['quote']}\" - {data['author']}"
    else:
        quote = "> Couldn't fetch a quote at this time."
    await ctx.send(f"> {quote}", reference=ctx.message)

    await ctx.message.delete()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        print(f"Command not found? {commands.CommandNotFound}")
        await ctx.send(f"> Oops! :3 That command doesn't exist. Run `{config['prefix']}help` for a list of commands!", reference=ctx.message)
    else:
        print(f"Error? {error}")
        await ctx.send("> An error occurred while processing the command. ^_^", reference=ctx.message)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ✅")

try: 
    print("------------------ DONE INSTALLING NOW LAUNCHING ------------------")
    bot.run(config['token'])
except: print("⚠ Invalid token used! ⚠")
