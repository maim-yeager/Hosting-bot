#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Professional Python Execution Bot
Creator: MAIM DEV
Library: python-telegram-bot v20+
"""

import os
import sys
import re
import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path
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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8551142834:AAGQkG5VBxL_b7CJxjUhH1Iax7LoBSjTmX0")
ALLOWED_USER_ID = int(os.environ.get("ALLOWED_USER_ID", "6375918223"))
FILES_DIR = Path("files")
EXEC_TIMEOUT = 30  # Increased for package installation
OUTPUT_LIMIT = 4000

# ⚠️ ALLOWED PACKAGES WHITELIST (Security)
ALLOWED_PACKAGES = {
    'aiogram', 'telebot', 'pyTelegramBotAPI',
    'requests', 'httpx', 'aiohttp',
    'pandas', 'numpy', 'matplotlib',
    'beautifulsoup4', 'bs4', 'lxml',
    'selenium', 'playwright',
    'flask', 'fastapi', 'django',
    'pydantic', 'sqlalchemy',
    'pillow', 'pil', 'opencv-python', 'cv2',
    'discord.py', 'discord',
    'youtube_dl', 'yt_dlp',
    'pygame', 'tkinter',
    'json', 'csv', 'sqlite3', 'datetime', 'time',
    'os', 'sys', 'math', 'random', 're',
    'collections', 'itertools', 'functools',
    'typing', 'dataclasses', 'enum',
    'logging', 'hashlib', 'base64', 'uuid',
    'pathlib', 'shutil', 'glob',
    'asyncio', 'threading', 'multiprocessing',
    'subprocess', 'socket', 'ssl',
    'urllib', 'email', 'html', 'xml',
    'unittest', 'pytest',
    # Add more safe packages as needed
}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def ensure_directories():
    FILES_DIR.mkdir(exist_ok=True)
    logger.info(f"✓ Storage directory ready: {FILES_DIR.absolute()}")

def check_access(user_id: int) -> bool:
    return user_id == ALLOWED_USER_ID

def get_file_list() -> list:
    if not FILES_DIR.exists():
        return []
    return sorted([f.name for f in FILES_DIR.iterdir() if f.suffix == ".py"])

def extract_imports(file_path: Path) -> list:
    """Extract import statements from Python file."""
    imports = []
    try:
        content = file_path.read_text(encoding='utf-8')
        
        # Match: import package, from package import ..., import package.subpackage
        patterns = [
            r'^import\s+([\w\.]+)',
            r'^from\s+([\w\.]+)\s+import',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                # Get root package name (e.g., 'requests' from 'requests.api')
                root_pkg = match.split('.')[0]
                if root_pkg not in imports:
                    imports.append(root_pkg)
        
        return imports
    except Exception as e:
        logger.error(f"Error extracting imports: {e}")
        return []

def check_package_installed(package: str) -> bool:
    """Check if a package is already installed."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except:
        return False

async def install_package(package: str) -> tuple:
    """
    Install a package using pip.
    Returns: (success: bool, message: str)
    """
    # Security check
    if package.lower() not in [p.lower() for p in ALLOWED_PACKAGES]:
        return False, f"❌ Package '{package}' is not in the allowed whitelist."
    
    try:
        logger.info(f"📦 Installing package: {package}")
        
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "pip", "install", package, "--quiet",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=60  # 60 seconds for installation
        )
        
        if process.returncode == 0:
            return True, f"✅ Package '{package}' installed successfully."
        else:
            error_msg = stderr.decode('utf-8', errors='ignore').strip()
            return False, f"❌ Failed to install '{package}': {error_msg}"
            
    except asyncio.TimeoutError:
        return False, f"⚠️ Installation timeout for '{package}'."
    except Exception as e:
        return False, f"❌ Installation error: {str(e)}"

async def install_missing_packages(file_path: Path) -> str:
    """
    Check and install missing packages.
    Returns: Status message
    """
    imports = extract_imports(file_path)
    logger.info(f"📋 Found imports: {imports}")
    
    if not imports:
        return "✓ No external imports detected."
    
    status_messages = []
    missing_packages = []
    
    # Check which packages are missing
    for pkg in imports:
        # Skip standard library modules
        if pkg in ALLOWED_PACKAGES and check_package_installed(pkg):
            status_messages.append(f"✓ {pkg} (already installed)")
        elif pkg in ALLOWED_PACKAGES:
            missing_packages.append(pkg)
        else:
            status_messages.append(f"⚠️ {pkg} (not in whitelist)")
    
    # Install missing packages
    if missing_packages:
        status_messages.append("\n📦 **Installing missing packages...**\n")
        
        for pkg in missing_packages:
            success, msg = await install_package(pkg)
            status_messages.append(f"{'✓' if success else '✗'} {msg}")
            
            # Small delay between installations
            await asyncio.sleep(1)
    else:
        status_messages.append("\n✓ All required packages are available.")
    
    return "\n".join(status_messages)

async def execute_python_script(filename: str) -> tuple:
    """Executes a python script with auto package installation."""
    file_path = FILES_DIR / filename
    
    if not file_path.exists():
        return "", "❌ Error: File not found.", 1

    # Step 1: Install missing packages
    install_status = await install_missing_packages(file_path)
    logger.info(f"Installation status: {install_status}")
    
    # Step 2: Execute the script
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable, str(file_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(FILES_DIR)
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=EXEC_TIMEOUT
            )
            return (
                stdout.decode('utf-8', errors='ignore').strip(),
                stderr.decode('utf-8', errors='ignore').strip(),
                process.returncode
            )
        except asyncio.TimeoutError:
            try:
                process.kill()
            except:
                pass
            return "", f"⚠️ Timeout: Execution exceeded {EXEC_TIMEOUT} seconds.", -1
            
    except Exception as e:
        logger.error(f"Execution error: {e}")
        return "", f"❌ System Error: {str(e)}", 1

def format_output(output: str, is_error: bool = False) -> str:
    if not output:
        return "_(No output)_"
    
    if len(output) > OUTPUT_LIMIT:
        truncated_msg = f"\n\n... (Truncated at {OUTPUT_LIMIT} chars, total: {len(output)})"
        return f"```{output[:OUTPUT_LIMIT]}{truncated_msg}```"
    
    lang = "diff" if is_error else "text"
    return f"```{output}```"

# ==========================================
# UI COMPONENTS
# ==========================================

def build_main_menu():
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
    keyboard = []
    for file in files:
        safe_name = file[:50] if len(file) > 50 else file
        keyboard.append([
            InlineKeyboardButton(f"📄 {safe_name}", callback_data=f"run_{file}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="act_start")])
    return InlineKeyboardMarkup(keyboard)

# ==========================================
# HANDLERS
# ==========================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not check_access(user.id):
        if update.callback_query:
            await update.callback_query.answer("🚫 Access Denied", show_alert=True)
        else:
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
    query = update.callback_query
    user = query.from_user
    
    if not check_access(user.id):
        await query.answer("🚫 Access Denied", show_alert=True)
        return

    await query.answer()
    data = query.data

    try:
        if data == "act_start":
            await start_command(update, context)
            
        elif data == "act_help":
            help_text = (
                "❓ **Help & Instructions**\n\n"
                "1️⃣ **Upload File:** Send a `.py` file to the bot.\n"
                "2️⃣ **My Files:** View saved scripts.\n"
                "3️⃣ **Run File:** Execute a saved script.\n\n"
                "⚠️ **Features:**\n"
                f"- Auto-install missing packages\n"
                f"- Execution limit: {EXEC_TIMEOUT} seconds\n"
                "- Only whitelisted packages allowed\n\n"
                "📦 **Supported Packages:**\n"
                "`aiogram`, `requests`, `pandas`, `numpy`,\n"
                "`beautifulsoup4`, `flask`, `fastapi`, etc.\n\n"
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
                "External packages will be auto-installed!"
            )
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
            filename = data.replace("run_", "", 1)
            await execute_file_flow(query, context, filename)

    except Exception as e:
        logger.error(f"Callback error: {e}")
        await query.answer("⚠️ An error occurred", show_alert=True)

async def execute_file_flow(query, context, filename):
    """Handles the execution flow with loading states."""
    
    loading_text = f"⏳ **Running:** `{filename}`\n\n📦 Checking dependencies...\nPlease wait..."
    await query.edit_message_text(
        text=loading_text,
        parse_mode="Markdown"
    )

    stdout, stderr, code = await execute_python_script(filename)
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if code == 0 and not stderr:
        status_emoji = "✅"
        result_text = format_output(stdout)
        caption = f"{status_emoji} **Execution Successful**\n🕒 Time: `{timestamp}`\n\n👇 **Output:**\n{result_text}"
    else:
        status_emoji = "❌"
        error_content = stderr if stderr else stdout
        result_text = format_output(error_content, is_error=True)
        caption = f"{status_emoji} **Execution Failed**\n🕒 Time: `{timestamp}`\n\n👇 **Error:**\n{result_text}"

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
        logger.warning(f"Message too long, sending as file: {e}")
        await query.edit_message_text(
            text=f"{status_emoji} **Result Ready**\nOutput was too large for text.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Dashboard", callback_data="act_start")]]),
            parse_mode="Markdown"
        )
        
        file_content = stdout if stdout else stderr
        output_file = FILES_DIR / "output.txt"
        output_file.write_text(file_content, encoding="utf-8")
            
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=open(output_file, "rb"),
            caption=f"📄 **Full Output Log**\nFile: `{filename}`",
            parse_mode="Markdown"
        )
        output_file.unlink(missing_ok=True)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if not check_access(user.id):
        return

    if not context.user_data.get('awaiting_file', False):
        return

    document = update.message.document
    file_name = document.file_name

    if not file_name.endswith(".py"):
        await update.message.reply_text(
            "❌ **Invalid File**\n\nOnly `.py` files are allowed.",
            parse_mode="Markdown"
        )
        context.user_data['awaiting_file'] = False
        await start_command(update, context)
        return

    status_msg = await update.message.reply_text("⏳ **Downloading...**")
    
    try:
        file = await context.bot.get_file(document.file_id)
        save_path = FILES_DIR / file_name
        await file.download_to_drive(str(save_path))
        
        await status_msg.edit_text(
            f"✅ **Saved Successfully!**\n\n📄 File: `{file_name}`\n\nYou can now run it from **My Files**.",
            parse_mode="Markdown"
        )
        
        context.user_data['awaiting_file'] = False
        await asyncio.sleep(2)
        await start_command(update, context)
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        await status_msg.edit_text("❌ **Download Failed**\nPlease try again.")
        context.user_data['awaiting_file'] = False

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# ==========================================
# MAIN EXECUTION
# ==========================================

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN not configured! Set BOT_TOKEN environment variable.")
        sys.exit(1)
    
    if ALLOWED_USER_ID == 123456789:
        logger.warning("⚠️ Using default ALLOWED_USER_ID! Change it for security.")
    
    ensure_directories()
    
    logger.info("🚀 Initializing bot...")
    logger.info(f"👨‍💻 Creator: MAIM DEV")
    logger.info(f"🔐 Allowed User ID: {ALLOWED_USER_ID}")
    logger.info(f"📦 Auto-install: Enabled")
    
    try:
        application = Application.builder().token(BOT_TOKEN).build()
        
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
        application.add_error_handler(error_handler)
        
        logger.info("✅ Bot started successfully!")
        logger.info("📡 Polling for updates...")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
