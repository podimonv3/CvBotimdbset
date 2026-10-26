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


async def get_search_results(
    query, file_type=None, max_results=10, offset=0, filter=False
):
    """For given query return (results, next_offset)"""

    # 1. യൂസർ അയക്കുന്ന ടെക്സ്റ്റിലെ ചിഹ്നങ്ങളും സ്പെഷ്യൽ ക്യാരക്ടറുകളും നീക്കം ചെയ്യുന്നു
    cleaned_query = re.sub(r"[^\w\s]", "", query)
    cleaned_query = re.sub(r"\s+", " ", cleaned_query).strip()

    # മെയിൻ ഫംഗ്ഷൻ - ഈ ഹെൽപർ ഫംഗ്ഷൻ ആണ് യഥാർത്ഥ തിരച്ചിൽ നടത്തുന്നത്
    async def execute_search(search_text):
        if not search_text:
            raw_pattern = "."
            prefix_pattern = "."
        elif " " not in search_text:
            raw_pattern = r"(\b|[\.\+\-_])" + search_text + r"(\b|[\.\+\-_])"
            prefix_pattern = r"^" + re.escape(search_text) + r"(?=\s|[\.\+\-_()]|$)"
        else:
            raw_pattern = search_text.replace(" ", r".*[\s\.\+\-_]")
            prefix_pattern = r"^" + re.escape(search_text).replace(r"\ ", r".*[\s\.\+\-_()]")

        try:
            regex = re.compile(raw_pattern, flags=re.IGNORECASE)
            prefix_regex = re.compile(prefix_pattern, flags=re.IGNORECASE)
        except:
            return [], 0, 0

        # --- ഫിൽട്ടറുകൾ തയാറാക്കുന്നു ---
        if USE_CAPTION_FILTER:
            prefix_filter = {"$or": [{"file_name": prefix_regex}, {"caption": prefix_regex}]}
            normal_filter = {
                "$and": [
                    {"$or": [{"file_name": regex}, {"caption": regex}]},
                    {"file_name": {"$not": prefix_regex}},
                    {"caption": {"$not": prefix_regex}}
                ]
            }
        else:
            prefix_filter = {"file_name": prefix_regex}
            normal_filter = {
                "$and": [
                    {"file_name": regex},
                    {"file_name": {"$not": prefix_regex}}
                ]
            }

        if file_type:
            prefix_filter["file_type"] = file_type
            normal_filter["$and"].append({"file_type": file_type})

        # ആകെ റിസൾട്ടുകളുടെ എണ്ണം കാണാൻ
        total_prefix = await Media.count_documents(prefix_filter)
        total_normal = await Media.count_documents(normal_filter)
        total_results = total_prefix + total_normal

        # ഡാറ്റാബേസ് സെർച്ചിംഗ്
        prefix_cursor = Media.find(prefix_filter).sort("$natural", -1).skip(offset).limit(max_results)
        prefix_files = await prefix_cursor.to_list(length=max_results)

        if len(prefix_files) < max_results:
            remaining = max_results - len(prefix_files)
            normal_skip = max(0, offset - total_prefix)
            normal_cursor = Media.find(normal_filter).sort("$natural", -1).skip(normal_skip).limit(remaining)
            normal_files = await normal_cursor.to_list(length=remaining)
        else:
            normal_files = []

        return prefix_files + normal_files, total_results

    # --- ലോജിക് ആരംഭിക്കുന്നു ---
    
    # 1. ആദ്യം യൂസർ നൽകിയ അതേ വാക്ക് വെച്ച് തിരയുന്നു (उदा: bhramem)
    files, total_results = await execute_search(cleaned_query)
    
    # 2. റിസൾട്ട് ഒന്നും കിട്ടിയില്ലെങ്കിൽ മാത്രം അക്ഷരങ്ങൾ ഓരോന്നായി കുറച്ച് തിരയുന്നു
    if not files and cleaned_query:
        current_query = cleaned_query
        
        # സുരക്ഷാ മുൻകരുതൽ: വാക്കിന്റെ നീളം 4 അക്ഷരത്തിൽ കൂടുതൽ ആണെങ്കിൽ മാത്രം കട്ട് ചെയ്യുക
        # (ഇത് വഴി 'Vi' അല്ലെങ്കിൽ 'V' പോലുള്ള ചെറിയ വാക്കുകളിലേക്ക് പോയി ബോട്ട് സ്ലോ ആകുന്നത് തടയാം)
        while len(current_query) > 4:
            current_query = current_query[:-1] # അവസാനത്തെ ഒരു അക്ഷരം കളയുന്നു
            
            if " " not in current_query:
                raw_pattern = r"(\b|[\.\+\-_])" + re.escape(current_query) + r".*?(\b|[\.\+\-_]|$)"
                prefix_pattern = r"^" + re.escape(current_query)
            else:
                raw_pattern = current_query.replace(" ", r".*[\s\.\+\-_]") + r".*"
                prefix_pattern = r"^" + re.escape(current_query).replace(r"\ ", r".*[\s\.\+\-_()]") + r".*"

            files, total_results = await execute_search(raw_pattern, prefix_pattern)
            
            if files: # റിസൾട്ട് കിട്ടിയാൽ ലൂപ്പ് ഇവിടെ അവസാനിക്കും
                break
                
    # നെക്സ്റ്റ് ഓഫ്സെറ്റ് കണക്കാക്കുന്നു
    next_offset = offset + max_results
    if next_offset > total_results:
        next_offset = ""

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
