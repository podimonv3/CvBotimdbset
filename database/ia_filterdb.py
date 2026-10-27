import base64
import logging
import re
from struct import pack

from marshmallow.exceptions import ValidationError
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from pyrogram.file_id import FileId
from umongo import Document, Instance, fields

from info import COLLECTION_NAME, DATABASE_NAME, DATABASE_URI, USE_CAPTION_FILTER

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)


@instance.register
class Media(Document):
    file_id = fields.StrField(attribute="_id")
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    chatID = fields.IntField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)

    class Meta:
        indexes = ("$file_name",)
        collection_name = COLLECTION_NAME


import re


async def save_file(media):
    """Save file in database"""

    # TODO: Find better way to get same file_id for same media to avoid duplicates
    file_id, file_ref = unpack_new_file_id(media.file_id)

    raw_name = str(media.file_name)

    # 1. തുടക്കത്തിൽ വരുന്ന [] ബ്രാക്കറ്റുകൾ, @ ടാഗുകൾ, വെബ്‌സൈറ്റുകൾ എന്നിവ ഒഴിവാക്കാൻ
    clean_pattern = r"^(\s*(\[.*?\]|@\w+|www\.\S+|https?://\S+)\s*)+"
    cleaned_name = re.sub(clean_pattern, "", raw_name, flags=re.IGNORECASE)

    # 2. ബാക്കിയുള്ള ഭാഗത്തെ അണ്ടർസ്‌കോർ, ഹൈഫൻ, ഡോട്ട് എന്നിവ മാറ്റി സ്പേസ് ആക്കുന്നു
    file_name = re.sub(r"(_|\-|\.|\+)", " ", cleaned_name)

    # 3. പുതിയ മാറ്റം: അക്ഷരങ്ങളും അക്കങ്ങളും സ്പേസും ഒഴികെയുള്ള എല്ലാ സ്പെഷ്യൽ ക്യാരക്ടറുകളും (ചിഹ്നങ്ങൾ) പൂർണ്ണമായി നീക്കം ചെയ്യുന്നു
    file_name = re.sub(r"[^\w\s]", "", file_name)

    # 4. തുടക്കത്തിലെയും ഒടുക്കത്തിലെയും അനാവശ്യ സ്പേസ് കളയുന്നു, ഇരട്ട സ്പേസുകൾ ഒറ്റ സ്പേസ് ആക്കുന്നു
    file_name = re.sub(r"\s+", " ", file_name).strip()

    try:
        file = Media(
            file_id=file_id,
            file_ref=file_ref,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            chatID=media.chatID,
            caption=media.caption.html if media.caption else None,
        )
    except ValidationError:
        logger.exception("Error occurred while saving file in database")
        return False, 2
    else:
        try:
            await file.commit()
        except DuplicateKeyError:
            logger.warning(
                f'{getattr(media, "file_name", "NO_FILE")} is already saved in database'
            )
            return False, 0
        else:
            logger.info(
                f'{getattr(media, "file_name", "NO_FILE")} is saved to database'
            )
            return True, 1




import re

async def get_search_results(query, file_type=None, max_results=10, offset=0, filter=False):
    """Search files with safe matching, title/year ranking and pagination."""
    query = query.strip()
    if not query or max_results < 1 or offset < 0:
        return [], '', 0

    # Escape regex characters and allow common separators between words.
    words = query.split()
    escaped_words = [re.escape(word) for word in words]
    flexible_query = r'[\s._+\-]*'.join(escaped_words)
    raw_pattern = r'(?<!\w)' + flexible_query + r'(?!\w)'

    try:
        regex = re.compile(raw_pattern, re.IGNORECASE)
    except re.error:
        return [], '', 0

    search_filter = {'file_name': regex}
    if USE_CAPTION_FILTER:
        search_filter = {'$or': [
            {'file_name': regex},
            {'caption': regex}
        ]}
    if file_type:
        search_filter['file_type'] = file_type

    try:
        total_results = await Media.count_documents(search_filter)
        if not total_results:
            return [], '', 0

        # Rank title-prefix matches first, then matching year, then other matches.
        year_match = re.search(r'\b(?:19|20)\d{2}\b', query)
        year_pattern = re.escape(year_match.group()) if year_match else None
        prefix_pattern = r'^\s*' + flexible_query

        pipeline = [
            {'$match': search_filter},
            {'$addFields': {
                '_search_rank': {
                    '$switch': {
                        'branches': [
                            {
                                'case': {'$regexMatch': {
                                    'input': {'$ifNull': ['$file_name', '']},
                                    'regex': prefix_pattern,
                                    'options': 'i'
                                }},
                                'then': 0
                            }
                        ] + ([{
                            'case': {'$regexMatch': {
                                'input': {'$ifNull': ['$file_name', '']},
                                'regex': r'(?<!\d)' + year_pattern + r'(?!\d)',
                                'options': 'i'
                            }},
                            'then': 1
                        }] if year_pattern else []),
                        'default': 2
                    }
                }
            }},
            {'$sort': {'_search_rank': 1, '_id': -1}},
            {'$skip': offset},
            {'$limit': max_results},
            {'$project': {'_search_rank': 0}}
        ]

        cursor = Media.aggregate(pipeline)
        files = await cursor.to_list(length=max_results)
        next_offset = offset + max_results if offset + max_results < total_results else ''
        return files, next_offset, total_results

    except Exception:
        logger.exception("get_search_results failed for query: %r", query)
        return [], '', 0




async def get_file_details(query):
    filter = {"file_id": query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails


def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0

    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0

            r += bytes([i])

    return base64.urlsafe_b64encode(r).decode().rstrip("=")


def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")


def unpack_new_file_id(new_file_id):
    """Return file_id, file_ref"""
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash,
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref
