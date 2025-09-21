@Client.on_message(filters.command("flink_formats") & filters.private & filters.user(ADMINS))
async def manage_flink_formats(client: Client, message: Message):
    """Manage flink formats - bonus feature"""
    user_id = message.from_user.id
    
    current_format = await flink_db.get_user_format(user_id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Edit Format", callback_data="flink_edit_format")],
        [InlineKeyboardButton("🗑️ Delete Format", callback_data="flink_delete_format")],
        [InlineKeyboardButton("📋 Preset Formats", callback_data="flink_preset_formats")]
    ])
    
    format_text = f"**Current Format:**\n`{current_format}`" if current_format else "**No format set**"
    
    await message.reply(
        f"**🔗 FLINK FORMAT MANAGER**\n\n"
        f"{format_text}\n\n"
        f"**Available Actions:**\n"
        f"• Edit your current format\n"
        f"• Delete saved format\n"
        f"• Use preset formats",
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex("^flink_preset_formats$"))
async def show_preset_formats(client: Client, callback_query: CallbackQuery):
    """Show preset format options"""
    presets = {
        "Standard HD": "480p = 1, 720p = 1, 1080p = 1",
        "Multi Quality": "360p = 1, 480p = 2, 720p = 2, 1080p = 2",
        "High Quality": "720p = 2, 1080p = 3, 4K = 1",
        "Mobile Friendly": "360p = 2, 480p = 2, 720p = 1",
        "Premium Pack": "HDRIP = 1, 720p = 2, 1080p = 2, 4K = 1"
    }
    
    keyboard = []
    for name, format_str in presets.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"flink_use_preset_{name}")])
    
    keyboard.append([InlineKeyboardButton("◀️ Back", callback_data="flink_back_to_formats")])
    
    preset_text = "\n".join([f"**{name}:** `{format_str}`" for name, format_str in presets.items()])
    
    await callback_query.edit_message_text(
        f"**📋 PRESET FORMATS**\n\n"
        f"{preset_text}\n\n"
        f"Select a preset to use:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@Client.on_callback_query(filters.regex("^flink_use_preset_"))
async def use_preset_format(client: Client, callback_query: CallbackQuery):
    """Apply preset format"""
    user_id = callback_query.from_user.id
    preset_name = callback_query.data.replace("flink_use_preset_", "")
    
    presets = {
        "Standard HD": "480p = 1, 720p = 1, 1080p = 1",
        "Multi Quality": "360p = 1, 480p = 2, 720p = 2, 1080p = 2",
        "High Quality": "720p = 2, 1080p = 3, 4K = 1",
        "Mobile Friendly": "360p = 2, 480p = 2, 720p = 1",
        "Premium Pack": "HDRIP = 1, 720p = 2, 1080p = 2, 4K = 1"
    }
    
    if preset_name in presets:
        format_str = presets[preset_name]
        await flink_db.save_user_format(user_id, format_str)
        await callback_query.answer("✅ Preset format applied!", show_alert=True)
        
        await callback_query.edit_message_text(
            f"✅ **Format Updated!**\n\n"
            f"**Applied Preset:** {preset_name}\n"
            f"**Format:** `{format_str}`\n\n"
            f"You can now use /flink to generate formatted links."
        )

@Client.on_callback_query(filters.regex("^flink_delete_format$"))
async def delete_user_format_callback(client: Client, callback_query: CallbackQuery):
    """Delete user's saved format"""
    user_id = callback_query.from_user.id
    await flink_db.delete_user_format(user_id)
    await callback_query.answer("🗑️ Format deleted!", show_alert=True)
    
    await callback_query.edit_message_text(
        f"🗑️ **Format Deleted!**\n\n"
        f"Your saved format has been removed.\n"
        f"Use /flink to set a new format."
    )
