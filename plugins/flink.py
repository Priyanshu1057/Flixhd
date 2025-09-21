import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from database.database import db
from helper_func import encode, decode
from config import OWNER_ID,CHANNEL_ID 
import logging

logger = logging.getLogger(__name__)

# Store user states for flink process (in-memory for session)
user_states = {}

class FlinkDatabase:
    """Flink database operations using existing db connection"""
    def __init__(self):
        self.col = db.flink_formats if hasattr(db, 'flink_formats') else db.db.flink_formats
    
    async def save_user_format(self, user_id: int, format_text: str):
        """Save user's flink format"""
        try:
            await self.col.update_one(
                {'user_id': user_id},
                {'$set': {'format': format_text}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error saving flink format: {e}")
    
    async def get_user_format(self, user_id: int):
        """Get user's saved format"""
        try:
            result = await self.col.find_one({'user_id': user_id})
            return result['format'] if result else None
        except Exception as e:
            logger.error(f"Error getting flink format: {e}")
            return None
    
    async def delete_user_format(self, user_id: int):
        """Delete user's format"""
        try:
            await self.col.delete_one({'user_id': user_id})
        except Exception as e:
            logger.error(f"Error deleting flink format: {e}")

# Initialize flink database
flink_db = FlinkDatabase()

@Client.on_message(filters.command("flink") & filters.private)
async def flink_command(client: Client, message: Message):
    """Main flink command - admin only"""
    user_id = message.from_user.id
    
    # Check if user is admin
    if user_id not in ADMINS:
        await message.reply("❌ **Access Denied!**\n\nThis command is only available for admins.")
        return
    
    # Reset user state
    user_states[user_id] = {"step": "menu"}
    
    # Get current format from database
    current_format = await flink_db.get_user_format(user_id)
    if current_format:
        format_text = f"**Current Format:**\n`{current_format}`"
    else:
        format_text = "**Current Format:**\n`480p = 14, 720p = 14, 1080p = 14`"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 SET FORMAT", callback_data="flink_set_format")],
        [InlineKeyboardButton("⚡ START PROCESS", callback_data="flink_start_process")],
        [InlineKeyboardButton("🔄 REFRESH", callback_data="flink_refresh")],
        [InlineKeyboardButton("❌ CANCEL", callback_data="flink_cancel")]
    ])
    
    await message.reply(
        f"**🔗 FORMATTED LINK GENERATOR**\n\n"
        f"{format_text}\n\n"
        f"**Instructions:**\n"
        f"1️⃣ Set your format first\n"
        f"2️⃣ Start the process\n"
        f"3️⃣ Send the channel post link\n\n"
        f"**Format Example:**\n"
        f"`480p = 2, 720p = 2, 1080p = 2`",
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("^flink_"))
async def flink_callback_handler(client: Client, callback_query: CallbackQuery):
    """Handle flink button callbacks"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if user_id not in ADMINS:
        await callback_query.answer("❌ Access Denied!", show_alert=True)
        return
    
    if data == "flink_set_format":
        user_states[user_id] = {"step": "waiting_format"}
        await callback_query.edit_message_text(
            "**🔗 SET FORMAT**\n\n"
            "Please send your format in the following pattern:\n\n"
            "**Examples:**\n"
            "`480p = 2, 720p = 2, 1080p = 2`\n""`360P = 1, 480P = 1, 720P = 1, 1080P = 1`\n"
            "`HDRIP = 1, 4K = 1, 1080P = 2`\n\n"
            "**Explanation:**\n"
            "• 480p = 2 means 2 files for 480p quality\n"
            "• 720p = 1 means 1 file for 720p quality\n\n"
            "Type CANCEL to cancel this operation."
        )
    
    elif data == "flink_start_process":
        current_format = await flink_db.get_user_format(user_id)
        if not current_format:
            await callback_query.answer("❌ Please set format first!", show_alert=True)
            return
        
        user_states[user_id] = {"step": "waiting_post_link", "format": current_format}
        await callback_query.edit_message_text(
            "**⚡ START PROCESS**\n\n"
            f"**Current Format:** `{current_format}`\n\n"
            "Now send me the channel post link or forward the post from your database channel.\n\n"
            "**Example:**\n"
            "`https://t.me/c/1995978690/64879`\n\n"
            "Type CANCEL to cancel this operation."
        )
    
    elif data == "flink_refresh":
        current_format = await flink_db.get_user_format(user_id)
        if current_format:
            format_text = f"**Current Format:**\n`{current_format}`"
        else:
            format_text = "**Current Format:**\n`480p = 14, 720p = 14, 1080p = 14`"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 SET FORMAT", callback_data="flink_set_format")],
            [InlineKeyboardButton("⚡ START PROCESS", callback_data="flink_start_process")],
            [InlineKeyboardButton("🔄 REFRESH", callback_data="flink_refresh")],
            [InlineKeyboardButton("❌ CANCEL", callback_data="flink_cancel")]
        ])
        
        await callback_query.edit_message_text(
            f"**🔗 FORMATTED LINK GENERATOR**\n\n"
            f"{format_text}\n\n"
            f"**Instructions:**\n"
            f"1️⃣ Set your format first\n"
            f"2️⃣ Start the process\n"
            f"3️⃣ Send the channel post link\n\n"
            f"**Format Example:**\n"
            f"`480p = 2, 720p = 2, 1080p = 2`",
            reply_markup=keyboard
        )
    
    elif data == "flink_cancel":
        if user_id in user_states:
            del user_states[user_id]
        await callback_query.edit_message_text("❌ **Operation Cancelled!**")

# IMPORTANT: This handler has higher priority to catch flink-related text
@Client.on_message(filters.private & filters.text & filters.user(ADMINS), group=0)
async def flink_text_handler(client: Client, message: Message):
    """Handle flink text input - only for admins in flink process"""
    user_id = message.from_user.id
    
    # Only process if user is in flink state
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    text = message.text.strip()
    
    # Handle cancel command
    if text.upper() == "CANCEL":
        del user_states[user_id]
        await message.reply("❌ **Operation Cancelled!**")
        return
    
    # Handle format setting
    if state.get("step") == "waiting_format":
        if validate_format(text):
            await flink_db.save_user_format(user_id, text)
            del user_states[user_id]
            await message.reply(
                f"✅ **Format Set Successfully!**\n\n"
                f"**Format:** `{text}`\n\n"
                f"You can now use /flink again to start the process."
            )
        else:
            await message.reply(
                "❌ **Invalid Format!**\n\n"
                "Please use the correct format:\n"
                "`480p = 2, 720p = 2, 1080p = 2`\n\n"
                "Try again or type CANCEL to cancel."
            )
        # Stop propagation to other handlers
        raise StopPropagation
    
    # Handle post link processing
    elif state.get("step") == "waiting_post_link":
        await process_post_link(client, message, text, user_id)
        # Stop propagation to other handlers
        raise StopPropagation

# Handle forwarded messages for flink
@Client.on_message(filters.private & filters.forwarded & filters.user(ADMINS), group=0)
async def flink_forwarded_handler(client: Client, message: Message):
    """Handle forwarded messages for flink - only if user is in flink process"""
    user_id = message.from_user.id
    
    # Only process if user is in flink state waiting for post link
    if user_id not in user_states:
        return
        
    state = user_states.get(user_id)
    if not (state and state.get("step") == "waiting_post_link"):
        return
    
    # Extract message info from forwarded message
    if message.forward_from_chat:
        channel_id = message.forward_from_chat.id
        message_id = message.forward_from_message_id
        
        # Create the post link
        if str(channel_id).startswith("-100"):
            # Private channel
            clean_id = str(channel_id)[4:]  # Remove -100 prefix
            post_link = f"https://t.me/c/{clean_id}/{message_id}"
        else:
            # Public channel
            username = message.forward_from_chat.username
            post_link = f"https://t.me/{username}/{message_id}"
        
        await process_post_link(client, message, post_link, user_id)
        # Stop propagation to other handlers
        raise StopPropagation
    else:
        await message.reply("❌ **Invalid forwarded message!**\n\nPlease forward from a channel.")
        raise StopPropagation

def validate_format(format_text):
    """Validate the format string"""
    try:
        # Pattern: quality = number, quality = number, ...
        pattern = r'^\s*\w+\s*=\s*\d+(?:\s*,\s*\w+\s*=\s*\d+)*\s*$'
        return bool(re.match(pattern, format_text, re.IGNORECASE))
    except:
        return False

async def process_post_link(client: Client, message: Message, post_link: str, user_id: int):
    """Process the post link and generate formatted links"""
    try:
        # Extract channel and message info from link
        channel_id = None
        start_msg_id = None
        
        if "/c/" in post_link:
            # Private channel link format: https://t.me/c/CHANNEL_ID/MESSAGE_ID
            parts = post_link.split("/")
            if len(parts) >= 2:
                channel_id = int("-100" + parts[-2])
                start_msg_id = int(parts[-1])
        elif "t.me/" in post_link and "/c/" not in post_link:
            # Public channel format: https://t.me/USERNAME/MESSAGE_ID
            parts = post_link.split("/")
            if len(parts) >= 2:
                username = parts[-2]
                start_msg_id = int(parts[-1])
                # Try to get channel info
                try:
                    chat = await client.get_chat(username)
                    channel_id = chat.id
                except:
                    await message.reply("❌ **Cannot access this channel!**")
                    return
        else:
            await message.reply(
                "❌ **Invalid Link Format!**\n\n"
                "Please send a valid channel post link:\n"
                "• Private: `https://t.me/c/CHANNEL_ID/MESSAGE_ID`\n"
                "• Public: `https://t.me/USERNAME/MESSAGE_ID`"
            )
            return
        
        if not channel_id or not start_msg_id:
            await message.reply("❌ **Could not extract channel information!**")
            return
        
        current_format = await flink_db.get_user_format(user_id)
        if not current_format:
            await message.reply("❌ No format set! Please set format first.")
            return
            
        format_dict = parse_format(current_format)
        
        # Get messages from the channel
        messages = []
        current_msg_id = start_msg_id
        total_files_needed = sum(format_dict.values())
        
        progress_msg = await message.reply("🔄 Processing... Please wait.")
        
        # Collect the required number of messages
        for i in range(total_files_needed):
            try:
                msg = await client.get_messages(channel_id, current_msg_id + i)
                if msg and (msg.document or msg.video or msg.audio):
                    messages.append(msg)
            except Exception as e:
                logger.error(f"Error getting message {current_msg_id + i}: {e}")
                continue
        
        if len(messages) < total_files_needed:
            await progress_msg.edit(
                f"⚠️ **Warning!**\n\n"
                f"Found only {len(messages)} files but need {total_files_needed}.\n"
                f"Proceeding with available files..."
            )
            await asyncio.sleep(2)
        
        # Generate links
        formatted_links = await generate_formatted_links(client, messages, format_dict)
        
        if formatted_links:
            # Create the final message with buttons
            keyboard = []
            for quality, link in formatted_links.items():
                keyboard.append([InlineKeyboardButton(quality, url=link)])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await progress_msg.edit(
                f"✅ **Formatted Links Generated Successfully!**\n\n"
                f"**Total Qualities:** {len(formatted_links)}\n"
                f"**Files Processed:** {len(messages)}\n\n"
                f"**Below is the formatted link:**",
                reply_markup=reply_markup
            )
            
            # Also send the raw links
            links_text = "\n".join([f"**{quality}** - {link}" for quality, link in formatted_links.items()])
            await message.reply(
                f"**🔗 Raw Links:**\n\n{links_text}",
                disable_web_page_preview=True
            )
        else:
            await progress_msg.edit("❌ **Failed to generate links!**")
        
        # Reset user state
        if user_id in user_states:
            del user_states[user_id]
            
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")
        logger.error(f"Error in process_post_link: {e}")
        if user_id in user_states:
            del user_states[user_id]

def parse_format(format_text):
    """Parse format string into dictionary"""
    format_dict = {}
    pairs = format_text.split(",")
    
    for pair in pairs:
        parts = pair.split("=")
        if len(parts) == 2:
            quality = parts[0].strip()
            count = int(parts[1].strip())
            format_dict[quality] = count
    
    return format_dict

async def generate_formatted_links(client, messages, format_dict):
    """Generate formatted download links using existing bot's encode function"""
    try:
        formatted_links = {}
        msg_index = 0
        
        for quality, count in format_dict.items():
            if msg_index >= len(messages):
                break
            
            # Get the required messages for this quality
            quality_messages = messages[msg_index:msg_index + count]
            msg_index += count
            
            if not quality_messages:
                continue
            
            # Create batch link for this quality using existing bot's logic
            if len(quality_messages) == 1:
                # Single file - create normal link
                msg_id = quality_messages[0].id
                encoded = encode(f"{msg_id}")
                link = f"https://t.me/{client.username}?start={encoded}"
            else:
                # Multiple files - create batch link
                msg_ids = [msg.id for msg in quality_messages]
                first_id = msg_ids[0]
                last_id = msg_ids[-1]
                encoded = encode(f"{first_id}-{last_id}")
                link = f"https://t.me/{client.username}?start=batch_{encoded}"
            
            formatted_links[quality] = link
        
        return formatted_links
        
    except Exception as e:
        logger.error(f"Error generating formatted links: {e}")
        return None
