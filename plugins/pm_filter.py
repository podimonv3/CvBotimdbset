# Kanged From @TroJanZheX
import ast
import asyncio
import logging
import re
from datetime import datetime, timedelta
from os import environ
from urllib.parse import quote_plus
import pyrogram  # For eval(btn)
from pyrogram import Client, enums, filters
from pyrogram.errors import (FloodWait, MessageNotModified, PeerIdInvalid,
                             UserIsBlocked)
from pyrogram.errors.exceptions.bad_request_400 import (MediaEmpty,
                                                        PhotoInvalidDimensions,
                                                        WebpageMediaEmpty)
from pyrogram.types import (CallbackQuery, InlineKeyboardButton,
                            InlineKeyboardMarkup)

from database.connections_mdb import (active_connection, all_connections,
                                      delete_connection, if_active,
                                      make_active, make_inactive)
from database.filters_mdb import del_all, find_filter, get_filters
from database.ia_filterdb import Media, get_file_details, get_search_results
from database.users_chats_db import db
from info import ADMINS, AUTH_CHANNEL, CUSTOM_FILE_CAPTION, REQ_CHANNEL, LOG_CHANNEL
from Script import script
from utils import (get_poster, get_posters, get_settings, get_size, is_subscribed,
                   save_group_settings, scheduler, search_gagala, temp)

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BUTTONS = {}

DELETE_TIME = int(environ.get("DELETE_TIME", 600))
import httpx


@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    k = await manual_filters(client, message)
    if k == False:
        await auto_filter(client, message)



@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    # 1. ബട്ടൺ ക്ലിക്ക് ചെയ്ത ഉടൻ തന്നെ ഇവിടെ ആൻസർ നൽകുന്നു
    try:
        await query.answer()
    except Exception:
        pass

    ident, req, key, offset = query.data.split("_")
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer("oKda", show_alert=True)
        
    try:
        offset = int(offset)
    except:
        offset = 0
    search = BUTTONS.get(key)
    if not search:
        await query.answer(
            "You are using one of my old messages, please send the request again.",
            show_alert=True,
        )
        return

    files, n_offset, total = await get_search_results(
        search, offset=offset, filter=True
    )
    try:
        n_offset = int(n_offset)
    except:
        n_offset = 0

    if not files:
        return
    settings = await get_settings(query.message.chat.id)
    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file.file_size)}] {file.file_name}",
                    callback_data=f"files#{file.file_id}",
                ),
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{file.file_name}", callback_data=f"files#{file.file_id}"
                ),
                InlineKeyboardButton(
                    text=f"{get_size(file.file_size)}",
                    callback_data=f"files_#{file.file_id}",
                ),
            ]
            for file in files
        ]

    if 0 < offset <= 10:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - 10
        
    if n_offset == 0:
        btn.append(
            [
                InlineKeyboardButton(
                    "⏪ BACK", callback_data=f"next_{req}_{key}_{off_set}"
                ),
                InlineKeyboardButton(
                    f"📃 Pages {round(int(offset) / 10) + 1} / {round(total / 10)}",
                    callback_data="pages",
                ),
            ]
        )
    elif off_set is None:
        btn.append(
            [
                InlineKeyboardButton(
                    f"🗓 {round(int(offset) / 10) + 1} / {round(total / 10)}",
                    callback_data="pages",
                ),
                InlineKeyboardButton(
                    "NEXT ⏩", callback_data=f"next_{req}_{key}_{n_offset}"
                ),
            ]
        )
    else:
        btn.append(
            [
                InlineKeyboardButton(
                    "⏪ BACK", callback_data=f"next_{req}_{key}_{off_set}"
                ),
                InlineKeyboardButton(
                    f"🗓 {round(int(offset) / 10) + 1} / {round(total / 10)}",
                    callback_data="pages",
                ),
                InlineKeyboardButton(
                    "NEXT ⏩", callback_data=f"next_{req}_{key}_{n_offset}"
                ),
            ],
        )
        
    # 2. മെസ്സേജ് എഡിറ്റ് ചെയ്യുമ്പോൾ ഫ്ലഡ് വെയ്റ്റ് വരാതിരിക്കാൻ സുരക്ഷിതമായ ട്രൈ-എക്സെപ്റ്റ് ബ്ലോക്ക്
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
    except MessageNotModified:
        pass
    except FloodWait as e:
        await asyncio.sleep(e.value) # FloodWait സെക്കൻഡുകൾ ബോട്ട് സ്വയം കാത്തുനിൽക്കും
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        except Exception:
            pass
    except Exception:
        pass




import re  # ഫയലിന്റെ മുകളിൽ ഉണ്ടെന്ന് ഉറപ്പാക്കുക

@Client.on_callback_query(filters.regex(r"^spolling"))
async def advantage_spoll_choker(bot, query):
    _, user, movie_ = query.data.split('#')
    
    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer("ഇത് നിങ്ങളുടെ സെർച്ച് റിസൾട്ട് അല്ല! ⚠️", show_alert=True)
        
    if movie_ == "close_spellcheck":
        return await query.message.delete()
        
    movies = SPELL_CHECK.get(query.message.reply_to_message.id)
    if not movies:
        return await query.answer("നിങ്ങൾ പഴയൊരു ബട്ടണിലാണ് ക്ലിക്ക് ചെയ്തത്. ഇത് കാലഹരണപ്പെട്ടു! ❌", show_alert=True)
        
    try:
        movie = movies[int(movie_)]
    except (IndexError, ValueError):
        return await query.answer("എന്തോ തകരാർ സംഭവിച്ചു. വീണ്ടും ശ്രമിക്കുക! ❌", show_alert=True)
        
    try:
        await query.message.delete()
    except Exception:
        pass

    await query.answer('Checking for Movie in database...')

    # 🛠️ സിനിമയുടെ പേര് ഡാറ്റാബേസിന് അനുയോജ്യമായ രീതിയിൽ ക്ലീൻ ചെയ്യുന്നു
    # ഇത് ബ്രാക്കറ്റുകൾ, ചിഹ്നങ്ങൾ ([, ], ', :, -) എന്നിവ മാറ്റി പകരം സിംഗിൾ സ്പേസ് നൽകും
    clean_movie_name = re.sub(r"[^\w\s]", " ", movie)
    # ഒന്നിലധികം സ്പേസുകൾ തുടർച്ചയായി വന്നാൽ അത് മാറ്റി ഒറ്റ സ്പേസ് ആക്കുന്നു
    clean_movie_name = re.sub(r"\s+", " ", clean_movie_name).strip()

    # 🔍 ക്ലീൻ ചെയ്ത പേര് ഉപയോഗിച്ചാണ് ഇനി ഡാറ്റാബേസിൽ തിരയുന്നത്
    k = await manual_filters(bot, query.message, text=clean_movie_name)
    if k == False:
        files, offset, total_results = await get_search_results(clean_movie_name, offset=0, filter=True)
        if files:
            k = (clean_movie_name, files, offset, total_results)
            await auto_filter(bot, query, k)
        else:
            k = await bot.send_message(
                chat_id=query.message.chat.id,
                text=f"<b>{clean_movie_name}</b> Not Found In DataBase ❌",
                reply_to_message_id=query.message.reply_to_message.id
            )
            await asyncio.sleep(10)
            await k.delete()



@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data == "close_data":
        await query.message.delete()
    elif query.data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text(
                        "Make sure I'm present in your group!!", quote=True
                    )
                    return await query.answer("Piracy Is Crime")
            else:
                await query.message.edit_text(
                    "I'm not connected to any groups!\nCheck /connections or connect to any groups",
                    quote=True,
                )
                return await query.answer("Piracy Is Crime")

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title

        else:
            return await query.answer("Piracy Is Crime")

        st = await client.get_chat_member(grp_id, userid)
        if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
            await del_all(query.message, grp_id, title)
        else:
            await query.answer(
                "You need to be Group Owner or an Auth User to do that!",
                show_alert=True,
            )
    elif query.data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("That's not for you!!", show_alert=True)
    elif "groupcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        act = query.data.split(":")[2]
        hr = await client.get_chat(int(group_id))
        title = hr.title
        user_id = query.from_user.id

        if act == "":
            stat = "CONNECT"
            cb = "connectcb"
        else:
            stat = "DISCONNECT"
            cb = "disconnect"

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
                    InlineKeyboardButton(
                        "DELETE", callback_data=f"deletecb:{group_id}"
                    ),
                ],
                [InlineKeyboardButton("BACK", callback_data="backcb")],
            ]
        )

        await query.message.edit_text(
            f"Group Name : **{title}**\nGroup ID : `{group_id}`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return await query.answer("Piracy Is Crime")
    elif "connectcb" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title

        user_id = query.from_user.id

        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Connected to **{title}**", parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                "Some error occurred!!", parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer("Piracy Is Crime")
    elif "disconnect" in query.data:
        await query.answer()

        group_id = query.data.split(":")[1]

        hr = await client.get_chat(int(group_id))

        title = hr.title
        user_id = query.from_user.id

        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Disconnected from **{title}**", parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                f"Some error occurred!!", parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer("Piracy Is Crime")
    elif "deletecb" in query.data:
        await query.answer()

        user_id = query.from_user.id
        group_id = query.data.split(":")[1]

        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text("Successfully deleted connection")
        else:
            await query.message.edit_text(
                f"Some error occurred!!", parse_mode=enums.ParseMode.MARKDOWN
            )
        return await query.answer("Piracy Is Crime")
    elif query.data == "backcb":
        await query.answer()

        userid = query.from_user.id

        groupids = await all_connections(str(userid))
        if groupids is None:
            await query.message.edit_text(
                "There are no active connections!! Connect to some groups first.",
            )
            return await query.answer("Piracy Is Crime")
        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [
                        InlineKeyboardButton(
                            text=f"{title}{act}",
                            callback_data=f"groupcb:{groupid}:{act}",
                        )
                    ]
                )
            except:
                pass
        if buttons:
            await query.message.edit_text(
                "Your connected group details ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons),
            )
    elif "alertmessage" in query.data:
        grp_id = query.message.chat.id
        i = query.data.split(":")[1]
        keyword = query.data.split(":")[2]
        reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
        if alerts is not None:
            alerts = ast.literal_eval(alerts)
            alert = alerts[int(i)]
            alert = alert.replace("\\n", "\n").replace("\\t", "\t")
            await query.answer(alert, show_alert=True)
    if query.data.startswith("file"):
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer("No such file exist.")
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        settings = await get_settings(query.message.chat.id)
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(
                    file_name="" if title is None else title,
                    file_size="" if size is None else size,
                    file_caption="" if f_caption is None else f_caption,
                )
            except Exception as e:
                logger.exception(e)
            f_caption = f_caption
        if f_caption is None:
            f_caption = f"{files.file_name}"

        try:
            if (AUTH_CHANNEL or REQ_CHANNEL) and not await is_subscribed(client, query):
                await query.answer(
                    url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}"
                )
                return
            elif settings["botpm"]:
                await query.answer(
                    url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}"
                )
                return
            else:
                await client.send_cached_media(
                    chat_id=query.from_user.id,
                    file_id=file_id,
                    caption=f_caption,
                    protect_content=True if ident == "filep" else False,
                )
                await query.answer("Check PM, I have sent files in pm", show_alert=True)
        except UserIsBlocked:
            await query.answer("Unblock the bot mahn !", show_alert=True)
        except PeerIdInvalid:
            await query.answer(
                url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}"
            )
        except Exception as e:
            await query.answer(
                url=f"https://t.me/{temp.U_NAME}?start={ident}_{file_id}"
            )
    elif query.data.startswith("checksub"):
        if (AUTH_CHANNEL or REQ_CHANNEL) and not await is_subscribed(client, query):
            await query.answer(
                "I Like Your Smartness, But Don't Be Oversmart 😒", show_alert=True
            )
            return
        ident, file_id = query.data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer("No such file exist.")
        files = files_[0]
        title = files.file_name
        size = get_size(files.file_size)
        f_caption = files.caption
        if CUSTOM_FILE_CAPTION:
            try:
                f_caption = CUSTOM_FILE_CAPTION.format(
                    file_name="" if title is None else title,
                    file_size="" if size is None else size,
                    file_caption="" if f_caption is None else f_caption,
                )
            except Exception as e:
                logger.exception(e)
                f_caption = f_caption
        if f_caption is None:
            f_caption = f"{title}"
        await query.answer()
        await client.send_cached_media(
            chat_id=query.from_user.id,
            file_id=file_id,
            caption=f_caption,
            protect_content=True if ident == "checksubp" else False,
        )
    elif query.data == "pages":
        await query.answer()

    elif query.data == "esp":
        await query.answer(text=script.ENG_SPELL, show_alert=True)
    
    elif query.data == "msp":
        await query.answer(text=script.MAL_SPELL, show_alert=True)
    
    elif query.data == "hsp":
        await query.answer(text=script.HIN_SPELL, show_alert=True)
    
    elif query.data == "tsp":
        await query.answer(text=script.TAM_SPELL, show_alert=True)

        

    
  
    elif query.data == "start":
        buttons = [[
            InlineKeyboardButton('➕ Add Me To Your Groups ➕', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
        ], [
            InlineKeyboardButton('🔍 Search', switch_inline_query_current_chat=''),
            InlineKeyboardButton('🤖 Updates', url='https://t.me/TeamEvamaria')
        ], [
            InlineKeyboardButton('ℹ️ Help', callback_data='help'),
            InlineKeyboardButton('😊 About', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.START_TXT.format(
                query.from_user.mention, temp.U_NAME, temp.B_NAME
            ),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
        await query.answer("Piracy Is Crime")
    elif query.data == "help":
        buttons = [[
            InlineKeyboardButton('Manual Filter', callback_data='manuelfilter'),
            InlineKeyboardButton('Auto Filter', callback_data='autofilter')
        ], [
            InlineKeyboardButton('Connection', callback_data='coct'),
            InlineKeyboardButton('Extra Mods', callback_data='extra')
        ], [
            InlineKeyboardButton('🏠 Home', callback_data='start'),
            InlineKeyboardButton('🔮 Status', callback_data='stats')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    elif query.data == "about":
        buttons = [[
            InlineKeyboardButton('🤖 Updates', url='https://t.me/TeamEvamaria'),
            InlineKeyboardButton('♥️ Source', callback_data='source')
        ], [
            InlineKeyboardButton('🏠 Home', callback_data='start'),
            InlineKeyboardButton('🔐 Close', callback_data='close_data')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ABOUT_TXT.format(temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    elif query.data == "source":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='about')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.SOURCE_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    elif query.data == "manuelfilter":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help'),
            InlineKeyboardButton('⏹️ Buttons', callback_data='button')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.MANUELFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    elif query.data == "button":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='manuelfilter')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.BUTTON_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    elif query.data == "autofilter":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.AUTOFILTER_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    elif query.data == "coct":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.CONNECTION_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    elif query.data == "extra":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help'),
            InlineKeyboardButton('👮‍♂️ Admin', callback_data='admin')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.EXTRAMOD_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    elif query.data == "admin":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='extra')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.message.edit_text(
            text=script.ADMIN_TXT,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    elif query.data == "stats":
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help'),
            InlineKeyboardButton('♻️', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    elif query.data == "rfrsh":
        await query.answer("Fetching MongoDb DataBase")
        buttons = [[
            InlineKeyboardButton('👩‍🦯 Back', callback_data='help'),
            InlineKeyboardButton('♻️', callback_data='rfrsh')
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await Media.count_documents()
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
        )
    elif query.data.startswith("setgs"):
        ident, set_type, status, grp_id = query.data.split("#")
        if query.message.chat.type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(query.from_user.id))
        else:
            grpid = query.message.chat.id

        if str(grp_id) != str(grpid):
            await query.message.edit(
                "Your Active Connection Has Been Changed. Go To /settings."
            )
            return await query.answer("Piracy Is Crime")

        if status == "True":
            await save_group_settings(grpid, set_type, False)
        else:
            await save_group_settings(grpid, set_type, True)

        settings = await get_settings(grpid)

        if settings is not None:
            buttons = [
                [
                    InlineKeyboardButton('Filter Button',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}'),
                    InlineKeyboardButton('Single' if settings["button"] else 'Double',
                                         callback_data=f'setgs#button#{settings["button"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Bot PM', callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["botpm"] else '❌ No',
                                         callback_data=f'setgs#botpm#{settings["botpm"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('File Secure',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["file_secure"] else '❌ No',
                                         callback_data=f'setgs#file_secure#{settings["file_secure"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('IMDB', callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["imdb"] else '❌ No',
                                         callback_data=f'setgs#imdb#{settings["imdb"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Spell Check',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["spell_check"] else '❌ No',
                                         callback_data=f'setgs#spell_check#{settings["spell_check"]}#{str(grp_id)}')
                ],
                [
                    InlineKeyboardButton('Welcome', callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}'),
                    InlineKeyboardButton('✅ Yes' if settings["welcome"] else '❌ No',
                                         callback_data=f'setgs#welcome#{settings["welcome"]}#{str(grp_id)}')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
    await query.answer("Piracy Is Crime")



async def auto_filter(client, msg, spoll=False):
    if not spoll:
        message = msg
        settings = await get_settings(message.chat.id)
        
        if message.text.startswith("/"):
            return  # ignore commands
            
        if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
            
        if 1 < len(message.text) < 100:
            raw_search_query = message.text
            
            # 1. Remove invisible characters
            search = re.sub(r'[\u200b\u200c\u200d\ufeff\u200e\u200f]', '', raw_search_query)
            
            # 2. Remove single and smart quotes
            search = re.sub(r"['‘’]", "", search)
            
            # 3. Replace special characters, symbols, and brackets with a space
            search = re.sub(r"""[–—\\_,#&=+₹@!?/( )\[\]":.¡%“”-]""", " ", search)
            
            # 4. ഒഴിവാക്കേണ്ട വാക്കുകൾ ഇവിടെ വെച്ച് മാറ്റുന്നു
            words_to_remove = r'\b(malayalm|movie|muv|movies|Hindhi|full\s+movie|web\s+series?|full\s+seasons?|full|Malayam|Thamil|Malyalm|Mlylm|hd|download|mp4|mkv|bluray|rip|link|subtile)\b'
            search = re.sub(words_to_remove, '', search, flags=re.IGNORECASE)
            
            # 5. എല്ലാത്തരം അധിക സ്പേസുകളും ഒരൊറ്റ തവണ ഇവിടെ വെച്ച് ക്ലീൻ ചെയ്യുന്നു
            search = re.sub(r'[\s\u00a0\u2000-\u200a\u202f\u205f\u3000]+', ' ', search).strip()
            
            files, offset, total_results = await get_search_results(
                search.lower(), offset=0, filter=True
            )
            
            if not files:
                if settings["spell_check"]:
                    return await advantage_spell_chok(client, msg)
                else:
                    return
        else:
            return
    else:
        settings = await get_settings(msg.message.chat.id)
        message = msg.message.reply_to_message  # msg will be callback query
        search, files, offset, total_results = spoll

    pre = "filep" if settings["file_secure"] else "file"
    if settings["button"]:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file.file_size)}] {file.file_name}",
                    callback_data=f"{pre}#{file.file_id}",
                ),
            ]
            for file in files
        ]
    else:
        btn = [
            [
                InlineKeyboardButton(
                    text=f"{file.file_name}",
                    callback_data=f"{pre}#{file.file_id}",
                ),
                InlineKeyboardButton(
                    text=f"{get_size(file.file_size)}",
                    callback_data=f"{pre}#{file.file_id}",
                ),
            ]
            for file in files
        ]

    if offset != "":
        key = f"{message.chat.id}-{message.id}"
        BUTTONS[key] = search
        req = message.from_user.id if message.from_user else 0
        btn.append(
            [
                InlineKeyboardButton(
                    text=f"🗓 1/{round(int(total_results) / 10)}", callback_data="pages"
                ),
                InlineKeyboardButton(
                    text="NEXT ⏩", callback_data=f"next_{req}_{key}_{offset}"
                ),
            ]
        )
    else:
        btn.append([
            InlineKeyboardButton(text="🗓 1/1", callback_data="pages")
        ])

    imdb = await get_poster(search, file=files[0].file_name) if settings["imdb"] and files else None
    TEMPLATE = settings["template"]

    if imdb:
        cap = TEMPLATE.format(
            query=search,
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
            url=imdb.get("url", "N/A"),
            **locals()
        )
    else:
        cap = f"Here is what I found for your query {search}"

    poster_url = imdb.get("poster") if imdb else None

    if poster_url:
        try:
            await message.reply_photo(
                photo=poster_url,
                caption=cap[:1024],
                reply_markup=InlineKeyboardMarkup(btn)
            )
        except Exception as e:
            logger.warning("Poster sending failed: %s", e)
            await message.reply_text(
                cap,
                reply_markup=InlineKeyboardMarkup(btn)
            )
    else:
        await message.reply_text(
            cap,
            reply_markup=InlineKeyboardMarkup(btn)
        )

    if spoll:
        await msg.delete()



async def _spell_not_found(msg):
    """"Not found" reply with language + Google buttons. The query is URL-encoded and capped:
    raw text with spaces, '&', '#', emoji or a very long message makes Telegram answer BUTTON_URL_INVALID."""
    query = quote_plus((text or "").strip()[:100])
    button = [[
        InlineKeyboardButton('ENG', callback_data='esp'),
        InlineKeyboardButton('MAL', callback_data='msp'),
        InlineKeyboardButton('HIN', callback_data='hsp'),
        InlineKeyboardButton('TAM', callback_data='tsp'),
    ]]
    if query:
        button.append([InlineKeyboardButton('🔍 ɢᴏᴏɢʟᴇ 🔎', url=f"https://www.google.com/search?q={query}")])
    try:
        k = await msg.reply_text(
            text=script.SPOLL_NOT_FND,
            reply_markup=InlineKeyboardMarkup(button),
            reply_to_message_id=msg.id
        )
    except Exception as e:                       # never let a failed helper message crash the handler
        logger.warning(f"spell-check not-found reply failed: {e}")
        return
    await asyncio.sleep(60)
    try:
        await k.delete()
    except Exception:
        pass



import asyncio  # ഫയലിന്റെ മുകളിൽ ഉണ്ടെന്ന് ഉറപ്പാക്കുക

SPELL_CHECK = {}

# ബാക്ക്‌ഗ്രൗണ്ടിൽ ഡാറ്റ ഡിലീറ്റ് ചെയ്യാനുള്ള ഹെൽപ്പർ ഫങ്ക്ഷൻ
async def auto_delete_spell_data(msg_id, delay=60):
    await asyncio.sleep(delay)
    if msg_id in SPELL_CHECK:
        del SPELL_CHECK[msg_id]

async def advantage_spell_chok(client, msg):
    mv_id, mv_rqst = msg.id, msg.text
    reqstr1 = msg.from_user.id if msg.from_user else 0
    cleaned_query = re.sub(
        r"\b(pl(i|e)\*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|"
        r"br((o|u)h?)\*|^h(e|a)?(l)\*(o)\*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)\*|"
        r"kit(t(i|y)?)?o(w)?|thar(u)?(o)\*w?|kittum(o)\*|aya(k)\*(um(o)\*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", msg.text, flags=re.IGNORECASE
    ).strip()    
    
    reqst_gle = quote_plus(mv_rqst)

    try:
        movies = await get_posters(cleaned_query, bulk=True)
    except Exception:
        movies = None

    google_button = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔎 𝗖𝗼𝗿𝗿𝗲𝗰𝘁 𝗦𝗽𝗲𝗹𝗹𝗶𝗻𝗴 (𝖦𝗈𝗈𝗀𝗅𝖾)", url=f"https://google.com{reqst_gle}")],
        [InlineKeyboardButton("📜 Rᴜʟᴇs", url="https://t.me"), InlineKeyboardButton("📥 Rᴇqᴜᴇsᴛ", url="https://t.me")]
    ])

    if not movies:
        try:
            await msg.reply_text(
                script.SPELL_TEXT.format(msg.from_user.mention),
                reply_markup=google_button,
                reply_to_message_id=msg.id,
                parse_mode=enums.ParseMode.HTML,
                disable_web_page_preview=True
            )
        except Exception:
            pass
        return

    movielist = []
    for movie in movies:
        if isinstance(movie, dict):
            title = movie.get('title')
            year = movie.get('year')
        else:
            title = movie.get('title') if hasattr(movie, 'get') else getattr(movie, 'title', None)
            year = movie.get('year') if hasattr(movie, 'get') else getattr(movie, 'year', None)
        
        if title:
            if year and str(year) != "N/A":
                year_str = re.findall(r'\b(19\d{2}|20\d{2})\b', str(year))
                year_val = f" {year_str}" if year_str else ""
            else:
                year_val = ""
                
            movielist.append(f"{title.strip()}{year_val}")

    if not movielist:
        return

    # 💾 ഇവിടെ സിനിമകളുടെ ലിസ്റ്റ് ഡിക്‌ഷ്ണറിയിലേക്ക് സേവ് ചെയ്യുന്നു
    SPELL_CHECK[msg.id] = movielist[:10]
    
    # ⏱️ കൃത്യം 1 മിനിറ്റ് (60 സെക്കൻഡ്) കഴിയുമ്പോൾ ഈ മെസ്സേജ് ഐഡിയിലുള്ള ഡാറ്റ ഡിലീറ്റ് ചെയ്യും
    asyncio.create_task(auto_delete_spell_data(msg.id, 60))

    buttons = []
    for index, movie_name in enumerate(movielist[:10]):
        buttons.append([InlineKeyboardButton(text=movie_name, callback_data=f"spolling#{reqstr1}#{index}")])
        
    buttons.append([InlineKeyboardButton("🔎 𝗖𝗼𝗿𝗿𝗲𝗰𝘁 𝗦𝗽𝗲𝗹𝗹𝗶𝗻𝗴 (𝖦𝗈𝗈𝗀𝗅𝖾)", url=f"https://google.com{reqst_gle}")])
    buttons.append([InlineKeyboardButton("❌ Close", callback_data=f"spolling#{reqstr1}#close_spellcheck")])

    spell_list_markup = InlineKeyboardMarkup(buttons)
    spell_list_text = script.NO_TXT if hasattr(script, 'NO_TXT') else "താങ്കൾ തിരഞ്ഞ സിനിമ കണ്ടെത്താനായില്ല. താഴെയുള്ള സജഷനുകളിൽ നിന്നും തിരഞ്ഞെടുക്കുക 👇"

    try:
        await msg.reply_text(
            text=spell_list_text,
            reply_markup=spell_list_markup,
            reply_to_message_id=msg.id,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True
        )
    except Exception:
        return



            

  
async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    __msg = None
    reply_id = message.reply_to_message_id if message.reply_to_message else message.id
    keywords = await get_filters(group_id)
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            if btn is not None:
                try:
                    if fileid == "None":
                        if btn == "[]":
                            __msg = await client.send_message(
                                group_id, reply_text, disable_web_page_preview=True
                            )
                        else:
                            button = eval(btn)
                            __msg = await client.send_message(
                                group_id,
                                reply_text,
                                disable_web_page_preview=True,
                                reply_markup=InlineKeyboardMarkup(button),
                                reply_to_message_id=reply_id,
                            )
                    elif btn == "[]":
                        __msg = await client.send_cached_media(
                            group_id,
                            fileid,
                            caption=reply_text or "",
                            reply_to_message_id=reply_id,
                        )
                    else:
                        button = eval(btn)
                        __msg = await message.reply_cached_media(
                            fileid,
                            caption=reply_text or "",
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id,
                        )
                except Exception as e:
                    logger.exception(e)
                if __msg:
                    scheduler.add_job(
                        _delete,
                        "date",
                        [client, __msg],
                        run_date=datetime.now() + timedelta(seconds=DELETE_TIME),
                    )
                break
    else:
        return False


@Client.on_message(filters.private & filters.text & filters.incoming)
async def handlePrivate(client, message):
    await auto_filter(client, message)
