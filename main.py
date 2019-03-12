import discord
import os
import youtube_dl
from discord.ext import commands
from music import MusicController
import re

TOKEN = os.environ['TOKEN']

client = commands.Bot(command_prefix='')
    
controller = MusicController()

async def connect_voice_channel(ctx):
    channel = ctx.message.author.voice.voice_channel
    if channel:
        server = ctx.message.server
        voice_client = client.voice_client_in(server)
        if not voice_client:
            voice_client = await client.join_voice_channel(channel)
        elif channel != voice_client.channel:
            await voice_client.move_to(channel)
        return voice_client
    else:
        await client.send_message(ctx.message.channel, 'Зайди в голосовой канал')

@client.command(pass_context=True)
async def join(ctx):
    await connect_voice_channel(ctx)

@client.command(pass_context=True)
async def leave(ctx):
    server = ctx.message.server
    voice_client = client.voice_client_in(server)
    if voice_client:
        await voice_client.disconnect()
        text = 'Ладно'
    else:
        text = 'И что?'
    await client.send_message(ctx.message.channel, text)

@client.command(pass_context=True)
async def find(ctx, url):
    voice_client = await connect_voice_channel(ctx)
    if voice_client:
        controller.find(ctx.message.server.id, voice_client, url)

@client.command(pass_context=True)
async def play(ctx):
    controller.play(ctx.message.server.id)

@client.command(pass_context=True)
async def pause(ctx):
    controller.pause(ctx.message.server.id)

@client.command(pass_context=True)
async def skip(ctx):
    controller.skip(ctx.message.server.id)

@client.command(pass_context=True)
async def volume(ctx, vol):
    vol = re.match('([0-9]{1,3})', vol)
    if vol:
        vol = float(vol[1]) / 100
        if vol >= 0. and vol <= 2.:
            controller.volume(ctx.message.server.id, vol)

@client.command(pass_context=True)
async def stop(ctx):
    controller.stop(ctx.message.server.id) 

@client.command(pass_context=True)
async def all(ctx):
    titles = controller.get_titles(ctx.message.server.id)
    await client.send_message(ctx.message.channel, '\n'.join(titles))

client.run(TOKEN)
