import os
from pyrogram import Client, filters, enums
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from utils import extract_user, get_file_id, get_poster, last_online, fetch_movie_details
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

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import logging

logger = logging.getLogger(__name__)

# മെസ്സേജ് ടെക്സ്റ്റ് ടെംപ്ലേറ്റ്
IMDB_TEMPLATE = """
🎬 **Title:** {title} ({year})
⭐ **IMDb Rating:** {rating}/10 ({votes} votes)
⏳ **Runtime:** {runtime} min
🎭 **Genres:** {genres}
🌐 **Languages:** {languages}
🎥 **Director:** {director}
🌟 **Stars:** {cast}
🌍 **Country:** {countries}

📖 **Storyline:** {plot}
"""

@Client.on_message(filters.command(["imdb", 'search']))
async def imdb_search(client, message):
    if ' ' in message.text:
        k = await message.reply('🔍 Searching IMDb...')
        r, title = message.text.split(None, 1)
        
        movies = await fetch_movie_details(title, bulk=True)
        
        if not movies:
            return await message.reply("ക്ഷമിക്കണം, ഫലങ്ങൾ ഒന്നും കണ്ടെത്തിയില്ല! ❌")
        
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{getattr(movie, 'title')} - {getattr(movie, 'year', 'N/A')}",
                    callback_data=f"imdb#{getattr(movie, 'imdb_id')}",
                )
            ]
            for movie in movies if getattr(movie, 'imdb_id', None)
        ]
        
        if not btn:
            return await k.edit('No processable results found.')
            
        await k.edit('Here is what i found on IMDb 👇', reply_markup=InlineKeyboardMarkup(btn))
    else:
        await message.reply('Give me a movie / series Name\nExample: `/imdb Spiderman`')

@Client.on_callback_query(filters.regex('^imdb'))
async def imdb_callback(bot: Client, quer_y: CallbackQuery):
    i, movie_id = quer_y.data.split('#')
    
    imdb = await fetch_movie_details(query=movie_id, id=True)
    
    if not imdb:
        await quer_y.answer("ഡാറ്റ എടുക്കാൻ കഴിഞ്ഞില്ല! ❌", show_alert=True)
        return

    btn = [
        [
            InlineKeyboardButton(
                text=f"🎬 {imdb.get('title')} on IMDb",
                url=imdb['url'],
            )
        ]
    ]
    
    # ക്യാപ്ഷൻ ഫോർമാറ്റ് ചെയ്യുന്നു (ടെക്സ്റ്റ് ലിമിറ്റിനായി പ്ലോട്ട് 900 അക്ഷരങ്ങളാക്കി കൂട്ടാം)
    caption = IMDB_TEMPLATE.format(
        title=imdb.get('title'),
        year=imdb.get('year'),
        rating=imdb.get('rating'),
        votes=imdb.get('votes'),
        genres=imdb.get('genres'),
        languages=imdb.get('languages'),
        director=imdb.get('director'),
        cast=imdb.get('cast'),
        countries=imdb.get('countries'),
        plot=imdb.get('plot')[:900] 
    )

    # ⚡ പോസ്റ്റർ പൂർണ്ണമായി ഒഴിവാക്കി നേരിട്ട് നിലവിലുള്ള മെസ്സേജ് എഡിറ്റ് ചെയ്യുന്നു
    try:
        await quer_y.message.edit(
            text=caption, 
            reply_markup=InlineKeyboardMarkup(btn), 
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.exception(e)
        await quer_y.message.reply(
            text=caption, 
            reply_markup=InlineKeyboardMarkup(btn), 
            disable_web_page_preview=True
        )
        
    await quer_y.answer()
