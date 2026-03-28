#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Professional Python Execution Bot
Creator: MAIM DEV
Library: python-telegram-bot v20+
"""

import os
import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ==========================================
# CONFIGURATION & SECURITY
# ==========================================

# ⚠️ REPLACE WITH YOUR BOT TOKEN FROM @BotFather
BOT_TOKEN = "8551142834:AAGQkG5VBxL_b7CJxjUhH1Iax7LoBSjTmX0"

# ⚠️ REPLACE WITH YOUR TELEGRAM USER ID (Get from @userinfobot)
ALLOWED_USER_ID = 6375918223 

# Directory to store uploaded scripts
FILES_DIR = "files"

# Execution Timeout (Seconds)
EXEC_TIMEOUT = 10

# Output Character Limit (Telegram message limit is 4096)
OUTPUT_LIMIT = 4000

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def ensure_directories():
    """Creates necessary directories if they don't exist."""
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)
        logger.info(f"Created directory: {FILES_DIR}")

def check_access(user_id: int) -> bool:
    """Security check to verify allowed user."""
    return user_id == ALLOWED_USER_ID

def get_file_list() -> list:
    """Returns a list of .py files in the storage directory."""
    if not os.path.exists(FILES_DIR):
        return []
    return [f for f in os.listdir(FILES_DIR) if f.endswith(".py")]

async def execute_python_script(filename: str) -> tuple:
    """
    Executes a python script securely with a timeout.
    Returns: (stdout, stderr, return_code)
    """
    file_path = os.path.join(FILES_DIR, filename)
    
    if not os.path.exists(file_path):
        return "", "❌ Error: File not found.", 1

    try:
        # Use asyncio subprocess for non-blocking execution
        process = await asyncio.create_subprocess_exec(
            "python", file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=EXEC_TIMEOUT
            )
            return (
                stdout.decode('utf-8', errors='ignore'),
                stderr.decode('utf-8', errors='ignore'),
                process.returncode
            )
        except asyncio.TimeoutError:
            process.kill()
            return "", f"⚠️ Timeout: Execution exceeded {EXEC_TIMEOUT} seconds.", -1
            
    except Exception as e:
        return "", f"❌ System Error: {str(e)}", 1

def format_output(output: str, is_error: bool = False) -> str:
    """Formats output for Telegram, handling length limits."""
    if not output:
        return "_(No output)_"
    
    if len(output) > OUTPUT_LIMIT:
        truncated_msg = f"... (Truncated, {len(output)} chars total)"
        return f"{output[:OUTPUT_LIMIT]}{truncated_msg}"
    
    # Wrap in code block
    lang = "diff" if is_error else "text"
    return f"```{lang}\n{output}\n```"

# ==========================================
# UI COMPONENTS (KEYBOARDS)
# ==========================================

def build_main_menu():
    """Creates the Dashboard Inline Keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📤 Upload File", callback_data="act_upload"),
            InlineKeyboardButton("📂 My Files", callback_data="act_files"),
        ],
        [
            InlineKeyboardButton("▶️ Run File", callback_data="act_run_select"),
            InlineKeyboardButton("❓ Help", callback_data="act_help"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="act_start"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_file_list_keyboard(files: list):
    """Creates a keyboard listing available files."""
    keyboard = []
    for file in files:
        # Callback data must be < 64 bytes. Filename might be long.
        # We use a prefix to identify action.
        keyboard.append([
            InlineKeyboardButton(f"📄 {file}", callback_data=f"run_{file}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="act_start")])
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# HANDLERS
# ==========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command and main dashboard."""
    user = update.effective_user
    
    if not check_access(user.id):
        await update.message.reply_text(
            "🚫 **Access Denied**\n\nYou are not authorized to use this bot.",
            parse_mode="Markdown"
        )
        return

    welcome_text = (
        f"👋 **Welcome, {user.first_name}!**\n\n"
        f"🤖 **PyExec Bot v2.0**\n"
        f"👨‍💻 **Creator:** MAIM DEV\n\n"
        f"Select an option from the dashboard below:"
    )
    
    # If called via command, send new message. If via callback, edit.
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=welcome_text,
            reply_markup=build_main_menu(),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=welcome_text,
            reply_markup=build_main_menu(),
            parse_mode="Markdown"
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all inline keyboard button presses."""
    query = update.callback_query
    user = query.from_user
    
    # Security Check for all interactions
    if not check_access(user.id):
        await query.answer("🚫 Access Denied", show_alert=True)
        return

    await query.answer() # Acknowledge callback
    data = query.data

    # --- Navigation Logic ---
    if data == "act_start":
        await start_command(update, context)
        
    elif data == "act_help":
        help_text = (
            "❓ **Help & Instructions**\n\n"
            "1️⃣ **Upload File:** Send a `.py` file to the bot.\n"
            "2️⃣ **My Files:** View saved scripts.\n"
            "3️⃣ **Run File:** Execute a saved script.\n\n"
            "⚠️ **Security Notes:**\n"
            "- Execution limit: 10 seconds.\n"
            "- Only `.py` files allowed.\n"
            "- Do not upload malicious code.\n\n"
            f"👨‍💻 **Dev:** MAIM DEV"
        )
        await query.edit_message_text(
            text=help_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="act_start")]]),
            parse_mode="Markdown"
        )

    elif data == "act_upload":
        instr_text = (
            "📤 **Upload Mode**\n\n"
            "Please send a **.py** file now.\n"
            "It will be saved securely to your storage."
        )
        # Store state in user_data to know next message is a file
        context.user_data['awaiting_file'] = True
        await query.edit_message_text(
            text=instr_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Cancel", callback_data="act_start")]]),
            parse_mode="Markdown"
        )

    elif data == "act_files":
        files = get_file_list()
        if not files:
            await query.edit_message_text(
                text="📂 **My Files**\n\nNo files found.\nPlease upload one first.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="act_start")]]),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                text=f"📂 **My Files** ({len(files)})\n\nSelect a file to run:",
                reply_markup=build_file_list_keyboard(files),
                parse_mode="Markdown"
            )

    elif data == "act_run_select":
        # Same as 'act_files' but different context title
        files = get_file_list()
        if not files:
            await query.edit_message_text(
                text="▶️ **Run File**\n\nNo files available.\nUpload a file first.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="act_start")]]),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                text=f"▶️ **Select Script**\n\nChoose a file to execute:",
                reply_markup=build_file_list_keyboard(files),
                parse_mode="Markdown"
            )

    elif data.startswith("run_"):
        filename = data.replace("run_", "")
        await execute_file_flow(query, context, filename)

async def execute_file_flow(query, context, filename):
    """Handles the execution flow with loading states."""
    
    # 1. Show Loading State
    loading_text = f"⏳ **Running:** `{filename}`\n\nPlease wait..."
    await query.edit_message_text(
        text=loading_text,
        parse_mode="Markdown"
    )

    # 2. Execute
    stdout, stderr, code = await execute_python_script(filename)
    
    # 3. Prepare Result
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if code == 0 and not stderr:
        status_emoji = "✅"
        result_text = format_output(stdout)
        caption = f"{status_emoji} **Execution Successful**\n🕒 Time: `{timestamp}`\n\n👇 **Output:**\n{result_text}"
    else:
        status_emoji = "❌"
        # Prefer stderr for errors, else stdout
        error_content = stderr if stderr else stdout
        result_text = format_output(error_content, is_error=True)
        caption = f"{status_emoji} **Execution Failed**\n🕒 Time: `{timestamp}`\n\n👇 **Error:**\n{result_text}"

    # 4. Send Result
    # If output is too long even after truncation logic inside format_output, 
    # we might need to send as file. But format_output handles text limit.
    # If the original output was massive, we send a file.
    
    try:
        await query.edit_message_text(
            text=caption,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Run Again", callback_data=f"run_{filename}")],
                [InlineKeyboardButton("🔙 Dashboard", callback_data="act_start")]
            ]),
            parse_mode="Markdown"
        )
    except Exception as e:
        # Fallback if text is still too long for Telegram API
        await query.edit_message_text(
            text=f"{status_emoji} **Result Ready**\nOutput was too large for text.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Dashboard", callback_data="act_start")]]),
            parse_mode="Markdown"
        )
        # Send output as file
        file_content = stdout if stdout else stderr
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write(file_content)
            
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=open("output.txt", "rb"),
            caption=f"📄 **Full Output Log**\nFile: `{filename}`",
            parse_mode="Markdown"
        )
        os.remove("output.txt")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming document (file) uploads."""
    user = update.effective_user
    
    if not check_access(user.id):
        return

    # Check if user is in 'upload mode'
    if not context.user_data.get('awaiting_file', False):
        return

    document = update.message.document
    file_name = document.file_name

    # Validate Extension
    if not file_name.endswith(".py"):
        await update.message.reply_text(
            "❌ **Invalid File**\n\nOnly `.py` files are allowed.",
            parse_mode="Markdown"
        )
        # Reset state
        context.user_data['awaiting_file'] = False
        # Return to menu
        await start_command(update, context)
        return

    # Download File
    status_msg = await update.message.reply_text("⏳ **Downloading...**")
    
    try:
        file = await context.bot.get_file(document.file_id)
        save_path = os.path.join(FILES_DIR, file_name)
        
        # Handle duplicate names by adding timestamp if needed, 
        # but for simplicity we overwrite or assume unique names.
        # To be safe, let's just save it.
        await file.download_to_drive(save_path)
        
        await status_msg.edit_text(
            f"✅ **Saved Successfully!**\n\n📄 File: `{file_name}`\n\nYou can now run it from **My Files**.",
            parse_mode="Markdown"
        )
        
        # Reset state
        context.user_data['awaiting_file'] = False
        
        # Show menu after short delay
        await asyncio.sleep(2)
        await start_command(update, context)
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        await status_msg.edit_text("❌ **Download Failed**\nPlease try again.")
        context.user_data['awaiting_file'] = False

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Logs errors and notifies admin."""
    logger.error(f"Update {update} caused error {context.error}")
    # In production, you might send this log to a private admin channel

# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    """Start the bot."""
    ensure_directories()
    
    # Build Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Error Handler
    application.add_error_handler(error_handler)
    
    # Start Bot
    logger.info("🚀 Bot started successfully...")
    logger.info(f"👨‍💻 Creator: MAIM DEV")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
