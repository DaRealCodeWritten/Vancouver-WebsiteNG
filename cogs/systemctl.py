import discord
import asyncio
import psutil
import time
import tqdm
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

    async def _nginx(self, action: str):
        if action == "start":
            task = Popen(["C:/nginx-1.23.0/nginx.exe"], cwd="C:/nginx-1.23.0/")
            await asyncio.sleep(5)
            if task.poll() is None:
                if "nginx" in self.processes.keys():
                    task.terminate()
            return True if task.poll() is None else False
        elif action == "stop":
            for task in tqdm.tqdm([proc for proc in psutil.process_iter()]):
                try:
                    if "nginx" in task.as_dict()["name"]:
                        task.kill()
                        await asyncio.sleep(5)
                        if task.is_running():
                            return False
                        else:
                            if "nginx" in self.processes.keys():
                                self.processes.pop("nginx")
                            continue
                except psutil.NoSuchProcess:
                    continue
            return True

    @commands.command()
    @is_dev()
    async def systemctl(self, ctx: commands.Context, module: str, action: str):
        modules = {
            "nginx": self._nginx,
            "web": None
        }
        func = modules.get(module)
        if func is None:
            await ctx.send("Couldn't find that module")
        else:
            result = await func(action)
            if result:
                await ctx.send("Completed action successfully")
            else:
                await ctx.send(
                    """
                    Something went wrong, the action may have thrown an error or if a task is being started, it crashed
                    """
                )


def setup(bot):
    bot.add_cog(SystemCTL(bot))
