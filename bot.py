import time
import discord
import mysql.connector
import requests
from typing import Union
from discord.ext import commands, tasks
from utils.configreader import config, return_guild
from socketio.asyncio_server import AsyncServer

"""
def refresh_vatcan():
    headers = {
        "Authorization": config["VATCAN_KEY"]
    }
    crs = db.cursor()
    crs.execute("SELECT * FROM {}".format(config["DATABASE_TABLE"]))
    for entry in crs:
        if entry[1] == 0: # User doesn't have discord linked, ignored
            continue
        else:
            data = requests.get(f"https://api.vatcan.ca/v2/user/{entry[0]}", headers=headers)
            if data.status_code == 404: # Somehow a user without a CID got committed or someone forgot to switch off the dev table
                continue
            else:
                udata = data.json()
                crs.close()
                crs = db.cursor()
                crs.execute(f"UPDATE {config['DATABASE_TABLE']} SET rating = {int(udata['data']['rating'])} WHERE cid = {entry[0]}")
                crs.close()
"""


def find_rating(member_roles, member_rating) -> Union[int, None]:
    rids = [role.id for role in member_roles]
    for rid in rids:
        for rating, role in rating_table.items():
            if role == rid:
                if rating != member_rating:
                    return role
    return None


sock = AsyncServer()
config = config()
guilds = return_guild()
rating_table = guilds["GUILD_ROLES"]
bot = commands.Bot(command_prefix=["!"], case_insensitive=True, intents=discord.Intents.all())
db = mysql.connector.connect(
    user=config["DATABASE_USER"],
    host="host.docker.internal",
    password=config["DATABASE_PASSWORD"],
    database="czvr"
)
bot.datafeed = None
bot.datafeed_url = requests.get("https://status.vatsim.net/status.json").json()["data"]["v3"][0]


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
    await sock.emit("ACK", {"status": "success"})


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


bot.run(config["BOT_TOKEN"])
