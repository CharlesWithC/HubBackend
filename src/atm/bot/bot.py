# Copyright (C) 2022 Charles All rights reserved.
# Author: @Charles-1414

# DriversHub Bot

import discord,sys
from discord.ext import commands,tasks
    
intents = discord.Intents().all()
bot = commands.Bot(command_prefix='/', intents=intents)