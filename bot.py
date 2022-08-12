import time
import discord
import asyncio
import logging
import nest_asyncio
import requests
import sentry_sdk
import concurrent.futures
import mysql.connector
from discord import Guild, Member
from sentry_sdk import capture_exception
from typing import Union
from discord.ext import commands, tasks
from utils.configreader import config, return_guild
import socketio


def asyncio_run(future, as_task=True):
    """
    A better implementation of `asyncio.run`.

    :param future: A future or task or call of an async method.
    :param as_task: Forces the future to be scheduled as task (needed for e.g. aiohttp).
    """

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # no event loop running:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(_to_task(future, as_task, loop))
    else:
        nest_asyncio.apply(loop)
        return asyncio.run(_to_task(future, as_task, loop))


def _to_task(future, as_task, loop):
    if not as_task or isinstance(future, asyncio.Task):
        return future
    return loop.create_task(future)


def find_rating(member_roles, member_rating) -> Union[int, None]:
    rids = [role.id for role in member_roles]
    for rid in rids:
        for rating, role in rating_table.items():
            if role == rid:
                if rating != member_rating:
                    return role
    return None


def find_all_rating_roles(member_roles: list):
    const = []
    for role in member_roles:
        if role.id in rating_table.values():
            const.append(role.id)
    return const


async def bot_startup():
    print("sockio")
    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        result = await loop.run_in_executor(
            pool, sockio)

config = config()
db = mysql.connector.connect(
        user=config["DATABASE_USER"],
        host="host.docker.internal",
        password=config["DATABASE_PASSWORD"],
        database="czvr",
)
logging.basicConfig(level=logging.DEBUG)
sock = socketio.AsyncClient(logger=True, engineio_logger=True)
sock.reconnection_delay_max = 5
sock.reconnection_attempts = 5
guilds = return_guild()
rating_table = guilds["GUILD_ROLES"]
bot = commands.Bot(command_prefix=["!"], case_insensitive=True, intents=discord.Intents.all())
bot.reconnect_attempts = 0
bot.datafeed = None
bot.datafeed_url = requests.get("https://status.vatsim.net/status.json").json()["data"]["v3"][0]
sentry = sentry_sdk.init(
    dsn="https://29825d826a3b4a07a5c4d7c2b70a8355@o1347372.ingest.sentry.io/6625912",
    traces_sample_rate=1.0,
)


@sock.on("disconnect")
def disconnected():
    print("Socket connection to webserver lost")
    bot.reconnect_attempts = 0


@sock.on("reconnect_failed")
def rcfail():
    print("Failed to reconnect to webserver")


@sock.on("reconnect_attempt")
def reconnecta():
    bot.reconnect_attempts += 1
    print(f"Attempting reconnection, attempt {bot.reconnect_attempts}")


@sock.on("reconnect")
def reconnect(attempts):
    print(f"Reconnected after {attempts}")


@sock.on("UPDATE USER")
async def update_user(data):
    guild = bot.get_guild(guilds[f"GUILD_{guilds['GUILD_SETTING']}"])
    user = await guild.fetch_member(data["cid"])
    old_role = find_rating(user.roles, data["rating"])
    role = guild.get_role(old_role)
    await user.remove_roles(role, reason="Vatsim rating updated")
    new_role = rating_table.get(data["rating"])
    role_object = guild.get_role(new_role)
    await user.add_roles(role_object, reason="Vatsim rating updated")


@sock.on("USER DELETED")
async def deleted_user(data):
    print("user deleted")
    print(guilds)
    guild: Guild = bot.get_guild(int(guilds[f"GUILD_{guilds['GUILD_SETTING']}"]))
    dcid = int(data['dcid'])
    user: Member = guild.get_member(dcid)
    if user is None:  # Weird, the user wasnt a part of the server when they deleted their user, ah w/e
        print("User is none")
        return
    else:
        relevant = find_all_rating_roles(user.roles)
        roles = [guild.get_role(role) for role in relevant]
        if any([role is None for role in roles]):
            raise ValueError("Role ID in 'relevant' list does not exist in the guild")
        else:
            bot.loop.create_task(user.remove_roles(*roles, reason="User deleted acct"))


@bot.event
async def on_ready():
    print("Logged in as: " + bot.user.name)


@bot.event
async def on_guild_channel_create(channel):
    setting = guilds["GUILD_SETTING"]
    if channel.category.id == int(guilds[f"GUILD_{guilds['GUILD_SETTING']}_CATEGORY"]):
        await channel.send(f"<@&{guilds[f'GUILD_{setting}_EVENTS_ID']}> New Event!")


@tasks.loop(seconds=30)
async def refresh_feed():
    try:
        dfeed = requests.get(bot.datafeed_url).json()
        if bot.datafeed is None:
            bot.datafeed = dfeed
        else:
            if dfeed["general"]["update"] > bot.datafeed["general"]["update"]:
                bot.datafeed = dfeed
            else:
                pass
    except Exception as e:
        owner = await bot.fetch_user(703104766632263730)
        await owner.send("Error when fetching datafeed: {}".format(e))


@tasks.loop(hours=24)
async def pull_new_certs():
    try:
        headers = {
            "Authorization": config["VATCAN_API_KEY"],
            "Accept": "application/json"
        }    
        data = requests.get("https://vatcan.ca/api/v2/facility/roster", headers=headers).json()
        inner = data.get("data")
        cursor = db.cursor(buffered=True)
        if inner is None:
            raise ValueError("VATCAN API encountered an error")
        else:
            for data in inner["controllers"]:
                cid = data["cid"]
                rating = data["rating"]
                cursor.execute(
                    f"UPDATE {config['DATABASE_TABLE']} SET rating = %s WHERE cid = %s",
                    (
                        rating,
                        cid
                    )
                )
        db.commit()
        cursor.close()
    except Exception as e:
        print("New cert pull failed")
        capture_exception(e)


@tasks.loop(hours=24)
async def update_tasker():
    """Async task to update roles as needed"""
    with db.cursor(buffered=True) as dbcrs:
        guild: discord.Guild = bot.get_guild(int(guilds[f"GUILD_{guilds['GUILD_SETTING']}"]))
        dbcrs.execute("SELECT * FROM {}".format(config["DATABASE_TABLE"]))
        for record in dbcrs:
            if record[1] is None:
                continue
            member: discord.Member = await guild.fetch_member(record[1])
            if member is None:
                # User is not part of the server or a null record was committed, ignore
                continue
            for role in member.roles:
                utd = False
                try:
                    if role.id == rating_table[record[2]]:
                        # User's rating role is up-to-date, ignore
                        utd = True
                        continue
                    else:
                        continue
                except KeyError:
                    # User does not have a rating entry, this is erroneous
                    owner = await bot.fetch_user(703104766632263730)
                    await owner.send("WARN: Erroneous DB entry")
            if not utd:
                role = guild.get_role(rating_table[record[2]])
                await member.add_roles(role, reason="Automatic role update")
                not_matching = find_rating(member.roles, record[2])
                if not_matching is None:
                    continue
                else:
                    role = guild.get_role(not_matching)
                    await member.remove_roles(role, reason="Automatic update")
    dbcrs.close()


def is_dev():
    """Decorator to ensure the user is a dev"""

    async def predicate(ctx):
        if ctx.author.id in [
            703104766632263730,
            212654520855953409,
            160534932970536960
        ]:
            return True
        else:
            if str(ctx.command) == "help":
                return False
            embed = discord.Embed(title="Access denied",
                                  description="This command is available to devs only",
                                  color=discord.Colour.red()
                                  )
            await ctx.send(embed=embed)
            return False

    return discord.ext.commands.check(predicate)


@is_dev()
@bot.command()
async def fupdate(ctx):
    """Force a complete recall of the database"""
    start = time.time()
    await update_tasker()
    await ctx.author.send("Completed database recall")
    end = time.time()
    embed = discord.Embed(title="Completed",
                          description=f"Completion time: {round(end - start, 3)}",
                          color=discord.Colour.green()
                          )
    await ctx.send(embed=embed)


@is_dev()
@bot.command()
async def starttask(ctx):
    """Starts the updater task, pending deprecation in favor of automation"""
    update_tasker.start()
    embed = discord.Embed(title="Completed", description=f"Task started", color=discord.Colour.green())
    await ctx.send(embed=embed)


@is_dev()
@bot.command()
async def stop(ctx):
    """Panic button (closes the bot)"""
    await bot.close()


@bot.command(description="Gets a METAR for the specified ICAO")
async def metar(ctx, icao: str):
    if len(list(icao)) != 4 or not icao.isalnum():
        await ctx.send(embed=discord.Embed(title="Error", description="Invalid ICAO", color=discord.Color.blurple()))
        return
    else:
        response = requests.get("https://metar.vatsim.net/metar.php?id={}".format(icao))
        if response.text == "":
            await ctx.send(
                embed=discord.Embed(
                    title="Error",
                    description="No METAR for that airport",
                    color=discord.Color.blurple()
                )
            )
            return
        embed = discord.Embed(title="METAR Report For {}".format(icao),
                              description=response.text,
                              color=discord.Color.blurple()
                              )
        await ctx.send(embed=embed)

"""
@bot.command(description="See who's online where")
async def vatsim_pilot(ctx, callsign: str):
    snapshot = bot.datafeed["pilots"]
    embed = discord.Embed(title="Working...", description="Looking for that callsign, only be a second")
    if pilot is None:
        await ctx.send("No pilot by that callsign")
        return
    desc = ""
    desc += f"Name: {pilot['name']}\n"
    desc += f"Squawking: {pilot['transponder']}\n"
    desc += f"Altitude: {pilot['altitude']}\n"
    if isinstance(pilot["flight_plan"], dict):
        desc += f"Depart - Arrive: {pilot['flight_plan']['departure']} - {pilot['flight_plan']['arrival']}\n"
        desc += f"Aircraft: {pilot['flight_plan']['aircraft_faa']}"
    else:
        desc += "Flight Plan: Not Filed"
    embed = discord.Embed(title=f"Details for {callsign.upper()}", description=desc, color=discord.Color.green())
    await ctx.send(embed=embed)"""

  
@bot.command()
async def feeder(ctx):
    await refresh_feed.start()


@bot.command()
async def status(ctx: commands.Context):
    connect = {
        True: "Connected",
        False: "Disconnected"
    }
    online = {
        True: "Online",
        False: "Offline"
    }
    web = False
    try: resp = requests.get("https://czvr-bot.xyz/")
    except:
        nginx = False
        print("Nginx refused connection")
        try:
            requests.get("http://127.0.0.1:6880")
        except Exception as e:
            web = False
        else:
            web = True
    else:
        nginx = True
        if resp.status_code == 502: web = False; print("Nginx connect; origin fail")
        else:
            web = True
    if any(var is False for var in [nginx, web, sock.connected]):
        desc = "Service Status: Degraded"
        col = discord.Color.orange()
    else:
        desc = "Service Status: All Systems Online"
        col = discord.Color.green()
    if not web:
        desc = "Service Status: Web Service Offline"
        col = discord.Color.red()
    embed = discord.Embed(
        title="Vancouver Integration Status",
        color=col,
        description=desc
    )
    embed.add_field(name="Webserver (Websocket)", value=f"Status: {connect[sock.connected]}", inline=False)
    embed.add_field(name="Webserver (Nginx)", value=f"Status: {online[nginx]}", inline=False)
    embed.add_field(name="Webserver (Origin)", value=f"Status: {online[web]}", inline=False)
    embed.add_field(name="Bot Latency", value=f"Time in ms: {round(bot.latency*1000, 3)}", inline=False)
    embed.set_footer(text=f"Requested by {str(ctx.author)}", icon_url=ctx.author.avatar_url)
    await ctx.send(embed=embed)


@bot.command(name="readable-status")
async def human_status(ctx):
    access = {
        True: "Website is reachable",
        False: "Website cannot be accessed"
    }
    realtime = {
        True: "Realtime rating roles updates will happen",
        False: "Updates will happen daily"
    }
    web = False
    try:
        resp = requests.get("https://czvr-bot.xyz/")
    except:
        nginx = False
        print("Nginx refused connection")
        try:
            requests.get("http://127.0.0.1:6880")
        except Exception as e:
            web = False
        else:
            web = True
    else:
        nginx = True
        if resp.status_code == 502:
            web = False; print("Nginx connect; origin fail")
        else:
            web = True
    embed = discord.Embed(
        title="Human-readable Web Status",
        color=discord.Color.blue()
    )
    accessible = True if web and nginx else False
    socket = True if web and sock.connected and nginx else False
    embed.add_field(name="Website Accessibility", value=access[accessible], inline=False)
    embed.add_field(name="Realtime Rating Roles Updates", value=realtime[socket], inline=False)
    await ctx.send(embed=embed)


@bot.command()
@is_dev()
async def reconnect_socket(ctx, thru_nginx=True):
    try:
        if isinstance(thru_nginx, str):
            thru_nginx = False
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool, sockio, thru_nginx)
        await asyncio.sleep(5)
        if sock.connected:
            await ctx.send("Connected!")
        else:
            await ctx.send("Didn't connect")
    except Exception as e:
        await ctx.send(f"Error occurred: {e}")


@bot.command()
@is_dev()
async def disconnect_socket(ctx):
    title = "Can't disconnect socket"
    desc = "Socket is not connected"
    color = discord.Color.red()
    if sock.connected:
        title = "Socket disconnected"
        desc = "Successfully closed socket"
        color = discord.Color.green()
        await sock.disconnect()
    embed = discord.Embed(
        title=title,
        description=desc,
        color=color
    )
    await ctx.send(embed=embed)


def sockio(thru_nginx=True):
    async def inner(thru_nginx_inner):  # Inner? I hardly know'er!
        try:
            addr = "https://czvr-bot.xyz" if thru_nginx_inner else "ws://127.0.0.1:6880"
            await sock.connect(addr, wait_timeout=5)
        except Exception as e:
            capture_exception(e)
            return False
        await sock.wait()
    bot.loop.create_task(inner(thru_nginx))


bot.loop.create_task(bot_startup())
bot.run(config["BOT_TOKEN"])
