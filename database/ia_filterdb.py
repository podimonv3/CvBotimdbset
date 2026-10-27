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
    """
    Returns results sorted by exact prefix match first, then by alphabetical order.
    Fixed uMongo UnknownFieldInDBError.
    """
    query = query.strip()
    if not query:
        return [], '', 0

    escaped_query = re.escape(query)
    raw_pattern = escaped_query.replace(r'\ ', r'.*')
    
    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
        prefix_regex = re.compile(r'^' + escaped_query, flags=re.IGNORECASE)
    except Exception:
        return [], '', 0

    match_filter = {'file_name': regex}
    if file_type:
        match_filter['file_type'] = file_type

    # ਆਕੇ ഫയലുകളുടെ എണ്ണം എടുക്കുന്നു
    total_results = await Media.count_documents(match_filter)
    
    pipeline = [
        {'$match': match_filter},
        {
            '$addFields': {
                'search_score': {
                    '$cond': [{'$regexMatch': {'input': '$file_name', 'regex': prefix_regex}}, 0, 1]
                }
            }
        },
        # ഇവിടെ സീരീസുകൾ കൃത്യമായി വരാൻ file_name: 1 (A to Z) ഉപയോഗിച്ചിരിക്കുന്നു
        {'$sort': {'search_score': 1, 'file_name': 1}},
        {'$skip': offset},
        {'$limit': max_results},
        # uMongo എറർ ഒഴിവാക്കാൻ ഡാറ്റാബേസിൽ നിന്ന് താൽക്കാലികമായി ഉണ്ടാക്കിയ 'search_score' ഒഴിവാക്കുന്നു
        {'$project': {'search_score': 0}}
    ]

    cursor = Media.collection.aggregate(pipeline)
    raw_files = await cursor.to_list(length=max_results)

    # ഇപ്പോൾ uMongo സുഗമമായി ഒബ്‌ജക്റ്റുകൾ ബിൽഡ് ചെയ്യും
    files = [Media.build_from_mongo(doc) for doc in raw_files] if raw_files else []

    next_offset = offset + len(files)
    if next_offset >= total_results:
        next_offset = ''

    return files, next_offset, total_results







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
