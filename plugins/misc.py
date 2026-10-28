import os
from pyrogram import Client, filters, enums
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from utils import extract_user, get_file_id, get_poster, last_online, get_posters
import time
from datetime import datetime
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

@Client.on_message(filters.command('id'))
async def showid(client, message):
    chat_type = message.chat.type
    if chat_type == enums.ChatType.PRIVATE:
        user_id = message.chat.id
        first = message.from_user.first_name
        last = message.from_user.last_name or ""
        username = message.from_user.username
        dc_id = message.from_user.dc_id or ""
        await message.reply_text(
            f"<b>➲ First Name:</b> {first}\n<b>➲ Last Name:</b> {last}\n<b>➲ Username:</b> {username}\n<b>➲ Telegram ID:</b> <code>{user_id}</code>\n<b>➲ Data Centre:</b> <code>{dc_id}</code>",
            quote=True
        )

    elif chat_type in [enums.ChatType.GROUP , enums.ChatType.SUPERGROUP]:
        _id = ""
        _id += (
            "<b>➲ Chat ID</b>: "
            f"<code>{message.chat.id}</code>\n"
        )
        if message.reply_to_message:
            _id += (
                "<b>➲ User ID</b>: "
                f"<code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
                "<b>➲ Replied User ID</b>: "
                f"<code>{message.reply_to_message.from_user.id if message.reply_to_message.from_user else 'Anonymous'}</code>\n"
            )
            file_info = get_file_id(message.reply_to_message)
        else:
            _id += (
                "<b>➲ User ID</b>: "
                f"<code>{message.from_user.id if message.from_user else 'Anonymous'}</code>\n"
            )
            file_info = get_file_id(message)
        if file_info:
            _id += (
                f"<b>{file_info.message_type}</b>: "
                f"<code>{file_info.file_id}</code>\n"
            )
        await message.reply_text(
            _id,
            quote=True
        )

@Client.on_message(filters.command(["info"]))
async def who_is(client, message):
    # https://github.com/SpEcHiDe/PyroGramBot/blob/master/pyrobot/plugins/admemes/whois.py#L19
    status_message = await message.reply_text(
        "`Fetching user info...`"
    )
    await status_message.edit(
        "`Processing user info...`"
    )
    from_user = None
    from_user_id, _ = extract_user(message)
    try:
        from_user = await client.get_users(from_user_id)
    except Exception as error:
        await status_message.edit(str(error))
        return
    if from_user is None:
        return await status_message.edit("no valid user_id / message specified")
    message_out_str = ""
    message_out_str += f"<b>➲First Name:</b> {from_user.first_name}\n"
    last_name = from_user.last_name or "<b>None</b>"
    message_out_str += f"<b>➲Last Name:</b> {last_name}\n"
    message_out_str += f"<b>➲Telegram ID:</b> <code>{from_user.id}</code>\n"
    username = from_user.username or "<b>None</b>"
    dc_id = from_user.dc_id or "[User Doesn't Have A Valid DP]"
    message_out_str += f"<b>➲Data Centre:</b> <code>{dc_id}</code>\n"
    message_out_str += f"<b>➲User Name:</b> @{username}\n"
    message_out_str += f"<b>➲User 𝖫𝗂𝗇𝗄:</b> <a href='tg://user?id={from_user.id}'><b>Click Here</b></a>\n"
    if message.chat.type in ((enums.ChatType.SUPERGROUP, enums.ChatType.CHANNEL )):
        try:
            chat_member_p = await message.chat.get_member(from_user.id)
            joined_date = datetime.fromtimestamp(
                chat_member_p.joined_date or time.time()
            ).strftime("%Y.%m.%d %H:%M:%S")
            message_out_str += (
                "<b>➲Joined this Chat on:</b> <code>"
                f"{joined_date}"
                "</code>\n"
            )
        except UserNotParticipant:
            pass
    chat_photo = from_user.photo
    if chat_photo:
        local_user_photo = await client.download_media(
            message=chat_photo.big_file_id
        )
        buttons = [[
            InlineKeyboardButton('🔐 Close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_photo(
            photo=local_user_photo,
            quote=True,
            reply_markup=reply_markup,
            caption=message_out_str,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
        os.remove(local_user_photo)
    else:
        buttons = [[
            InlineKeyboardButton('🔐 Close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_text(
            text=message_out_str,
            reply_markup=reply_markup,
            quote=True,
            parse_mode=enums.ParseMode.HTML,
            disable_notification=True
        )
    await status_message.delete()


@Client.on_message(filters.command(["imdb", "search"]))
async def imdb_search(client, message):
    if len(message.command) < 2:
        return await message.reply("Give me a movie / series Name")

    k = await message.reply("Searching movie databases...")
    title = message.text.split(None, 1)[1].strip()

    try:
        movies = await get_poster(title, bulk=True)
        if not movies:
            await k.edit("No results found.")
            return

        btn = [
            [
                InlineKeyboardButton(
                    text=f"{movie.get('title', 'Unknown')} - {movie.get('year', 'N/A')}",
                    callback_data=f"imdb#{movie.get('movieID')}"
                )
            ]
            for movie in movies if movie.get("movieID")
        ]

        if not btn:
            await k.edit("No results found.")
            return

        await k.edit(
            "Here is what I found:",
            reply_markup=InlineKeyboardMarkup(btn)
        )
    except Exception as e:
        logger.exception("Movie search failed: %s", e)
        await k.edit("Search failed. Please try again.")


@Client.on_callback_query(filters.regex(r"^imdb#"))
async def imdb_callback(bot: Client, quer_y: CallbackQuery):
    try:
        _, movie_id = quer_y.data.split("#", 1)
        imdb = await get_posters(query=movie_id, id=True)

        if not imdb:
            await quer_y.answer("No results found.", show_alert=True)
            return

        btn = []
        movie_url = imdb.get("url")
        if movie_url and movie_url != "N/A":
            btn.append([
                InlineKeyboardButton(
                    text=imdb.get("title", "Movie details"),
                    url=movie_url
                )
            ])

        caption = IMDB_TEMPLATE.format(
            query=imdb.get("title", "N/A"),
            title=imdb.get("title", "N/A"),
            votes=imdb.get("votes", "N/A"),
            aka=imdb.get("aka", "N/A"),
            seasons=imdb.get("seasons", "N/A"),
            box_office=imdb.get("box_office", "N/A"),
            localized_title=imdb.get("localized_title", "N/A"),
            kind=imdb.get("kind", "N/A"),
            imdb_id=imdb.get("imdb_id", "N/A"),
            cast=imdb.get("cast", "N/A"),
            runtime=imdb.get("runtime", "N/A"),
            countries=imdb.get("countries", "N/A"),
            certificates=imdb.get("certificates", "N/A"),
            languages=imdb.get("languages", "N/A"),
            director=imdb.get("director", "N/A"),
            writer=imdb.get("writer", "N/A"),
            producer=imdb.get("producer", "N/A"),
            composer=imdb.get("composer", "N/A"),
            cinematographer=imdb.get("cinematographer", "N/A"),
            music_team=imdb.get("music_team", "N/A"),
            distributors=imdb.get("distributors", "N/A"),
            release_date=imdb.get("release_date", "N/A"),
            year=imdb.get("year", "N/A"),
            genres=imdb.get("genres", "N/A"),
            poster=imdb.get("poster") or "N/A",
            plot=imdb.get("plot", "N/A"),
            rating=imdb.get("rating", "N/A"),
            url=imdb.get("url", "N/A")
        )

        markup = InlineKeyboardMarkup(btn) if btn else None
        poster_url = imdb.get("poster")

        if poster_url:
            try:
                await quer_y.message.reply_photo(
                    photo=poster_url,
                    caption=caption[:1024],
                    reply_markup=markup
                )
            except Exception as e:
                logger.warning("Poster sending failed: %s", e)
                await quer_y.message.reply_text(
                    caption,
                    reply_markup=markup,
                    disable_web_page_preview=False
                )
            try:
                await quer_y.message.delete()
            except Exception:
                pass
        else:
            await quer_y.message.edit_text(
                caption,
                reply_markup=markup,
                disable_web_page_preview=False
            )

        await quer_y.answer()

    except Exception as e:
        logger.exception("Movie callback failed: %s", e)
        await quer_y.answer("Unable to fetch movie details.", show_alert=True)
