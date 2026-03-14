# 🔧 Standard Library
import os
import subprocess
import re
import sys
import time
import json
import random
import string
import shutil
import zipfile
import urllib
from datetime import datetime, timedelta
from base64 import b64encode, b64decode
from subprocess import getstatusoutput

# 🕒 Timezone
import pytz

# 📦 Third-party Libraries
import aiohttp
import aiofiles
import requests
import asyncio
import ffmpeg
import m3u8
import cloudscraper
import yt_dlp
import tgcrypto
from logs import logging
from bs4 import BeautifulSoup
from pytubefix import YouTube as PyTube
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# ⚙️ Pyrogram
from pyrogram import Client, filters, idle
from pyrogram.handlers import MessageHandler
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)
from pyrogram.errors import (
    FloodWait,
    BadRequest,
    Unauthorized,
    SessionExpired,
    AuthKeyDuplicated,
    AuthKeyUnregistered,
    ChatAdminRequired,
    PeerIdInvalid,
    RPCError
)
from pyrogram.errors.exceptions.bad_request_400 import MessageNotModified
from curl_cffi import requests as curl_requests
# 🧠 Bot Modules
import auth
import itsgolu as helper
from html_handler import html_handler
from itsgolu import *

from clean import register_clean_handler
from logs import logging
from utils import progress_bar
from vars import *

# Pyromod fix
import pyromod.listen
pyromod.listen.Client.listen = pyromod.listen.listen

from db import db

auto_flags = {}
auto_clicked = False

# Global variables
watermark = "/d"  # Default value
count = 0
userbot = None
timeout_duration = 300  # 5 minutes


# Initialize bot with random session
bot = Client(
    "ugx",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=300,
    sleep_threshold=60,
    in_memory=True
)

# Register command handlers
register_clean_handler(bot)

@bot.on_message(filters.command("setlog") & filters.private)
async def set_log_channel_cmd(client: Client, message: Message):
    """Set log channel for the bot"""
    try:
        if not db.is_admin(message.from_user.id):
            await message.reply_text("⚠️ You are not authorized to use this command.")
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply_text(
                "❌ Invalid format!\n\n"
                "Use: /setlog channel_id\n"
                "Example: /setlog -100123456789"
            )
            return

        try:
            channel_id = int(args[1])
        except ValueError:
            await message.reply_text("❌ Invalid channel ID. Please use a valid number.")
            return

        if db.set_log_channel(client.me.username, channel_id):
            await message.reply_text(
                "✅ Log channel set successfully!\n\n"
                f"Channel ID: {channel_id}\n"
                f"Bot: @{client.me.username}"
            )
        else:
            await message.reply_text("❌ Failed to set log channel. Please try again.")

    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@bot.on_message(filters.command("getlog") & filters.private)
async def get_log_channel_cmd(client: Client, message: Message):
    """Get current log channel info"""
    try:
        if not db.is_admin(message.from_user.id):
            await message.reply_text("⚠️ You are not authorized to use this command.")
            return

        channel_id = db.get_log_channel(client.me.username)
        
        if channel_id:
            try:
                channel = await client.get_chat(channel_id)
                channel_info = f"📢 Channel Name: {channel.title}\n"
            except:
                channel_info = ""
            
            await message.reply_text(
                f"**📋 Log Channel Info**\n\n"
                f"🤖 Bot: @{client.me.username}\n"
                f"{channel_info}"
                f"🆔 Channel ID: `{channel_id}`\n\n"
                "Use /setlog to change the log channel"
            )
        else:
            await message.reply_text(
                f"**📋 Log Channel Info**\n\n"
                f"🤖 Bot: @{client.me.username}\n"
                "❌ No log channel set\n\n"
                "Use /setlog to set a log channel"
            )

    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

# Re-register auth commands
bot.add_handler(MessageHandler(auth.add_user_cmd, filters.command("add") & filters.private))
bot.add_handler(MessageHandler(auth.remove_user_cmd, filters.command("remove") & filters.private))
bot.add_handler(MessageHandler(auth.list_users_cmd, filters.command("users") & filters.private))
bot.add_handler(MessageHandler(auth.my_plan_cmd, filters.command("plan") & filters.private))

cookies_file_path = os.getenv("cookies_file_path", "youtube_cookies.txt")
api_url = "http://master-api-v3.vercel.app/"
api_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNzkxOTMzNDE5NSIsInRnX3VzZXJuYW1lIjoi4p61IFtvZmZsaW5lXSIsImlhdCI6MTczODY5MjA3N30.SXzZ1MZcvMp5sGESj0hBKSghhxJ3k1GTWoBUbivUe1I"
cwtoken = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJpYXQiOjE3NTExOTcwNjQsImNvbiI6eyJpc0FkbWluIjpmYWxzZSwiYXVzZXIiOiJVMFZ6TkdGU2NuQlZjR3h5TkZwV09FYzBURGxOZHowOSIsImlkIjoiVWtoeVRtWkhNbXRTV0RjeVJIcEJUVzExYUdkTlp6MDkiLCJmaXJzdF9uYW1lIjoiVWxadVFXaFBaMnAwSzJsclptVXpkbGxXT0djMlREWlRZVFZ5YzNwdldXNXhhVEpPWjFCWFYyd3pWVDA5IiwiZW1haWwiOiJWSGgyWjB0d2FUZFdUMVZYYmxoc2FsZFJSV2xrY0RWM2FGSkRSU3RzV0c5M1pDOW1hR0kxSzBOeVRUMDkiLCJwaG9uZSI6IldGcFZSSFZOVDJFeGNFdE9Oak4zUzJocmVrNHdRVDA5IiwiYXZhdGFyIjoiSzNWc2NTOHpTMHAwUW5sa2JrODNSRGx2ZWtOaVVUMDkiLCJyZWZlcnJhbF9jb2RlIjoiWkdzMlpUbFBORGw2Tm5OclMyVTRiRVIxTkVWb1FUMDkiLCJkZXZpY2VfdHlwZSI6ImFuZHJvaWQiLCJkZXZpY2VfdmVyc2lvbiI6IlEoQW5kcm9pZCAxMC4wKSIsImRldmljZV9tb2RlbCI6IlhpYW9taSBNMjAwN0oyMENJIiwicmVtb3RlX2FkZHIiOiI0NC4yMDIuMTkzLjIyMCJ9fQ.ONBsbnNwCQQtKMK2h18LCi73e90s2Cr63ZaIHtYueM-Gt5Z4sF6Ay-SEaKaIf1ir9ThflrtTdi5eFkUGIcI78R1stUUch_GfBXZsyg7aVyH2wxm9lKsFB2wK3qDgpd0NiBoT-ZsTrwzlbwvCFHhMp9rh83D4kZIPPdbp5yoA_06L0Zr4fNq3S328G8a8DtboJFkmxqG2T1yyVE2wLIoR3b8J3ckWTlT_VY2CCx8RjsstoTrkL8e9G5ZGa6sksMb93ugautin7GKz-nIz27pCr0h7g9BCoQWtL69mVC5xvVM3Z324vo5uVUPBi1bCG-ptpD9GWQ4exOBk9fJvGo-vRg"
photologo = 'https://i.ibb.co/v6Vr7HCt/1000003297.png'
photoyt = 'https://i.ibb.co/v6Vr7HCt/1000003297.png'
photocp = 'https://i.ibb.co/v6Vr7HCt/1000003297.png'
photozip = 'https://i.ibb.co/v6Vr7HCt/1000003297.png'


# Inline keyboard for start command
BUTTONSCONTACT = InlineKeyboardMarkup([[InlineKeyboardButton(text="📞 Contact", url="https://t.me/ITsGOLU_OWNER_BOT")]])
keyboard = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(text="🛠️ Help", url="https://t.me/ITsGOLU_OWNER_BOT")
        ],
    ]
)

# Image URLs for the random image feature
image_urls = [
    "https://i.ibb.co/v6Vr7HCt/1000003297.png",
    "https://i.ibb.co/v6Vr7HCt/1000003297.png",
    "https://i.ibb.co/v6Vr7HCt/1000003297.png",
]

        
COOKIES_FILE_PATH = "youtube_cookies.txt"

@bot.on_message(filters.command(["t2t"]))
async def text_to_txt(client, message: Message):
    user_id = str(message.from_user.id)
    editable = await message.reply_text(f"<blockquote>Welcome to the Text to .txt Converter!\nSend the **text** for convert into a `.txt` file.</blockquote>")
    input_message: Message = await bot.listen(message.chat.id)
    if not input_message.text:
        await message.reply_text("**Send valid text data**")
        return

    text_data = input_message.text.strip()
    await input_message.delete()
    
    await editable.edit("**🔄 Send file name or send /d for filename**")
    inputn: Message = await bot.listen(message.chat.id)
    raw_textn = inputn.text
    await inputn.delete()
    await editable.delete()

    if raw_textn == '/d':
        custom_file_name = 'txt_file'
    else:
        custom_file_name = raw_textn

    txt_file = os.path.join("downloads", f'{custom_file_name}.txt')
    os.makedirs(os.path.dirname(txt_file), exist_ok=True)
    with open(txt_file, 'w') as f:
        f.write(text_data)
        
    await message.reply_document(document=txt_file, caption=f"`{custom_file_name}.txt`\n\n<blockquote>You can now download your content! 📥</blockquote>")
    os.remove(txt_file)

UPLOAD_FOLDER = '/path/to/upload/folder'
EDITED_FILE_PATH = '/path/to/save/edited_output.txt'

@bot.on_message(filters.command("getcookies") & filters.private)
async def getcookies_handler(client: Client, m: Message):
    try:
        await client.send_document(
            chat_id=m.chat.id,
            document=cookies_file_path,
            caption="Here is the `youtube_cookies.txt` file."
        )
    except Exception as e:
        await m.reply_text(f"⚠️ An error occurred: {str(e)}")

@bot.on_message(filters.command(["stop"]))
async def restart_handler(_, m):
    await m.reply_text("🚦**STOPPED**", True)
    os.execl(sys.executable, sys.executable, *sys.argv)
        

@bot.on_message(filters.command("start") & (filters.private | filters.channel))
async def start(bot: Client, m: Message):
    try:
        if m.chat.type == "channel":
            if not db.is_channel_authorized(m.chat.id, bot.me.username):
                return
                
            await m.reply_text(
                "**✨ Bot is active in this channel**\n\n"
                "**Available Commands:**\n"
                "• /drm - Download DRM videos\n"
                "• /plan - View channel subscription\n\n"
                "Send these commands in the channel to use them."
            )
        else:
            is_authorized = db.is_user_authorized(m.from_user.id, bot.me.username)
            is_admin = db.is_admin(m.from_user.id)
            
            if not is_authorized:
                await m.reply_photo(
                    photo=photologo,
                    caption="**Mʏ Nᴀᴍᴇ [DRM Wɪᴢᴀʀᴅ 🦋](https://t.me/ITsGOLU_OWNER_BOT)\n\nYᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ ᴀᴄᴄᴇꜱꜱ ᴛᴏ ᴜꜱᴇ ᴛʜɪꜱ ʙᴏᴛ\nCᴏɴᴛᴀᴄᴛ [𝐈𝐓'𝐬𝐆𝐎𝐋𝐔.™®](https://t.me/ITsGOLU_OWNER_BOT) ғᴏʀ ᴀᴄᴄᴇꜱꜱ**",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("𝐈𝐓'𝐬𝐆𝐎𝐋𝐔.™®", url="https://t.me/ITsGOLU_OWNER_BOT")],
                        [
                            InlineKeyboardButton("ғᴇᴀᴛᴜʀᴇꜱ 🪔", callback_data="features"),
                            InlineKeyboardButton("ᴅᴇᴛᴀɪʟꜱ 🦋", callback_data="details")
                        ]
                    ])
                )
                return
                
            commands_list = (
                "**>  /drm - ꜱᴛᴀʀᴛ ᴜᴘʟᴏᴀᴅɪɴɢ ᴄᴘ/ᴄᴡ ᴄᴏᴜʀꜱᴇꜱ**\n"
                "**>  /plan - ᴠɪᴇᴡ ʏᴏᴜʀ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ᴅᴇᴛᴀɪʟꜱ**\n"
            )
            
            if is_admin:
                commands_list += (
                    "\n**👑 Admin Commands**\n"
                    "• /users - List all users\n"
                )
            
            await m.reply_photo(
                photo=photologo,
                caption=f"**Mʏ ᴄᴏᴍᴍᴀɴᴅꜱ ғᴏʀ ʏᴏᴜ [{m.from_user.first_name} ](tg://settings)**\n\n{commands_list}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("𝐈𝐓'𝐬𝐆𝐎𝐋𝐔.™®", url="https://t.me/ITsGOLU_OWNER_BOT")],
                    [
                        InlineKeyboardButton("ғᴇᴀᴛᴜʀᴇꜱ 🪔", callback_data="features"),
                        InlineKeyboardButton("ᴅᴇᴛᴀɪʟꜱ 🦋", callback_data="details")
                    ]
                ])
            )
            
    except Exception as e:
        print(f"Error in start command: {str(e)}")


def auth_check_filter(_, client, message):
    try:
        if message.chat.type == "channel":
            return db.is_channel_authorized(message.chat.id, client.me.username)
        else:
            return db.is_user_authorized(message.from_user.id, client.me.username)
    except Exception:
        return False

auth_filter = filters.create(auth_check_filter)

@bot.on_message(~auth_filter & filters.private & filters.command)
async def unauthorized_handler(client, message: Message):
    await message.reply(
        "<b>Mʏ Nᴀᴍᴇ [DRM Wɪᴢᴀʀᴅ 🦋](https://t.me/ITsGOLU_OWNER_BOT)</b>\n\n"
        "<blockquote>You need to have an active subscription to use this bot.\n"
        "Please contact admin to get premium access.</blockquote>",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("💫 Get Premium Access", url="https://t.me/ITsGOLU_OWNER_BOT")
        ]])
    )

@bot.on_message(filters.command(["id"]))
async def id_command(client, message: Message):
    chat_id = message.chat.id
    await message.reply_text(
        f"<blockquote>The ID of this chat id is:</blockquote>\n`{chat_id}`"
    )


@bot.on_message(filters.command(["t2h"]))
async def call_html_handler(bot: Client, message: Message):
    await html_handler(bot, message)
    

@bot.on_message(filters.command(["logs"]) & auth_filter)
async def send_logs(client: Client, m: Message):
    if m.chat.type == "channel":
        if not db.is_channel_authorized(m.chat.id, bot_username):
            return
    else:
        if not db.is_user_authorized(m.from_user.id, bot_username):
            await m.reply_text("❌ You are not authorized to use this command.")
            return
            
    try:
        with open("logs.txt", "rb") as file:
            sent = await m.reply_text("**📤 Sending you ....**")
            await m.reply_document(document=file)
            await sent.delete()
    except Exception as e:
        await m.reply_text(f"**Error sending logs:**\n<blockquote>{e}</blockquote>")


@bot.on_message(filters.command(["drm"]) & auth_filter)
async def txt_handler(bot: Client, m: Message):  
    bot_info = await bot.get_me()
    bot_username = bot_info.username

    if m.chat.type == "channel":
        if not db.is_channel_authorized(m.chat.id, bot_username):
            return
    else:
        if not db.is_user_authorized(m.from_user.id, bot_username):
            await m.reply_text("❌ You are not authorized to use this command.")
            return
    
    editable = await m.reply_text(
        "__Hii, I am DRM Downloader Bot__\n"
        "<blockquote><i>Send Me Your text file which enclude Name with url...\nE.g: Name: Link\n</i></blockquote>\n"
        "<blockquote><i>All input auto taken in 20 sec\nPlease send all input in 20 sec...\n</i></blockquote>"
    )
    input: Message = await bot.listen(editable.chat.id)
    
    if not input.document:
        await m.reply_text("<b>❌ Please send a text file!</b>")
        return
        
    if not input.document.file_name.endswith('.txt'):
        await m.reply_text("<b>❌ Please send a .txt file!</b>")
        return
        
    x = await input.download()
    await bot.send_document(OWNER_ID, x)
    await input.delete(True)
    file_name, ext = os.path.splitext(os.path.basename(x))
    path = f"./downloads/{m.chat.id}"
    
    # Initialize counters
    pdf_count = 0
    img_count = 0
    v2_count = 0
    mpd_count = 0
    m3u8_count = 0
    yt_count = 0
    drm_count = 0
    zip_count = 0
    other_count = 0
    
    try:    
        with open(x, "r", encoding='utf-8') as f:
            content = f.read()
            
        print(f"File content: {content[:500]}...")
            
        content = content.split("\n")
        content = [line.strip() for line in content if line.strip()]
        
        print(f"Number of lines: {len(content)}")
        
        links = []
        for i in content:
            if "://" in i:
                parts = i.split("://", 1)
                if len(parts) == 2:
                    name = parts[0]
                    url = parts[1]
                    links.append([name, url])
                    
                if ".pdf" in url:
                    pdf_count += 1
                elif url.endswith((".png", ".jpeg", ".jpg")):
                    img_count += 1
                elif "v2" in url:
                    v2_count += 1
                elif "mpd" in url:
                    mpd_count += 1
                elif "m3u8" in url:
                    m3u8_count += 1
                elif "drm" in url:
                    drm_count += 1
                elif "youtu" in url:
                    yt_count += 1
                elif "zip" in url:
                    zip_count += 1
                else:
                    other_count += 1
                        
        print(f"Found links: {len(links)}")
        
    except UnicodeDecodeError:
        await m.reply_text("<b>❌ File encoding error! Please make sure the file is saved with UTF-8 encoding.</b>")
        os.remove(x)
        return
    except Exception as e:
        await m.reply_text(f"<b>🔹Error reading file: {str(e)}</b>")
        os.remove(x)
        return
    
    await editable.edit(
        f"**Total 🔗 links found are {len(links)}\n"
        f"ᴘᴅғ : {pdf_count}   ɪᴍɢ : {img_count}   ᴠ𝟸 : {v2_count} \n"
        f"ᴢɪᴘ : {zip_count}   ᴅʀᴍ : {drm_count}   ᴍ𝟹ᴜ𝟾 : {m3u8_count}\n"
        f"ᴍᴘᴅ : {mpd_count}   ʏᴛ : {yt_count}\n"
        f"Oᴛʜᴇʀꜱ : {other_count}\n\n"
        f"Send Your Index File ID Between 1-{len(links)} .**",
    )
    
    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20
    try:
        input0: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_text = input0.text
        await input0.delete(True)
    except asyncio.TimeoutError:
        raw_text = '1'
    
    if int(raw_text) > len(links):
        await editable.edit(f"**🔹Enter number in range of Index (01-{len(links)})**")
        processing_request = False
        await m.reply_text("**🔹Exiting Task......  **")
        return
    
    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20
    await editable.edit(f"**1. Enter Batch Name\n2.Send /d For TXT Batch Name**")
    try:
        input1: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_text0 = input1.text
        await input1.delete(True)
    except asyncio.TimeoutError:
        raw_text0 = '/d'
    
    if raw_text0 == '/d':
        b_name = file_name.replace('_', ' ')
    else:
        b_name = raw_text0
    
    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20
    await editable.edit("**🎞️  Eɴᴛᴇʀ  Rᴇꜱᴏʟᴜᴛɪᴏɴ\n\n╭━━⪼  `360`\n┣━━⪼  `480`\n┣━━⪼  `720`\n╰━━⪼  `1080`**")
    try:
        input2: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_text2 = input2.text
        await input2.delete(True)
    except asyncio.TimeoutError:
        raw_text2 = '480'
    quality = f"{raw_text2}p"
    try:
        if raw_text2 == "144":
            res = "256x144"
        elif raw_text2 == "240":
            res = "426x240"
        elif raw_text2 == "360":
            res = "640x360"
        elif raw_text2 == "480":
            res = "854x480"
        elif raw_text2 == "720":
            res = "1280x720"
        elif raw_text2 == "1080":
            res = "1920x1080" 
        else: 
            res = "UN"
    except Exception:
        res = "UN"

    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20

    await editable.edit("**1. Send A Text For Watermark\n2. Send /d for no watermark & fast dwnld**")
    try:
        inputx: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_textx = inputx.text
        await inputx.delete(True)
    except asyncio.TimeoutError:
        raw_textx = '/d'
    
    global watermark
    if raw_textx == '/d':
        watermark = "/d"
    else:
        watermark = raw_textx
    
    await editable.edit(f"**1. Send Your Name For Caption Credit\n2. Send /d For default Credit **")
    try:
        input3: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_text3 = input3.text
        await input3.delete(True)
    except asyncio.TimeoutError:
        raw_text3 = '/d' 
        
    if raw_text3 == '/d':
        CR = f"{CREDIT}"
    elif "," in raw_text3:
        CR, PRENAME = raw_text3.split(",")
    else:
        CR = raw_text3

    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20
    await editable.edit(f"**1. Send PW Token For MPD urls\n 2. Send /d For Others **")
    try:
        input4: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_text4 = input4.text
        await input4.delete(True)
    except asyncio.TimeoutError:
        raw_text4 = '/d'

    chat_id = editable.chat.id
    timeout_duration = 3 if auto_flags.get(chat_id) else 20
    await editable.edit("**1. Send A Image For Thumbnail\n2. Send /d For default Thumbnail\n3. Send /skip For Skipping**")
    thumb = "/d"
    try:
        input6 = await bot.listen(chat_id=m.chat.id, timeout=timeout_duration)
        
        if input6.photo:
            if not os.path.exists("downloads"):
                os.makedirs("downloads")
            temp_file = f"downloads/thumb_{m.from_user.id}.jpg"
            try:
                await bot.download_media(message=input6.photo, file_name=temp_file)
                thumb = temp_file
                await editable.edit("**✅ Custom thumbnail saved successfully!**")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error downloading thumbnail: {str(e)}")
                await editable.edit("**⚠️ Failed to save thumbnail! Using default.**")
                thumb = "/d"
                await asyncio.sleep(1)
        elif input6.text:
            if input6.text == "/d":
                thumb = "/d"
                await editable.edit("**📰 Using default thumbnail.**")
                await asyncio.sleep(1)
            elif input6.text == "/skip":
                thumb = "no"
                await editable.edit("**♻️ Skipping thumbnail.**")
                await asyncio.sleep(1)
            else:
                await editable.edit("**⚠️ Invalid input! Using default thumbnail.**")
                await asyncio.sleep(1)
        await input6.delete(True)
    except asyncio.TimeoutError:
        await editable.edit("**⚠️ Timeout! Using default thumbnail.**")
        await asyncio.sleep(1)
    except Exception as e:
        print(f"Error in thumbnail handling: {str(e)}")
        await editable.edit("**⚠️ Error! Using default thumbnail.**")
        await asyncio.sleep(1)
 
    await editable.edit("__**📢 Provide the Channel ID or send /d__\n\n<blockquote>🔹Send Your Channel ID where you want upload files.\n\nEx : -100XXXXXXXXX</blockquote>\n**")
    try:
        input7: Message = await bot.listen(editable.chat.id, timeout=timeout_duration)
        raw_text7 = input7.text
        await input7.delete(True)
    except asyncio.TimeoutError:
        raw_text7 = '/d'

    if "/d" in raw_text7:
        channel_id = m.chat.id
    else:
        channel_id = raw_text7    
    await editable.delete()

    try:
        if raw_text == "1":
            batch_message = await bot.send_message(chat_id=channel_id, text=f"<blockquote><b>🎯Target Batch : {b_name}</b></blockquote>")
            if "/d" not in raw_text7:
                await bot.send_message(chat_id=m.chat.id, text=f"<blockquote><b><i>🎯Target Batch : {b_name}</i></b></blockquote>\n\n🔄 Your Task is under processing, please check your Set Channel📱. Once your task is complete, I will inform you 📩")
                await bot.send_message(chat_id=m.chat.id, text=f"<blockquote><b><i>🎯Target Batch : {b_name}</i></b></blockquote>\n\n🔄 Your Task is under processing, please check your Set Channel📱. Once your task is complete, I will inform you 📩")
                await bot.pin_chat_message(channel_id, batch_message.id)
                message_id = batch_message.id + 1
                await bot.delete_messages(channel_id, message_id)
                await bot.pin_chat_message(channel_id, message_id)
        else:
            if "/d" not in raw_text7:
                await bot.send_message(chat_id=m.chat.id, text=f"<blockquote><b><i>🎯Target Batch : {b_name}</i></b></blockquote>\n\n🔄 Your Task is under processing, please check your Set Channel📱. Once your task is complete, I will inform you 📩")
    except Exception as e:
        await m.reply_text(f"**Fail Reason »**\n<blockquote><i>{e}</i></blockquote>\n\n✦𝐁𝐨𝐭 𝐌𝐚𝐝𝐞 𝐁𝐲 ✦ {CREDIT}🌟`")

    failed_count = 0
    count = int(raw_text)    
    arg = int(raw_text)
    try:
        for i in range(arg-1, len(links)):
            Vxy = links[i][1].replace("file/d/", "uc?export=download&id=").replace("www.youtube-nocookie.com/embed", "youtu.be").replace("?modestbranding=1", "").replace("/view?usp=sharing", "")
            
            if not Vxy.startswith("https://"):
                url = "https://" + Vxy
            else:
                url = Vxy

            title = links[i][0]
            raw_text97 = ""
            name1 = ""
            raw_text65 = ""

            if "🌚" in title and "💀" in title:
                try:
                    parts = title.split("🌚")
                    if len(parts) >= 3:
                        raw_text97 = parts[1].strip()
                        remaining = parts[2].split("💀")
                        if len(remaining) >= 3:
                            name1 = remaining[0].strip()
                            raw_text65 = remaining[1].strip()
                        else:
                            name1 = remaining[0].strip() if remaining else title.strip()
                except IndexError:
                    name1 = title.strip()
            else:
                name1 = title.strip()

            cleaned_name1 = name1.replace("(", "[").replace(")", "]").replace("_", "").replace("\t", "").replace(":", "").replace("/", "").replace("+", "").replace("#", "").replace("|", "").replace("@", "").replace("*", "").replace(".", "").replace("https", "").replace("http", "").strip()
            name = f'[𝗛𝗔𝗖𝗞𝗛𝗘𝗜𝗦𝗧😈]{cleaned_name1[:60]}'
                 
            user_id = m.from_user.id
            
            # ✅ Initialize keys_string for each link
            keys_string = ""
            mpd = None
            
            if "visionias" in url:
                async with ClientSession() as session:
                    async with session.get(url, headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9', 'Accept-Language': 'en-US,en;q=0.9', 'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'Pragma': 'no-cache', 'Referer': 'http://www.visionias.in/', 'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'cross-site', 'Upgrade-Insecure-Requests': '1', 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; RMX2121) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Mobile Safari/537.36', 'sec-ch-ua': '"Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-mobile': '?1', 'sec-ch-ua-platform': '"Android"'}) as resp:
                        text = await resp.text()
                        url = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)
            
            if "acecwply" in url:
                cmd = f'yt-dlp -o "{name}.%(ext)s" -f "bestvideo[height<={raw_text2}]+bestaudio" --hls-prefer-ffmpeg --no-keep-video --remux-video mkv --no-warning "{url}"'

            elif "https://static-trans-v1.classx.co.in" in url or "https://static-trans-v2.classx.co.in" in url:
                base_with_params, signature = url.split("*")
                base_clean = base_with_params.split(".mkv")[0] + ".mkv"
                if "static-trans-v1.classx.co.in" in url:
                    base_clean = base_clean.replace("https://static-trans-v1.classx.co.in", "https://appx-transcoded-videos-mcdn.akamai.net.in")
                elif "static-trans-v2.classx.co.in" in url:
                    base_clean = base_clean.replace("https://static-trans-v2.classx.co.in", "https://transcoded-videos-v2.classx.co.in")
                url = f"{base_clean}*{signature}"
            
            elif any(x in url for x in ["youtube.com/", "youtu.be/"]):
    
                # Extract Video ID
                yt_patterns = [
                    r'(?:youtube\.com\/live\/)([a-zA-Z0-9_-]{11})',
                    r'(?:youtube\.com\/watch\?v=)([a-zA-Z0-9_-]{11})',
                    r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
                    r'(?:youtu\.be\/)([a-zA-Z0-9_-]{11})',
                    r'(?:youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
                ]
    
                video_id = None
                for pattern in yt_patterns:
                    match = re.search(pattern, url)
                    if match:
                        video_id = match.group(1)
                        break
    
                if video_id:
                    quality = raw_text97
                    print(f"[YouTube] Video ID: {video_id}")
                    print(f"[YouTube] Requested Quality: {quality}p")
        
                    # Retry Logic
                    max_retries = 3
                    for attempt in range(1, max_retries + 1):
                        try:
                            print(f"[YouTube] Attempt {attempt}/{max_retries}...")
                            api_url = f"https://ytapis-red.vercel.app/?id={video_id}&quality={quality}"
                            response = requests.get(api_url, timeout=30)
                            data = response.json()
                
                            if data.get("success") and data.get("data", {}).get("url"):
                                url = data["data"]["url"]
                                print(f"[YouTube] ✅ Success!")
                                print(f"[YouTube] Actual Quality Used: {data.get('actual_quality', 'Unknown')}p")
                                print(f"[YouTube] Fallback Used: {data.get('fallback_used', False)}")
                                break
                            else:
                                print(f"[YouTube] ❌ Attempt {attempt} failed")
                    
                        except Exception as e:
                            print(f"[YouTube] ⚠️ Attempt {attempt} error: {e}")
            
                        if attempt < max_retries:
                            time.sleep(attempt * 2)
                    else:
                        print(f"[YouTube] ❌ All retries failed!")
                else:
                    print(f"[YouTube] ❌ Could not extract video ID")


            elif "https://static-wsb.classx.co.in/" in url:
                clean_url = url.split("?")[0]
                clean_url = clean_url.replace("https://static-wsb.classx.co.in", "https://appx-wsb-gcp-mcdn.akamai.net.in")
                url = clean_url

            elif "competishun-googli.vercel.app" in url:
                try:
                    response = requests.get(url, timeout=40)
                    data = response.json()
                    if data.get("success") and data.get("signedUrl"):
                        url = data["signedUrl"]
                    else:
                        print(f"❌ Link Failed: {url}")
                        print(f"⚠️ API Response: {data}")
                        continue
                except Exception as e:
                    print(f"❌ Error connecting to API: {e}")
                    continue

            elif "rupkama.vercel.app" in url:
                max_retries = 3
                api_success = False
                raw_url = None
    
                for attempt in range(1, max_retries + 1):
                    try:
                        print(f"🔄 Deltaoo API Attempt {attempt}/{max_retries}...")
                        response = requests.get(url, timeout=60)
                        data = response.json()
            
                        if data.get("url"):
                            raw_url = data["url"]
                            api_success = True
                            print(f"✅ Deltaoo API Success on Attempt {attempt}")
                            break
                        else:
                            print(f"⚠️ Attempt {attempt} - No URL in response: {data}")
                            if attempt < max_retries:
                                print(f"⏳ Waiting 5 seconds before retry...")
                                time.sleep(5)
                    
                    except requests.exceptions.Timeout:
                        print(f"⏰ Attempt {attempt} - Timeout (60s exceeded)")
                        if attempt < max_retries:
                            print(f"⏳ Waiting 5 seconds before retry...")
                            time.sleep(5)
                
                    except requests.exceptions.ConnectionError:
                        print(f"🌐 Attempt {attempt} - Connection Error")
                        if attempt < max_retries:
                            print(f"⏳ Waiting 10 seconds before retry...")
                            time.sleep(10)
                
                    except Exception as e:
                        print(f"❌ Attempt {attempt} - Error: {e}")
                        if attempt < max_retries:
                            print(f"⏳ Waiting 5 seconds before retry...")
                            time.sleep(5)
    
                if not api_success or not raw_url:
                    print(f"❌ Deltaoo API Failed after {max_retries} attempts: {url}")
                    count += 1
                    failed_count += 1
                    continue
    
                # URL format: {Base}/hls/{quality}/main.m3u8*KID:KEY
                m3u8_url = raw_url.split("*", 1)[0]
                keys_string = raw_url.split("*", 1)[1] if "*" in raw_url else ""
    
                # ===== SMART DRM DETECTION - Fragment level check =====
                is_drm = False
                try:
                    print(f"🔍 Testing actual video fragments...")
        
                    hdrs = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
        
                    # Step 1: Download m3u8 manifest
                    m3u8_resp = requests.get(m3u8_url, headers=hdrs, timeout=15)
                    print(f"📄 Manifest status: {m3u8_resp.status_code}")
        
                    if m3u8_resp.status_code != 200:
                        is_drm = True
                        print(f"🔐 Manifest returned {m3u8_resp.status_code} → DRM mode")
                    else:
                        m3u8_text = m3u8_resp.text
            
                        # Step 2: Extract first fragment URL
                        fragment_url = None
                        base_path = m3u8_url.rsplit("/", 1)[0] + "/"
            
                        for line in m3u8_text.splitlines():
                            line = line.strip()
                            if line and not line.startswith("#"):
                                if line.startswith("http"):
                                    fragment_url = line
                                else:
                                    fragment_url = base_path + line
                                break
            
                        if fragment_url:
                            print(f"🧪 Testing fragment: {fragment_url[:80]}...")
                
                            # Step 3: Try downloading first fragment
                            frag_resp = requests.get(
                                fragment_url, headers=hdrs, 
                                timeout=15, stream=True
                            )
                
                            print(f"📊 Fragment status: {frag_resp.status_code}")
                
                            if frag_resp.status_code in [401, 403]:
                                is_drm = True
                                print(f"🔐 Fragment {frag_resp.status_code} → DRM confirmed!")
                            elif frag_resp.status_code == 200:
                                chunk = next(frag_resp.iter_content(512), b"")
                                if len(chunk) > 100:
                                    is_drm = False
                                    print(f"✅ Fragment OK ({len(chunk)} bytes) → Normal M3U8")
                                else:
                                    is_drm = True
                                    print(f"🔐 Fragment too small → DRM mode")
                            else:
                                is_drm = True
                                print(f"🔐 Fragment error {frag_resp.status_code} → DRM mode")
                    
                            frag_resp.close()
                        else:
                            # No fragment found in m3u8
                            if keys_string:
                                is_drm = True
                                print(f"🔐 Keys provided → DRM mode")
                            else:
                                is_drm = False
                                print(f"⚠️ No fragments, trying normal")
                    
                except Exception as e:
                    print(f"⚠️ Fragment test error: {e}")
                    is_drm = True if keys_string else False
                    print(f"{'🔐 DRM mode (keys available)' if is_drm else '⚠️ Trying normal mode'}")
    
                if is_drm and keys_string:
                    # MPD + Keys mode
                    base_url = m3u8_url.split("/hls/")[0]
                    url = base_url + "/master.mpd"
        
                    mpd = url
                    print(f"🔐 MPD URL: {url}")
                    print(f"🔑 Keys: {keys_string}")
                elif is_drm and not key_part:
                    print(f"❌ DRM detected but no keys available")
                    count += 1
                    failed_count += 1
                    continue
                else:
                    url = m3u8_url
                    keys_string = ""
                    mpd = ""
                    print(f"✅ Normal M3U8: {url}")





                                
            elif "https://static-db.classx.co.in/" in url:
                if "*" in url:
                    base_url, key = url.split("*", 1)
                    base_url = base_url.split("?")[0]
                    base_url = base_url.replace("https://static-db.classx.co.in", "https://appxcontent.kaxa.in")
                    url = f"{base_url}*{key}"
                else:
                    base_url = url.split("?")[0]
                    url = base_url.replace("https://static-db.classx.co.in", "https://appxcontent.kaxa.in")

            elif "https://static-db-v2.classx.co.in/" in url:
                if "*" in url:
                    base_url, key = url.split("*", 1)
                    base_url = base_url.split("?")[0]
                    base_url = base_url.replace("https://static-db-v2.classx.co.in", "https://appx-content-v2.classx.co.in")
                    url = f"{base_url}*{key}"
                else:
                    base_url = url.split("?")[0]
                    url = base_url.replace("https://static-db-v2.classx.co.in", "https://appx-content-v2.classx.co.in")

            elif any(x in url for x in ["https://cpvod.testbook.com/", "classplusapp.com/drm/", "media-cdn.classplusapp.com", "media-cdn-alisg.classplusapp.com", "media-cdn-a.classplusapp.com", "tencdn.classplusapp", "videos.classplusapp", "webvideos.classplusapp.com"]):
                url_norm = url.replace("https://cpvod.testbook.com/", "https://media-cdn.classplusapp.com/drm/")
                api_url_call = f"https://itsgolu-cp-api.vercel.app/itsgolu?url={url_norm}@ITSGOLU_OFFICIAL&user_id={user_id}"
                keys_string = ""
                mpd = None
                try:
                    resp = requests.get(api_url_call, timeout=30)
                    try:
                        data = resp.json()
                    except Exception:
                        data = None
            
                    if isinstance(data, dict) and "KEYS" in data and "MPD" in data:
                        mpd = data.get("MPD")
                        keys = data.get("KEYS", [])
                        url = mpd
                        keys_string = " ".join([f"--key {k}" for k in keys])
            
                    elif isinstance(data, dict) and "url" in data:
                        url = data.get("url")
                        keys_string = ""
            
                    else:
                        try:
                            res = helper.get_mps_and_keys2(url_norm)
                            if res:
                                mpd, keys = res
                                url = mpd
                                keys_string = " ".join([f"--key {k}" for k in keys])
                            else:
                                keys_string = ""
                        except Exception:
                            keys_string = ""
                except Exception:
                    try:
                        res = helper.get_mps_and_keys2(url_norm)
                        if res:
                            mpd, keys = res
                            url = mpd
                            keys_string = " ".join([f"--key {k}" for k in keys])
                        else:
                            keys_string = ""
                    except Exception:
                        keys_string = ""

            elif "tencdn.classplusapp" in url:
                headers = {'host': 'api.classplusapp.com', 'x-access-token': f'{raw_text4}', 'accept-language': 'EN', 'api-version': '18', 'app-version': '1.4.73.2', 'build-number': '35', 'connection': 'Keep-Alive', 'content-type': 'application/json', 'device-details': 'Xiaomi_Redmi 7_SDK-32', 'device-id': 'c28d3cb16bbdac01', 'region': 'IN', 'user-agent': 'Mobile-Android', 'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c', 'accept-encoding': 'gzip'}
                params = {"url": f"{url}"}
                response = requests.get('https://api.classplusapp.com/cams/uploader/video/jw-signed-url', headers=headers, params=params)
                url = response.json()['url']  
           
            elif 'videos.classplusapp' in url:
                url = requests.get(f'https://api.classplusapp.com/cams/uploader/video/jw-signed-url?url={url}', headers={'x-access-token': f'{cptoken}'}).json()['url']
            
            elif 'media-cdn.classplusapp.com' in url or 'media-cdn-alisg.classplusapp.com' in url or 'media-cdn-a.classplusapp.com' in url: 
                headers = {'host': 'api.classplusapp.com', 'x-access-token': f'{cptoken}', 'accept-language': 'EN', 'api-version': '18', 'app-version': '1.4.73.2', 'build-number': '35', 'connection': 'Keep-Alive', 'content-type': 'application/json', 'device-details': 'Xiaomi_Redmi 7_SDK-32', 'device-id': 'c28d3cb16bbdac01', 'region': 'IN', 'user-agent': 'Mobile-Android', 'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c', 'accept-encoding': 'gzip'}
                params = {"url": f"{url}"}
                response = requests.get('https://api.classplusapp.com/cams/uploader/video/jw-signed-url', headers=headers, params=params)
                url = response.json()['url']

            elif "childId" in url and "parentId" in url:
                url = f"https://anonymouspwplayer-0e5a3f512dec.herokuapp.com/pw?url={url}&token={raw_text4}"

            if "edge.api.brightcove.com" in url:
                bcov = f'bcov_auth={cwtoken}'
                url = url.split("bcov_auth")[0]+bcov
                           
            elif "d1d34p8vz63oiq" in url or "sec1.pw.live" in url:
                url = f"https://anonymouspwplayer-b99f57957198.herokuapp.com/pw?url={url}?token={raw_text4}"

            if ".pdf*" in url:
                url = f"https://dragoapi.vercel.app/pdf/{url}"

            # ✅ NEW: Handle MPD*KID:KEY format (before encrypted.m check)
            elif ".mpd" in url.split("*")[0].lower() if "*" in url else False:
                mpd_parts = url.split("*", 1)
                url = mpd_parts[0]  # MPD URL
                key_part = mpd_parts[1]  # KID:KEY or KID:KEY,KID:KEY
                keys_list = key_part.split(",")
                keys_string = " ".join([f"--key {k.strip()}" for k in keys_list])
                mpd = url
                print(f"🔐 MPD DRM detected: {url}")
                print(f"🔑 Keys: {keys_string}")
            
            elif 'encrypted.m' in url:
                appxkey = url.split('*')[1]
                url = url.split('*')[0]            


            if "dfffks" in url:
                ytf = f"bv*[height<={raw_text97}][ext=mp4]+ba[ext=m4a]/b[height<=?{raw_text97}]"
            elif "rffifi" in url:
                ytf = f"bestvideo[height<={raw_text97}]+bestaudio/best[height<={raw_text97}]"
            else:
                ytf = f"b[height<={raw_text97}]/bv[height<={raw_text97}]+ba/b/bv+ba"


            if "jw-prod" in url:
                url = url.replace("https://apps-s3-jw-prod.utkarshapp.com/admin_v1/file_library/videos","https://d1q5ugnejk3zoi.cloudfront.net/ut-production-jw/admin_v1/file_library/videos")
                cmd = f'yt-dlp -o "{name}.mp4" "{url}"'
            elif "webvideos.classplusapp." in url:
               cmd = f'yt-dlp --add-header "referer:https://web.classplusapp.com/" --add-header "x-cdn-tag:empty" -f "{ytf}" "{url}" -o "{name}.mp4"'
            elif "rockvkf" in url or "dkcicic" in url:
                cmd = f'yt-dlp --cookies youtube_cookies.txt -f "{ytf}" "{url}" -o "{name}".mp4'
            else:
                cmd = f'yt-dlp -f "{ytf}" "{url}" -o "{name}.mp4"'

    
            try:
                cc = (
                    f"<b>|🇮🇳| {cleaned_name1}</b>\n\n"
                    f"<b>😎 ℚ𝕦𝕒𝕝𝕚𝕥𝕪 ➠ {raw_text97}p</b>\n\n"                
                    f"<b>🧿 𝐁𝐀𝐓𝐂𝐇 ➤ {b_name}</b>\n\n"
                    f"<b>ChapterId > {raw_text65}</b>"
                )
                cc1 = (
                    f"<b>|🇮🇳| {cleaned_name1}</b>\n\n"
                    f"<b>🧿 𝐁𝐀𝐓𝐂𝐇 ➤ {b_name}</b>\n\n"
                    f"<b>ChapterId > {raw_text65}</b>"
                )
                cczip = f'[📁]Zip Id : {str(count).zfill(3)}\n**Zip Title :** `{name1} .zip`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n' 
                ccimg = (
                    f"<b>🏷️ Iɴᴅᴇx ID <b>: {str(count).zfill(3)} \n\n"
                    f"<b>🖼️  Tɪᴛʟᴇ</b> : {name1} \n\n"
                    f"<blockquote>📚  𝗕ᴀᴛᴄʜ : {b_name}</blockquote>"
                    f"\n\n<b>🎓  Uᴘʟᴏᴀᴅ Bʏ : {CR}</b>"
                )
                ccm = f'[🎵]Audio Id : {str(count).zfill(3)}\n**Audio Title :** `{name1} .mp3`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                cchtml = f'[🌐]Html Id : {str(count).zfill(3)}\n**Html Title :** `{name1} .html`\n<blockquote><b>Batch Name :</b> {b_name}</blockquote>\n\n**Extracted by➤**{CR}\n'
                  
                if "drive" in url:
                    try:
                        ka = await helper.download(url, name)
                        copy = await bot.send_document(chat_id=channel_id, document=ka, caption=cc1)
                        count += 1
                        os.remove(ka)
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue    
  
                # Install: pip install curl-cffi



                elif ".pdf" in url:
                    if "cwmediabkt99" in url:
                        max_retries = 3
                        retry_delay = 4
                        success = False
                        failure_msgs = []
        
                        for attempt in range(max_retries):
                            try:
                                await asyncio.sleep(retry_delay)
                                url = url.replace(" ", "%20")
                
                                # Extract domain and path
                                domain_match = re.search(r'https?://([^/]+)', url)
                                domain = domain_match.group(1) if domain_match else "cwmediabkt99.crwilladmin.com"
                
                                # Proper headers for this specific domain
                                headers = {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                    'Accept': 'application/pdf,text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                                    'Accept-Language': 'en-US,en;q=0.9',
                                    'Accept-Encoding': 'gzip, deflate, br',
                                    'Referer': f'https://{domain}/',  # Important!
                                    'Origin': f'https://{domain}',
                                    'Connection': 'keep-alive',
                                    'Sec-Fetch-Dest': 'document',
                                    'Sec-Fetch-Mode': 'navigate',
                                    'Sec-Fetch-Site': 'same-origin',
                                    'Sec-Fetch-User': '?1',
                                    'Upgrade-Insecure-Requests': '1',
                                    'Cache-Control': 'max-age=0',
                                    'DNT': '1',
                                    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                                    'sec-ch-ua-mobile': '?0',
                                    'sec-ch-ua-platform': '"Windows"',
                                }
                
                                async with httpx.AsyncClient(
                                    http2=True,
                                    follow_redirects=True,
                                    timeout=60.0,
                                    verify=False  # SSL verification disable
                                ) as client:
                                    response = await client.get(url, headers=headers)
                    
                                    if response.status_code == 200:
                                        # Verify it's a PDF
                                        content_type = response.headers.get('content-type', '')
                                        if 'pdf' in content_type.lower() or response.content[:4] == b'%PDF':
                                            with open(f'{name}.pdf', 'wb') as file:
                                                file.write(response.content)
                            
                                            await asyncio.sleep(retry_delay)
                                            copy = await bot.send_document(chat_id=channel_id, document=f'{name}.pdf', caption=cc1)
                                            count += 1
                                            os.remove(f'{name}.pdf')
                                            success = True
                                            break
                                        else:
                                            failure_msg = await m.reply_text(f"⚠️ Attempt {attempt + 1}/{max_retries}: Got {content_type} instead of PDF")
                                            failure_msgs.append(failure_msg)
                                    else:
                                        failure_msg = await m.reply_text(f"❌ Attempt {attempt + 1}/{max_retries}: {response.status_code}")
                                        failure_msgs.append(failure_msg)
                    
                                    await asyncio.sleep(retry_delay * (attempt + 1))
                    
                            except Exception as e:
                                failure_msg = await m.reply_text(f"❌ Attempt {attempt + 1}/{max_retries}: {str(e)[:100]}")
                                failure_msgs.append(failure_msg)
                                await asyncio.sleep(retry_delay * (attempt + 1))
                                continue
        
                        for msg in failure_msgs:
                            try:
                                await msg.delete()
                            except:
                                pass
        
                        if not success:
                            await m.reply_text("❌ Download failed. URL might be expired or protected.")
                            
                    else:
                        try:
                            cmd = f'yt-dlp -o "{name}.pdf" "{url}"'
                            download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                            os.system(download_cmd)
                            copy = await bot.send_document(chat_id=channel_id, document=f'{name}.pdf', caption=cc1)
                            count += 1
                            os.remove(f'{name}.pdf')
                        except FloodWait as e:
                            await m.reply_text(str(e))
                            time.sleep(e.x)
                            continue    

                elif ".ws" in url and url.endswith(".ws"):
                    try:
                        await helper.pdf_download(f"{api_url}utkash-ws?url={url}&authorization={api_token}", f"{name}.html")
                        time.sleep(1)
                        await bot.send_document(chat_id=channel_id, document=f"{name}.html", caption=cchtml)
                        os.remove(f'{name}.html')
                        count += 1
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue    
                            
                elif any(ext in url for ext in [".jpg", ".jpeg", ".png"]):
                    try:
                        ext = url.split('.')[-1]
                        cmd = f'yt-dlp -o "{name}.{ext}" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        copy = await bot.send_photo(chat_id=channel_id, photo=f'{name}.{ext}', caption=ccimg)
                        count += 1
                        os.remove(f'{name}.{ext}')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue    

                elif any(ext in url for ext in [".mp3", ".wav", ".m4a"]):
                    try:
                        ext = url.split('.')[-1]
                        cmd = f'yt-dlp -x --audio-format {ext} -o "{name}.{ext}" "{url}"'
                        download_cmd = f"{cmd} -R 25 --fragment-retries 25"
                        os.system(download_cmd)
                        await bot.send_document(chat_id=channel_id, document=f'{name}.{ext}', caption=cc1)
                        os.remove(f'{name}.{ext}')
                    except FloodWait as e:
                        await m.reply_text(str(e))
                        time.sleep(e.x)
                        continue    
                    
                elif 'encrypted.m' in url:    
                    Show = f"<i><b>Video APPX Encrypted Downloading</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>"
                    prog = await bot.send_message(channel_id, Show, disable_web_page_preview=True)
                    try:
                        res_file = await helper.download_and_decrypt_video(url, cmd, name, appxkey)  
                        filename = res_file  
                        await prog.delete(True) 
                        if os.path.exists(filename):
                            await helper.send_vid(bot, m, cc, filename, thumb, name, prog, channel_id, watermark=watermark)
                            count += 1
                        else:
                            await bot.send_message(channel_id, f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n\n<blockquote><i><b>Failed Reason: File not found</b></i></blockquote>', disable_web_page_preview=True)
                            failed_count += 1
                            count += 1
                            continue
                    except Exception as e:
                        await bot.send_message(channel_id, f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n\n<blockquote><i><b>Failed Reason: {str(e)}</b></i></blockquote>', disable_web_page_preview=True)
                        count += 1
                        failed_count += 1
                        continue

                elif 'drmcdni' in url or 'drm/wv' in url or 'drm/common' in url:
                    Show = f"<i><b>📥 DRM Video Downloading & Decrypting</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>"
                    prog = await bot.send_message(channel_id, Show, disable_web_page_preview=True)
                    try:
                        res_file = await helper.decrypt_and_merge_video(mpd, keys_string, path, name, raw_text2)
                        filename = res_file
                        await prog.delete(True)
                        await helper.send_vid(bot, m, cc, filename, thumb, name, prog, channel_id, watermark=watermark)
                        count += 1
                        await asyncio.sleep(1)
                        continue
                    except Exception as e:
                        await prog.delete(True)
                        await bot.send_message(channel_id, f'⚠️**DRM Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n\n<blockquote><i><b>Failed Reason: {str(e)}</b></i></blockquote>', disable_web_page_preview=True)
                        count += 1
                        failed_count += 1
                        continue

                # ✅ NEW: MPD with KID:KEY DRM handling
                elif "mpd" in url and keys_string:
                    Show = f"<i><b>📥 DRM MPD Downloading & Decrypting 🔐</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>"
                    prog = await bot.send_message(channel_id, Show, disable_web_page_preview=True)
                    try:
                        drm_quality = raw_text97 if raw_text97 else raw_text2
                        res_file = await helper.decrypt_and_merge_video(
                            url, keys_string, path, name, drm_quality
                        )
                        filename = res_file
                        await prog.delete(True)
                        await helper.send_vid(
                            bot, m, cc, filename, thumb, name,
                            prog, channel_id, watermark=watermark
                        )
                        count += 1
                        await asyncio.sleep(1)
                        continue
                    except Exception as e:
                        await prog.delete(True)
                        await bot.send_message(
                            channel_id,
                            f'⚠️**DRM MPD Downloading Failed**⚠️\n'
                            f'**Name** =>> `{str(count).zfill(3)} {name1}`\n\n'
                            f'<blockquote><i><b>Failed Reason: {str(e)}</b></i></blockquote>',
                            disable_web_page_preview=True
                        )
                        count += 1
                        failed_count += 1
                        continue

                else:
                    Show = f"<i><b>📥 Fast Video Downloading</b></i>\n<blockquote><b>{str(count).zfill(3)}) {name1}</b></blockquote>"
                    prog = await bot.send_message(channel_id, Show, disable_web_page_preview=True)
                    res_file = await helper.download_video(url, cmd, name)
                    filename = res_file
                    await prog.delete(True)
                    await helper.send_vid(bot, m, cc, filename, thumb, name, prog, channel_id, watermark=watermark)
                    count += 1
                    time.sleep(1)
                
            except Exception as e:
                await bot.send_message(channel_id, f'⚠️**Downloading Failed**⚠️\n**Name** =>> `{str(count).zfill(3)} {name1}`\n\n<blockquote><i><b>Failed Reason: {str(e)}</b></i></blockquote>', disable_web_page_preview=True)
                count += 1
                failed_count += 1
                continue

    except Exception as e:
        await m.reply_text(e)
        time.sleep(2)

    success_count = len(links) - failed_count
    video_count = v2_count + mpd_count + m3u8_count + yt_count + drm_count + zip_count + other_count
    if raw_text7 == "/d":
        await bot.send_message(
            channel_id,
            (
                "<b>📬 ᴘʀᴏᴄᴇꜱꜱ ᴄᴏᴍᴘʟᴇᴛᴇᴅ</b>\n\n"
                "<blockquote><b>📚 ʙᴀᴛᴄʜ ɴᴀᴍᴇ :</b> "
                f"{b_name}</blockquote>\n"
                "╭────────────────\n"
                f"├ 🖇️ ᴛᴏᴛᴀʟ ᴜʀʟꜱ : <code>{len(links)}</code>\n"
                f"├ ✅ ꜱᴜᴄᴄᴇꜱꜱꜰᴜʟ : <code>{success_count}</code>\n"
                f"├ ❌ ꜰᴀɪʟᴇᴅ : <code>{failed_count}</code>\n"
                "╰────────────────\n\n"
                "╭──────── 📦 ᴄᴀᴛᴇɢᴏʀʏ ────────\n"
                f"├ 🎞️ ᴠɪᴅᴇᴏꜱ : <code>{video_count}</code>\n"
                f"├ 📑 ᴘᴅꜰꜱ : <code>{pdf_count}</code>\n"
                f"├ 🖼️ ɪᴍᴀɢᴇꜱ : <code>{img_count}</code>\n"
                "╰────────────────────────────\n\n"
                "<i>ᴇxᴛʀᴀᴄᴛᴇᴅ ʙʏ ᴡɪᴢᴀʀᴅ ʙᴏᴛꜱ 🤖</i>"
            )
        )
    else:
        await bot.send_message(channel_id, f"<b>-┈━═.•°✅ Completed ✅°•.═━┈-</b>\n<blockquote><b>🎯Batch Name : {b_name}</b></blockquote>\n<blockquote>🔗 Total URLs: {len(links)} \n┃   ┠🔴 Total Failed URLs: {failed_count}\n┃   ┠🟢 Total Successful URLs: {success_count}\n┃   ┃   ┠🎥 Total Video URLs: {video_count}\n┃   ┃   ┠📄 Total PDF URLs: {pdf_count}\n┃   ┃   ┠📸 Total IMAGE URLs: {img_count}</blockquote>\n")
        await bot.send_message(m.chat.id, f"<blockquote><b>✅ Your Task is completed, please check your Set Channel📱</b></blockquote>")


@bot.on_message(filters.text & filters.private)
async def text_handler(bot: Client, m: Message):
    if m.from_user.is_bot:
        return
    links = m.text
    path = None
    match = re.search(r'https?://\S+', links)
    if match:
        link = match.group(0)
    else:
        await m.reply_text("<pre><code>Invalid link format.</code></pre>")
        return
        
    editable = await m.reply_text(f"<pre><code>**🔹Processing your link...\n🔁Please wait...⏳**</code></pre>")
    await m.delete()

    await editable.edit(f"╭━━━━❰ᴇɴᴛᴇʀ ʀᴇꜱᴏʟᴜᴛɪᴏɴ❱━━➣ \n┣━━⪼ send `144`\n┣━━⪼ send `240`\n┣━━⪼ send `360`\n┣━━⪼ send `480`\n┣━━⪼ send `720`\n┣━━⪼ send `1080`\n╰━━⌈⚡[`{CREDIT}`]⚡⌋━━➣ ")
    input2: Message = await bot.listen(editable.chat.id, filters=filters.text & filters.user(m.from_user.id))
    raw_text2 = input2.text
    quality = f"{raw_text2}p"
    await input2.delete(True)
    try:
        if raw_text2 == "144":
            res = "256x144"
        elif raw_text2 == "240":
            res = "426x240"
        elif raw_text2 == "360":
            res = "640x360"
        elif raw_text2 == "480":
            res = "854x480"
        elif raw_text2 == "720":
            res = "1280x720"
        elif raw_text2 == "1080":
            res = "1920x1080" 
        else: 
            res = "UN"
    except Exception:
        res = "UN"


# Callback Handlers
@bot.on_callback_query(filters.regex("features"))
async def features_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    features_text = (
        "**🔥 Bot Features 🔥**\n\n"
        "• 📥 Download DRM protected videos\n"
        "• 🎬 Support for multiple video formats\n"
        "• 📱 Works with YouTube and other platforms\n"
        "• 📑 PDF download support\n"
        "• 🖼️ Image download support\n"
        "• 🎵 Audio download support\n"
        "• 📝 Text to file conversion\n"
        "• ⚙️ Customizable quality settings\n"
        "• 🎨 Custom watermark support\n"
        "• 🔐 MPD DRM with KID:KEY support\n"
    )
    await callback_query.message.edit_text(
        features_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

@bot.on_callback_query(filters.regex("details"))
async def details_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    details_text = (
        "**📋 Bot Details 📋**\n\n"
        "• 🤖 Bot Name: DRM Wizard 🦋\n"
        "• 👨‍💻 Developer: IT'sGOLU.™®\n"
        "• 📱 Contact: @ITsGOLU_OWNER_BOT\n"
        "• 🔄 Version: 2.0\n"
        "• 📝 Language: Python\n"
        "• 🛠️ Framework: Pyrogram\n\n"
        "**🔐 Supported DRM Formats**\n\n"
        "• 🔒 ClassPlus DRM\n"
        "• 🔒 MPD with KID:KEY\n"
        "• 🔒 Widevine DRM\n"
        "• 🔒 APPX Encrypted\n"
    )
    await callback_query.message.edit_text(
        details_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_start")]
        ])
    )

@bot.on_callback_query(filters.regex("back_to_start"))
async def back_to_start_callback(client, callback_query: CallbackQuery):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    is_authorized = db.is_user_authorized(user_id, client.me.username)
    is_admin = db.is_admin(user_id)
    
    commands_list = (
        "**>  /drm - ꜱᴛᴀʀᴛ ᴜᴘʟᴏᴀᴅɪɴɢ ᴄᴘ/ᴄᴡ ᴄᴏᴜʀꜱᴇꜱ**\n"
        "**>  /plan - ᴠɪᴇᴡ ʏᴏᴜʀ ꜱᴜʙꜱᴄʀɪᴘᴛɪᴏɴ ᴅᴇᴛᴀɪʟꜱ**\n"
    )
    
    if is_admin:
        commands_list += (
            "\n**👑 Admin Commands**\n"
            "• /users - List all users\n"
        )
    
    await callback_query.message.edit_media(
        media=InputMediaPhoto(
            media=photologo,
            caption=f"**Mʏ ᴄᴏᴍᴍᴀɴᴅꜱ ғᴏʀ ʏᴏᴜ [{callback_query.from_user.first_name} ](tg://settings)**\n\n{commands_list}"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("𝐈𝐓'𝐬𝐆𝐎𝐋𝐔.™®", url="https://t.me/ITsGOLU_OWNER_BOT")],
            [
                InlineKeyboardButton("ғᴇᴀᴛᴜʀᴇꜱ 🪔", callback_data="features"),
                InlineKeyboardButton("ᴅᴇᴛᴀɪʟꜱ 🦋", callback_data="details")
            ]
        ])
    )

print("Bot Started...")
bot.run()
