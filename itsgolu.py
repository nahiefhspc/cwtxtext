import os
import glob
import re
import time
import mmap
import datetime
import aiohttp
import aiofiles
import asyncio
import logging
import requests
import xml.etree.ElementTree as ET
import tgcrypto
import subprocess
import shutil
import concurrent.futures
import psutil
from math import ceil
from utils import progress_bar
from pyrogram import Client, filters
from pyrogram.types import Message
from io import BytesIO
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from base64 import b64decode
import math
import m3u8
from urllib.parse import urljoin
from vars import *
from db import Database

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ LOGGING SETUP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ GLOBAL DOWNLOAD LOCKS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
active_downloads = {}
download_lock = asyncio.Lock()
download_processes = {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ DURATION FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ FIXED: get_duration
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_duration(filename):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",           # ✅ warnings suppress karo
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filename
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE       # ✅ stderr alag rakho
        )

        # ✅ stdout se sirf duration lo
        raw_output = result.stdout.decode('utf-8', errors='replace').strip()

        # ✅ Multiple lines mein se float dhundo
        duration_value = None
        for line in raw_output.split('\n'):
            line = line.strip()
            try:
                duration_value = float(line)
                break  # Pehla valid float mil gaya
            except ValueError:
                continue  # Warning lines skip karo

        if duration_value is None:
            # ✅ Fallback: ffprobe se format duration try karo
            result2 = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    filename
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            import json
            try:
                info = json.loads(result2.stdout.decode())
                duration_value = float(info['format']['duration'])
            except Exception:
                duration_value = 0.0

        print(f"⏱️ Duration: {duration_value:.2f}s")
        return duration_value

    except Exception as e:
        logging.error(f"get_duration error: {e}")
        return 0.0


def duration(filename):
    return get_duration(filename)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ SPLIT LARGE VIDEO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def split_large_video(file_path, max_size_mb=1900):
    try:
        size_bytes = os.path.getsize(file_path)
        max_bytes = max_size_mb * 1024 * 1024

        if size_bytes <= max_bytes:
            return [file_path]

        dur = get_duration(file_path)
        parts = ceil(size_bytes / max_bytes)
        part_duration = dur / parts
        base_name = file_path.rsplit(".", 1)[0]
        output_files = []

        for i in range(parts):
            output_file = f"{base_name}_part{i + 1}.mp4"
            cmd = [
                "ffmpeg", "-y",
                "-i", file_path,
                "-ss", str(int(part_duration * i)),
                "-t", str(int(part_duration)),
                "-c", "copy",
                output_file
            ]
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            if os.path.exists(output_file):
                output_files.append(output_file)
                print(f"✅ Part {i + 1} created: {output_file}")

        return output_files if output_files else [file_path]

    except Exception as e:
        logging.error(f"split_large_video error: {e}")
        return [file_path]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ HELPER FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_mps_and_keys(api_url):
    try:
        response = requests.get(api_url, timeout=30)
        response_json = response.json()
        mpd = response_json.get('mpd_url')
        keys = response_json.get('keys')
        return mpd, keys
    except Exception as e:
        logging.error(f"get_mps_and_keys error: {e}")
        return None, None


def exec(cmd):
    try:
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        output = process.stdout.decode()
        print(output)
        return output
    except Exception as e:
        logging.error(f"exec error: {e}")
        return ""


def pull_run(work, cmds):
    with concurrent.futures.ThreadPoolExecutor(max_workers=work) as executor:
        print("Waiting for tasks to complete")
        executor.map(exec, cmds)


async def aio(url, name):
    try:
        k = f'{name}.pdf'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    async with aiofiles.open(k, mode='wb') as f:
                        await f.write(await resp.read())
        return k
    except Exception as e:
        logging.error(f"aio error: {e}")
        return None


async def download(url, name):
    try:
        ka = f'{name}.pdf'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    async with aiofiles.open(ka, mode='wb') as f:
                        await f.write(await resp.read())
        return ka
    except Exception as e:
        logging.error(f"download error: {e}")
        return None


async def pdf_download(url, file_name, chunk_size=1024 * 10):
    try:
        if os.path.exists(file_name):
            os.remove(file_name)
        r = requests.get(url, allow_redirects=True, stream=True, timeout=60)
        with open(file_name, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    fd.write(chunk)
        return file_name
    except Exception as e:
        logging.error(f"pdf_download error: {e}")
        return None


def parse_vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = []
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ", 2)
            try:
                if (
                    "RESOLUTION" not in i[2]
                    and i[2] not in temp
                    and "audio" not in i[2]
                ):
                    temp.append(i[2])
                    new_info.append((i[0], i[2]))
            except:
                pass
    return new_info


def vid_info(info):
    info = info.strip()
    info = info.split("\n")
    new_info = dict()
    temp = []
    for i in info:
        i = str(i)
        if "[" not in i and '---' not in i:
            while "  " in i:
                i = i.replace("  ", " ")
            i.strip()
            i = i.split("|")[0].split(" ", 3)
            try:
                if (
                    "RESOLUTION" not in i[2]
                    and i[2] not in temp
                    and "audio" not in i[2]
                ):
                    temp.append(i[2])
                    new_info.update({f'{i[2]}': f'{i[0]}'})
            except:
                pass
    return new_info


def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if size < 1024.0 or unit == 'PB':
            break
        size /= 1024.0
    return f"{size:.{decimal_places}f} {unit}"


def time_name():
    date = datetime.date.today()
    now = datetime.datetime.now()
    current_time = now.strftime("%H%M%S")
    return f"{date} {current_time}.mp4"


async def run(cmd):
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        print(f'[{cmd!r} exited with {proc.returncode}]')
        if proc.returncode == 1:
            return False
        if stdout:
            return f'[stdout]\n{stdout.decode()}'
        if stderr:
            return f'[stderr]\n{stderr.decode()}'
    except Exception as e:
        logging.error(f"run error: {e}")
        return False


def old_download(url, file_name, chunk_size=1024 * 10 * 10):
    try:
        if os.path.exists(file_name):
            os.remove(file_name)
        r = requests.get(url, allow_redirects=True, stream=True, timeout=60)
        with open(file_name, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    fd.write(chunk)
        return file_name
    except Exception as e:
        logging.error(f"old_download error: {e}")
        return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ BUILD DOWNLOAD COMMAND (FIXED)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_download_command(
    url: str,
    output_name: str,
    use_aria2c: bool = True
) -> str:
    """
    FIXES:
    1. ✅ aria2c:-x (no space after colon)
    2. ✅ --hls-use-mpegts
    3. ✅ --concurrent-fragments 16
    4. ✅ --newline for clean output
    5. ✅ HEADERS ADDED
    """

    base_cmd = (
        f'yt-dlp '
        f'-f "b[height<=720]/bv[height<=720]+ba/b/bv+ba" '
        f'--hls-use-mpegts '
        f'--concurrent-fragments 16 '
        f'--retries 25 '
        f'--fragment-retries 25 '
        f'--no-warnings '
        f'--newline '
        # 👇 HEADERS ADDED HERE
        f'--add-header "User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36" '
        f'--add-header "Referer: https://rarestudy.in/" '
    )

    # ✅ Cookies
    if os.path.exists('cookies.txt'):
        base_cmd += '--cookies cookies.txt '

    # ✅ aria2c (FIX: no space after "aria2c:")
    if use_aria2c:
        base_cmd += (
            f'--external-downloader aria2c '
            f'--downloader-args "aria2c:-x 16 -j 16 -k 1M --no-conf --retry-wait=3 --max-tries=0" '
        )

    base_cmd += f'-o "{output_name}" "{url}"'
    return base_cmd

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ DECRYPT AND MERGE VIDEO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def decrypt_and_merge_video(
    mpd_url,
    keys_string,
    output_path,
    output_name,
    quality="720"
):
    try:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ✅ STEP 1: Download MPD & Inject CloudFront Query Params
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
            'Referer': 'https://rarestudy.in/'
        }
        
        print(f"🌐 Downloading and patching MPD manifest...")
        resp = requests.get(mpd_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            raise Exception(f"Failed to fetch MPD: HTTP {resp.status_code}")
            
        mpd_text = resp.text
        parsed_mpd = urlparse(mpd_url)
        query_string = f"?{parsed_mpd.query}" if parsed_mpd.query else ""
        
        # Parse XML and append query string to all segment URLs
        root = ET.fromstring(mpd_text)
        ns = root.tag.split('}')[0] + '}' if '}' in root.tag else ''
        
        for base in root.findall(f'.//{ns}BaseURL'):
            if base.text and '?' not in base.text:
                base.text += query_string
                
        for st in root.findall(f'.//{ns}SegmentTemplate'):
            if st.get('media') and '?' not in st.get('media'):
                st.set('media', st.get('media') + query_string)
            if st.get('initialization') and '?' not in st.get('initialization'):
                st.set('initialization', st.get('initialization') + query_string)
                
        for su in root.findall(f'.//{ns}SegmentURL'):
            if su.get('media') and '?' not in su.get('media'):
                su.set('media', su.get('media') + query_string

        # Save the patched manifest locally
        local_mpd = os.path.join(output_path, "manifest.mpd")
        with open(local_mpd, "w", encoding="utf-8") as f:
            f.write(ET.tostring(root, encoding='unicode'))
            
        print("✅ MPD patched successfully!")

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # ✅ STEP 2: Download using patched local MPD
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        cmd1 = (
            f'yt-dlp -f "bv[height<={quality}]+ba/b" '
            f'-o "{output_path}/file.%(ext)s" '
            f'--allow-unplayable-format '
            f'--no-check-certificate '
            f'--add-header "User-Agent: Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36" '
            f'--add-header "Referer: https://rarestudy.in/" '
            f'-N 16 '
            f'--retries 10 '
            f'--fragment-retries 10 '
            f'--no-warnings '
            f'"{local_mpd}"'  # 👈 Passing local file instead of URL
        )
        print(f"🔽 Downloading MPD: {cmd1}")
        subprocess.run(cmd1, shell=True)

        avDir = list(output_path.iterdir())
        print(f"📁 Downloaded files: {avDir}")
        print("🔐 Decrypting...")

        video_decrypted = False
        audio_decrypted = False

        for data in avDir:
            if data.name == "manifest.mpd": # Skip the manifest file
                continue
                
            if not video_decrypted and data.suffix in [".mp4", ".m4v", ".webm"]:
                cmd2 = (
                    f'mp4decrypt {keys_string} --show-progress '
                    f'"{data}" "{output_path}/video.mp4"'
                )
                print(f"🔓 Video: {cmd2}")
                os.system(cmd2)
                if (output_path / "video.mp4").exists():
                    video_decrypted = True
                    print("✅ Video decrypted")
                data.unlink()

            elif not audio_decrypted and data.suffix in [".m4a", ".mp4a", ".ogg"]:
                cmd3 = (
                    f'mp4decrypt {keys_string} --show-progress '
                    f'"{data}" "{output_path}/audio.m4a"'
                )
                print(f"🔓 Audio: {cmd3}")
                os.system(cmd3)
                if (output_path / "audio.m4a").exists():
                    audio_decrypted = True
                    print("✅ Audio decrypted")
                data.unlink()

        if not video_decrypted:
            remaining = list(output_path.iterdir())
            for data in remaining:
                if data.name == "manifest.mpd": continue
                if data.suffix in [".mp4", ".mkv", ".webm", ".m4v"]:
                    cmd_single = (
                        f'mp4decrypt {keys_string} --show-progress '
                        f'"{data}" "{output_path}/video.mp4"'
                    )
                    os.system(cmd_single)
                    if (output_path / "video.mp4").exists():
                        video_decrypted = True
                    data.unlink()
                    break

        if not video_decrypted:
            raise FileNotFoundError("❌ Decryption failed: No video file found.")

        if video_decrypted and audio_decrypted:
            cmd4 = (
                f'ffmpeg -i "{output_path}/video.mp4" '
                f'-i "{output_path}/audio.m4a" '
                f'-c copy -movflags +faststart '
                f'"{output_path}/{output_name}.mp4"'
            )
            print(f"🔄 Merging: {cmd4}")
            os.system(cmd4)

            for f in ["video.mp4", "audio.m4a", "manifest.mpd"]:
                fp = output_path / f
                if fp.exists():
                    fp.unlink()

        elif video_decrypted:
            print("⚠️ No audio - using video only")
            shutil.move(
                str(output_path / "video.mp4"),
                str(output_path / f"{output_name}.mp4")
            )
            # Cleanup manifest
            if (output_path / "manifest.mpd").exists():
                (output_path / "manifest.mpd").unlink()

        filename = output_path / f"{output_name}.mp4"

        if not filename.exists():
            raise FileNotFoundError("❌ Merged file not found.")

        file_size = os.path.getsize(str(filename)) / (1024 * 1024)
        print(f"✅ Final: {filename} ({file_size:.1f} MB)")
        return str(filename)

    except Exception as e:
        print(f"❌ decrypt_and_merge error: {e}")
        raise

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ FAST DOWNLOAD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def fast_download(url, name):
    max_retries = 5
    retry_count = 0

    while retry_count < max_retries:
        try:
            if "m3u8" in url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        m3u8_text = await response.text()

                playlist = m3u8.loads(m3u8_text)

                if playlist.is_endlist:
                    base_url = url.rsplit('/', 1)[0] + '/'
                    segments = []

                    async with aiohttp.ClientSession() as session:
                        tasks = [
                            asyncio.create_task(
                                session.get(urljoin(base_url, seg.uri))
                            )
                            for seg in playlist.segments
                        ]
                        responses = await asyncio.gather(*tasks)
                        for resp in responses:
                            data = await resp.read()
                            segments.append(data)

                    output_file = f"{name}.mp4"
                    with open(output_file, 'wb') as f:
                        for seg in segments:
                            f.write(seg)
                    return [output_file]

                else:
                    cmd = (
                        f'ffmpeg -hide_banner -loglevel error -stats '
                        f'-i "{url}" -c copy -bsf:a aac_adtstoasc '
                        f'-movflags +faststart "{name}.mp4"'
                    )
                    subprocess.run(cmd, shell=True)
                    if os.path.exists(f"{name}.mp4"):
                        return [f"{name}.mp4"]

            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            output_file = f"{name}.mp4"
                            with open(output_file, 'wb') as f:
                                while True:
                                    chunk = await response.content.read(1024 * 1024)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                            return [output_file]

        except Exception as e:
            print(f"❌ fast_download attempt {retry_count + 1}: {e}")

        retry_count += 1
        await asyncio.sleep(3)

    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ MAIN DOWNLOAD VIDEO FUNCTION (FULLY FIXED)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def download_video(url, cmd, name):
    """
    FIXES:
    1. ✅ limit=1024*1024*10 (10MB buffer) - MAIN FIX
    2. ✅ aria2c space bug fixed
    3. ✅ --hls-use-mpegts added
    4. ✅ Fallback: aria2c → native
    5. ✅ Error detection & recovery
    6. ✅ Process timeout handling
    7. ✅ File size verification
    """

    download_key = os.path.basename(name)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # LOCK CHECK
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    async with download_lock:
        if download_key in active_downloads:
            print(f"⚠️ Already downloading: {download_key}")
            wait_time = 0
            while download_key in active_downloads and wait_time < 1800:
                await asyncio.sleep(10)
                wait_time += 10
            if os.path.exists(name):
                return name

        lock_file = f"{name}.lock"
        if os.path.exists(lock_file):
            try:
                with open(lock_file, 'r') as f:
                    old_pid = int(f.read().strip())
                if psutil.pid_exists(old_pid):
                    await asyncio.sleep(5)
                    return name
                else:
                    os.remove(lock_file)
            except:
                try:
                    os.remove(lock_file)
                except:
                    pass

        active_downloads[download_key] = True
        try:
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            print(f"🔒 Locked: {download_key}")
        except:
            pass

    try:
        max_retries = 2
        retry_count = 0
        download_success = False
        result_file = name

        while retry_count < max_retries and not download_success:

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # CLEANUP PARTIAL FILES
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            base_name = name.split(".")[0]
            for f in (
                glob.glob(f"{base_name}*part*") +
                glob.glob(f"{base_name}*.ytdl") +
                glob.glob(f"{base_name}*.part")
            ):
                try:
                    os.remove(f)
                    print(f"🗑️ Cleaned: {f}")
                except:
                    pass

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # BUILD COMMAND
            # Attempt 1 → aria2c
            # Attempt 2 → native (no aria2c)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            use_aria2c = (retry_count == 0)
            download_cmd = build_download_command(url, name, use_aria2c=use_aria2c)

            print(f"\n{'='*50}")
            print(f"🚀 Download attempt {retry_count + 1}/{max_retries}")
            if not use_aria2c:
                print(f"⚠️ Fallback: Native downloader (no aria2c)")
            print(f"📝 Command: {download_cmd}")
            print(f"{'='*50}")

            logging.info(f"Download CMD: {download_cmd}")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # ✅ MAIN FIX: limit=10MB
            # (was 64KB → caused the error)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            process = await asyncio.create_subprocess_shell(
                download_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                limit=1024 * 1024 * 10  # ✅ 10MB (FIXED from 64KB)
            )

            download_processes[download_key] = process.pid
            print(f"📍 PID: {process.pid}")

            line_count = 0
            error_detected = False
            last_progress = time.time()

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # READ OUTPUT SAFELY
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            try:
                while True:
                    try:
                        line = await asyncio.wait_for(
                            process.stdout.readline(),
                            timeout=180  # 3 min no output = timeout
                        )
                    except asyncio.TimeoutError:
                        print("⚠️ 3min no output - killing process")
                        try:
                            process.kill()
                        except:
                            pass
                        break
                    except Exception as read_err:
                        print(f"⚠️ Read warning (non-fatal): {read_err}")
                        await asyncio.sleep(1)
                        continue

                    if not line:
                        break

                    try:
                        decoded = line.decode('utf-8', errors='replace').strip()
                    except Exception:
                        continue

                    if not decoded:
                        continue

                    line_count += 1
                    last_progress = time.time()

                    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
                    # ERROR DETECTION
                    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
                    fatal_errors = [
                        'HTTP Error 403',
                        'HTTP Error 404',
                        'Unable to download',
                        'giving up after',
                        'Sign in to confirm',
                        'This video is not available',
                    ]
                    for err in fatal_errors:
                        if err.lower() in decoded.lower():
                            print(f"❌ Fatal Error: {decoded}")
                            error_detected = True
                            break

                    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
                    # PROGRESS DISPLAY
                    # ━━━━━━━━━━━━━━━━━━━━━━━━━━
                    show_keywords = [
                        '[download]', '[info]', '%',
                        'ETA', 'Destination', 'Merging',
                        'error', 'Error', 'WARNING',
                        'Downloading', 'complete'
                    ]
                    if (
                        line_count % 5 == 0 or
                        any(x in decoded for x in show_keywords)
                    ):
                        print(f"📥 {decoded}")

            except Exception as e:
                print(f"⚠️ Output reading stopped: {e}")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # WAIT FOR PROCESS
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            try:
                await asyncio.wait_for(process.wait(), timeout=30)
            except asyncio.TimeoutError:
                print("⚠️ Process wait timeout - force killing")
                try:
                    process.kill()
                    await process.wait()
                except:
                    pass

            returncode = process.returncode
            print(f"\n📊 Exit code: {returncode}")

            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # FILE VERIFICATION
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            found_file = None
            check_names = [
                name,
                f"{base_name}.mp4",
                f"{base_name}.mkv",
                f"{base_name}.webm",
                f"{base_name}.mp4.webm",
            ]

            for check in check_names:
                if (
                    os.path.isfile(check) and
                    os.path.getsize(check) > 1024 * 100  # min 100KB
                ):
                    found_file = check
                    break

            # Success check
            if found_file and returncode == 0 and not error_detected:
                size_mb = os.path.getsize(found_file) / (1024 * 1024)
                print(f"✅ Download complete: {found_file} ({size_mb:.1f} MB)")
                download_success = True
                result_file = found_file
                break

            elif found_file and not error_detected:
                size_mb = os.path.getsize(found_file) / (1024 * 1024)
                if size_mb > 10:  # 10MB+ = probably complete
                    print(f"⚠️ Non-zero exit but file OK ({size_mb:.1f} MB) - accepting")
                    download_success = True
                    result_file = found_file
                    break
                else:
                    print(f"⚠️ File too small ({size_mb:.1f} MB) - retrying")

            else:
                print(f"❌ Attempt {retry_count + 1} failed")

            retry_count += 1
            if retry_count < max_retries:
                print(f"🔄 Retrying in 5s... (next: {'native' if retry_count == 1 else 'done'})")
                await asyncio.sleep(5)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # FINAL FILE RETURN
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        base_name = name.split(".")[0]
        final_checks = [
            result_file,
            name,
            f"{base_name}.mp4",
            f"{base_name}.mkv",
            f"{base_name}.webm",
        ]

        for check in final_checks:
            if (
                os.path.isfile(check) and
                os.path.getsize(check) > 1024 * 100
            ):
                size_mb = os.path.getsize(check) / (1024 * 1024)
                print(f"✅ Returning: {check} ({size_mb:.1f} MB)")
                return check

        print(f"❌ Download FAILED: {download_key}")
        return name

    finally:
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # CLEANUP LOCKS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        async with download_lock:
            active_downloads.pop(download_key, None)
            download_processes.pop(download_key, None)

        lock_file = f"{name}.lock"
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except:
                pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✅ SEND VIDEO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
async def send_vid(
    bot: Client,
    m: Message,
    cc,
    filename,
    thumb,
    name,
    prog,
    channel_id,
    watermark="𝐈𝐓'𝐬𝐆𝐎𝐋𝐔",
    topic_thread_id: int = None
):
    try:
        temp_thumb = None
        thumbnail = thumb

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # THUMBNAIL GENERATION
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if thumb in ["/d", "no"] or not os.path.exists(str(thumb)):
            os.makedirs("downloads", exist_ok=True)
            temp_thumb = f"downloads/thumb_{os.path.basename(filename)}.jpg"

            subprocess.run(
                f'ffmpeg -i "{filename}" -ss 00:00:10 '
                f'-vframes 1 -q:v 2 -y "{temp_thumb}"',
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            if (
                os.path.exists(temp_thumb) and
                watermark and
                watermark.strip() not in ["/d", ""]
            ):
                text_to_draw = watermark.strip()
                try:
                    probe_out = subprocess.check_output(
                        f'ffprobe -v error -select_streams v:0 '
                        f'-show_entries stream=width '
                        f'-of csv=p=0:s=x "{temp_thumb}"',
                        shell=True,
                        stderr=subprocess.DEVNULL
                    ).decode().strip()
                    img_width = (
                        int(probe_out.split('x')[0])
                        if 'x' in probe_out
                        else int(probe_out)
                    )
                except Exception:
                    img_width = 1280

                base_size = max(28, int(img_width * 0.075))
                text_len = len(text_to_draw)

                if text_len <= 3:
                    font_size = int(base_size * 1.25)
                elif text_len <= 8:
                    font_size = int(base_size * 1.0)
                elif text_len <= 15:
                    font_size = int(base_size * 0.85)
                else:
                    font_size = int(base_size * 0.7)

                font_size = max(32, min(font_size, 120))
                box_h = max(60, int(font_size * 1.6))
                safe_text = text_to_draw.replace("'", "\\'")

                text_cmd = (
                    f'ffmpeg -i "{temp_thumb}" -vf '
                    f'"drawbox=y=0:color=black@0.35:width=iw:'
                    f'height={box_h}:t=fill,'
                    f'drawtext=fontfile=font.ttf:'
                    f'text=\'{safe_text}\':fontcolor=white:'
                    f'fontsize={font_size}:'
                    f'x=(w-text_w)/2:y=(({box_h})-text_h)/2" '
                    f'-c:v mjpeg -q:v 2 -y "{temp_thumb}"'
                )
                subprocess.run(
                    text_cmd,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            thumbnail = (
                temp_thumb
                if os.path.exists(str(temp_thumb))
                else None
            )

        await prog.delete(True)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STATUS MESSAGES
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        reply1 = await bot.send_message(
            channel_id,
            f"**Uploading Video:**\n<blockquote>{name}</blockquote>"
        )
        reply = await m.reply_text(
            f"🖼 **Generating Thumbnail:**\n<blockquote>{name}</blockquote>"
        )

        file_size_mb = os.path.getsize(filename) / (1024 * 1024)
        sent_message = None

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # UPLOAD NORMAL (<2GB)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if file_size_mb < 2000:
            dur = int(duration(filename))
            start_time = time.time()

            try:
                sent_message = await bot.send_video(
                    chat_id=channel_id,
                    video=filename,
                    caption=cc,
                    supports_streaming=True,
                    height=720,
                    width=1280,
                    thumb=thumbnail,
                    duration=dur,
                    progress=progress_bar,
                    progress_args=(reply, start_time)
                )
            except Exception as e:
                print(f"⚠️ send_video failed → send_document: {e}")
                sent_message = await bot.send_document(
                    chat_id=channel_id,
                    document=filename,
                    caption=cc,
                    progress=progress_bar,
                    progress_args=(reply, start_time)
                )

            if os.path.exists(filename):
                os.remove(filename)

            await reply.delete(True)
            await reply1.delete(True)

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # UPLOAD LARGE (>2GB = SPLIT)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        else:
            notify_split = await m.reply_text(
                f"⚠️ File size: {human_readable_size(os.path.getsize(filename))}\n"
                f"⏳ Splitting into parts..."
            )

            parts = split_large_video(filename)
            first_part_message = None

            for idx, part in enumerate(parts):
                part_dur = int(duration(part))
                part_num = idx + 1
                total_parts = len(parts)
                part_caption = f"{cc}\n\n📦 Part {part_num} of {total_parts}"
                part_filename = f"{name}_Part{part_num}.mp4"

                upload_msg = await m.reply_text(
                    f"📤 Uploading Part {part_num}/{total_parts}..."
                )

                try:
                    msg_obj = await bot.send_video(
                        chat_id=channel_id,
                        video=part,
                        caption=part_caption,
                        file_name=part_filename,
                        supports_streaming=True,
                        height=720,
                        width=1280,
                        thumb=thumbnail,
                        duration=part_dur,
                        progress=progress_bar,
                        progress_args=(upload_msg, time.time())
                    )
                except Exception as e:
                    print(f"⚠️ Part {part_num} send_video failed → document: {e}")
                    msg_obj = await bot.send_document(
                        chat_id=channel_id,
                        document=part,
                        caption=part_caption,
                        file_name=part_filename,
                        progress=progress_bar,
                        progress_args=(upload_msg, time.time())
                    )

                if first_part_message is None:
                    first_part_message = msg_obj

                await upload_msg.delete(True)
                if os.path.exists(part):
                    os.remove(part)

            if len(parts) > 1:
                await m.reply_text(
                    f"✅ Video uploaded in {len(parts)} parts!"
                )

            await reply.delete(True)
            await reply1.delete(True)

            if notify_split:
                await notify_split.delete(True)

            if os.path.exists(filename):
                os.remove(filename)

            sent_message = first_part_message

        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # THUMBNAIL CLEANUP
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        if (
            thumb in ["/d", "no"] and
            temp_thumb and
            os.path.exists(str(temp_thumb))
        ):
            os.remove(temp_thumb)

        return sent_message

    except Exception as err:
        raise Exception(f"send_vid failed: {err}")
