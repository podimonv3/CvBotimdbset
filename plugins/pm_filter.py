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
from utils import (get_poster, get_settings, get_size, is_subscribed,
                   save_group_settings, scheduler, search_gagala, temp)

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

BUTTONS = {}
SPELL_CHECK = {}

DELETE_TIME = int(environ.get("DELETE_TIME", 600))



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
            search = re.sub(r"""[-–—\\_,#&@!?/( )\[\]":\.¡%“”]""", " ", search)
            
            # 4. Normalize all regular and Unicode white spaces into a single space
            search = re.sub(r'[\s\u00a0\u2000-\u200a\u202f\u205f\u3000]+', ' ', search)
            
            files, offset, total_results = await get_search_results(
                search.lower(), offset=0, filter=True
            )
            
            if not files:                
                reqst_gle = search.replace(" ", "+")              
                btn_google = InlineKeyboardButton("🔎 𝗖𝗼𝗿𝗿𝗲𝗰𝘁 𝗦𝗽𝗲𝗹𝗹𝗶𝗻𝗴 (𝖦𝗈𝗈𝗀𝗅𝖾) 🔍", url=f"https://www.google.com/search?q={reqst_gle}")
                google_row = [btn_google]

                # നിങ്ങൾ ആവശ്യപ്പെട്ട പുതിയ ഭാഷാ ബട്ടണുകൾ ഇവിടെ ചേർത്തു
                lang_row = [
                    InlineKeyboardButton('ENG', callback_data='esp'),
                    InlineKeyboardButton('MAL', callback_data='msp'),
                    InlineKeyboardButton('HIN', callback_data='hsp'),
                    InlineKeyboardButton('TAM', callback_data='tsp'),
                ]

                # രണ്ട് വരികളും ഒന്നിച്ച് കീബോർഡിലേക്ക് ആഡ് ചെയ്തു
                keyboard = InlineKeyboardMarkup(inline_keyboard=[google_row, lang_row])
                
                try:
                    k = await msg.reply_text(
                        text=f"<b>❝ 𝖧𝖾𝗒 {msg.from_user.mention} താഴെ ഉള്ള കാര്യങ്ങൾ ശ്രദ്ധിക്കുക ❞\n\n🔹കറക്റ്റ് സ്പെല്ലിംഗിൽ ചോദിക്കുക. (ഇംഗ്ലീഷിൽ മാത്രം)\n\n🔸സിനിമകൾ ഇംഗ്ലീഷിൽ Type ചെയ്ത് മാത്രം ചോദിക്കുക.\n\n🔹OTT റിലീസ് ആകാത്ത സിനിമകൾ ചോദിക്കരുത്.\n\n🔸സിനിമയുടെ പേര് [വർഷം ഭാഷ] ഈ രീതിയിൽ ചോദിക്കുക.\n\n🔹ഈ request അഡ്മിന് അയച്ചു കഴിഞ്ഞു ✅.\n\n🔹24Hr നുള്ളിൽ (spelling കറക്റ്റ് ആണെങ്കിൽ)Database ഇൽ ഇല്ലാത്തതാണെങ്കിൽ ആഡ് ചെയ്തിരിക്കും</b>", 
                        reply_markup=keyboard
                    )                    
                    # await k.delete()
                    return       
                except Exception as e:
                    return 
            else:
                pass  # ഫയലുകൾ ഉണ്ടെങ്കിൽ താഴെയുള്ള കോഡിലേക്ക് പോകും
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
        btn.append([InlineKeyboardButton(text="🗓 1/1", callback_data="pages")])
   
    cap = f"Here is what i found for your query {search}"
    await message.reply_text(cap, reply_markup=InlineKeyboardMarkup(btn))
    if spoll:
        await msg.message.delete()




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
