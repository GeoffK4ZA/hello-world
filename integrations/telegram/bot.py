#!/usr/bin/env python3
"""
Geoff OS - Telegram Interface

A lightweight Telegram bot that forwards commands to Claude Code.
This is the mobile interface to Geoff OS.

Setup:
1. Create bot via @BotFather on Telegram
2. Set TELEGRAM_BOT_TOKEN environment variable
3. Set TELEGRAM_ALLOWED_USERS (your user ID)
4. Run: python bot.py

Commands mirror Claude Code:
/brief - Daily operating brief
/prep <meeting> - Meeting preparation
/task <description> - Capture a task
/status <project> - Project status
/draft <type> - Draft communication
"""

import os
import asyncio
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Telegram bot library
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
except ImportError:
    print("Install: pip install python-telegram-bot")
    exit(1)

# Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = [int(uid) for uid in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if uid]
GEOFF_OS_PATH = Path(__file__).parent.parent  # Root of geoff-os
JOBS_PATH = GEOFF_OS_PATH / "jobs"
ARTEFACTS_PATH = GEOFF_OS_PATH / "artefacts"

# Ensure directories exist
JOBS_PATH.mkdir(exist_ok=True)


def is_authorized(user_id: int) -> bool:
    """Check if user is authorized to use the bot."""
    if not ALLOWED_USERS:
        return True  # No restrictions if not configured
    return user_id in ALLOWED_USERS


def create_job(intent: str, inputs: dict) -> dict:
    """Create a job record."""
    job = {
        "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "timestamp": datetime.now().isoformat(),
        "intent": intent,
        "inputs": inputs,
        "status": "pending",
        "source": "telegram"
    }

    # Save job file
    job_file = JOBS_PATH / f"{job['id']}_{intent}.json"
    job_file.write_text(json.dumps(job, indent=2))

    return job


def run_claude_command(command: str, args: str = "") -> str:
    """
    Execute a Claude Code command and return the result.

    This runs Claude Code in non-interactive mode with the command.
    """
    prompt = f"/{command}"
    if args:
        prompt += f" {args}"

    try:
        # Run claude with the command
        # Using --print to get output without interactive mode
        result = subprocess.run(
            ["claude", "--print", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            cwd=str(GEOFF_OS_PATH)
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"

    except subprocess.TimeoutExpired:
        return "Request timed out. Try a simpler query."
    except FileNotFoundError:
        return "Claude Code CLI not found. Ensure it's installed and in PATH."
    except Exception as e:
        return f"Error executing command: {str(e)}"


def run_claude_query(query: str) -> str:
    """
    Send a free-form query to Claude Code.
    """
    try:
        result = subprocess.run(
            ["claude", "--print", "-p", query],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(GEOFF_OS_PATH)
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"

    except subprocess.TimeoutExpired:
        return "Request timed out. Try a simpler query."
    except Exception as e:
        return f"Error: {str(e)}"


# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("Not authorized.")
        return

    await update.message.reply_text(
        "🤖 *Geoff OS*\n\n"
        "Your AI Chief of Staff is ready.\n\n"
        "*Commands:*\n"
        "/brief - Daily operating brief\n"
        "/prep <meeting> - Meeting preparation\n"
        "/task <description> - Capture a task\n"
        "/status <project> - Project status\n"
        "/draft <type> - Draft communication\n\n"
        "Or just send a message and I'll help.",
        parse_mode="Markdown"
    )


async def brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /brief command."""
    if not is_authorized(update.effective_user.id):
        return

    await update.message.reply_text("⏳ Generating brief...")

    job = create_job("brief", {"source": "telegram"})
    result = run_claude_command("brief")

    # Truncate if too long for Telegram
    if len(result) > 4000:
        result = result[:3997] + "..."

    await update.message.reply_text(result, parse_mode="Markdown")


async def prep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /prep command."""
    if not is_authorized(update.effective_user.id):
        return

    meeting = " ".join(context.args) if context.args else ""
    if not meeting:
        await update.message.reply_text("Usage: /prep <meeting name>")
        return

    await update.message.reply_text(f"⏳ Preparing for: {meeting}...")

    job = create_job("prep", {"meeting": meeting})
    result = run_claude_command("prep", meeting)

    if len(result) > 4000:
        result = result[:3997] + "..."

    await update.message.reply_text(result, parse_mode="Markdown")


async def task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /task command."""
    if not is_authorized(update.effective_user.id):
        return

    description = " ".join(context.args) if context.args else ""
    if not description:
        await update.message.reply_text("Usage: /task <description>")
        return

    await update.message.reply_text("⏳ Capturing task...")

    job = create_job("task", {"description": description})
    result = run_claude_command("task", description)

    await update.message.reply_text(result, parse_mode="Markdown")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    if not is_authorized(update.effective_user.id):
        return

    project = " ".join(context.args) if context.args else "all"

    await update.message.reply_text(f"⏳ Getting status for: {project}...")

    job = create_job("status", {"project": project})
    result = run_claude_command("status", project)

    if len(result) > 4000:
        result = result[:3997] + "..."

    await update.message.reply_text(result, parse_mode="Markdown")


async def draft(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /draft command."""
    if not is_authorized(update.effective_user.id):
        return

    draft_type = " ".join(context.args) if context.args else ""
    if not draft_type:
        await update.message.reply_text(
            "Usage: /draft <type> <context>\n\n"
            "Types: email, slack, update, response, doc"
        )
        return

    await update.message.reply_text("⏳ Drafting...")

    job = create_job("draft", {"type": draft_type})
    result = run_claude_command("draft", draft_type)

    if len(result) > 4000:
        result = result[:3997] + "..."

    await update.message.reply_text(result, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle free-form messages."""
    if not is_authorized(update.effective_user.id):
        return

    query = update.message.text

    await update.message.reply_text("⏳ Thinking...")

    job = create_job("query", {"query": query})
    result = run_claude_query(query)

    if len(result) > 4000:
        result = result[:3997] + "..."

    await update.message.reply_text(result, parse_mode="Markdown")


def main():
    """Start the bot."""
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        print("Get a token from @BotFather on Telegram")
        exit(1)

    print("Starting Geoff OS Telegram Bot...")
    print(f"Authorized users: {ALLOWED_USERS or 'All'}")

    # Create application
    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("brief", brief))
    app.add_handler(CommandHandler("prep", prep))
    app.add_handler(CommandHandler("task", task))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("draft", draft))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling
    print("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
