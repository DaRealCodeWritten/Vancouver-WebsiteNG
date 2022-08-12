import discord
import asyncio
import os
from signal import SIGTERM
from typing import Dict
from subprocess import Popen, CREATE_NEW_CONSOLE
from discord.ext import commands


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
                return True
            embed = discord.Embed(title="Access denied",
                                  description="This command is available to devs only",
                                  color=discord.Colour.red()
                                  )
            await ctx.send(embed=embed)
            return False

    return discord.ext.commands.check(predicate)


class SystemCTL(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.processes: Dict[str, Popen] = {

        }

    @commands.command()
    @is_dev()
    async def systemctl(self, ctx: commands.Context, module: str, action: str):
        modules = {
            "bot": "bot.py",
            "web": "main.py",
            "self": 0
        }
        actions = {
            "start": Popen,
            "stop": None
        }
        do = actions.get(action)
        using = modules.get(module)
        if not isinstance(using, str) and action == "stop":  # Special case 'self'
            await ctx.send("Stopping self...")
            await self.bot.close()
        if action == "stop":
            process = self.processes.get(module)
            if process is None:
                await ctx.send("Couldn't find that process")
                return
            else:
                process.send_signal(SIGTERM)
                await ctx.send("Sent SIGTERM")
                await asyncio.sleep(5)
                if process.poll() is None:
                    await ctx.send("Task did not close, it may be frozen")
                    return
                else:
                    await ctx.send("Task closed")
                    return
        if module == "nginx" and action == "start":
            ngin = Popen(["C:/nginx-1.23.0/nginx.exe"], cwd="C:/nginx-1.23.0/")
            await asyncio.sleep(5)
            if ngin.poll() is None:  # Process is most likely stable if this is True
                self.processes[module] = ngin
                await ctx.send(f"{module} started successfully")
            else:
                await ctx.send(f"{module} appears to have crashed :(")
        if do is None or using is None:
            await ctx.send("Invalid args")
            return
        proc = do([r".\venv\Scripts\python.exe", using], shell=True, creationflags=CREATE_NEW_CONSOLE, cwd=os.getcwd())
        await ctx.send(f"Attempted to {action} {using}")
        await asyncio.sleep(5)  # Wait to see if the process dies
        if proc.poll() is None:  # Process is most likely stable if this is True
            self.processes[module] = proc
            await ctx.send(f"{using} {action}ed successfully")
        else:
            await ctx.send(f"{using} appears to have crashed :(")


def setup(bot):
    bot.add_cog(SystemCTL(bot))
