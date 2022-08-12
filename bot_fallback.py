import discord
from discord.ext import commands
from utils.configreader import config


bot = commands.Bot(command_prefix="f!", intents=discord.Intents.all())
bot.remove_command("help")


@bot.event
async def on_ready():
    bot.load_extension("cogs.systemctl")


@bot.command(name="help")
async def helper(ctx):
    embed = discord.Embed(
        title="Fallback Mode",
        description=f"Hi {ctx.author.name}! I am currently in fallback mode, most features are unavailable currently",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)


@bot.command(name="fallbacks", aliases=["metar",])
async def fallbacks(ctx):
    embed = discord.Embed(
        title="Fallback Mode",
        description=f"Hi {ctx.author.name}! I am currently in fallback mode, most features are unavailable currently",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)


bot.run(config()['BOT_TOKEN'])
