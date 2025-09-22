import os
import signal
import sys
from typing import Final

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters

from .commands import (
	cmd_pingollama,
	cmd_omodels,
	cb_select_model,
	cmd_status,
	cmd_end,
	cmd_settemp,
	cmd_settopp,
	cmd_setmax,
	cmd_system,
	cmd_clearhistory,
	cmd_cancel,
	handle_text,
)
from .texts import START_TEXT, HELP_TEXT
from .session import session_manager
from .ollama_client import unload_model


def load_env() -> None:
	load_dotenv()


def get_bot_token() -> str:
	load_env()
	bot_token: Final[str | None] = os.getenv("TELEGRAM_BOT_TOKEN")
	if not bot_token:
		raise RuntimeError(
			"TELEGRAM_BOT_TOKEN is not set. Create a .env file or set the environment variable."
		)
	return bot_token


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if update.message:
		await update.message.reply_text(START_TEXT)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if update.message:
		await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


def build_application(token: str) -> Application:
	return ApplicationBuilder().token(token).build()


async def shutdown_handler(app: Application) -> None:
	"""Unload all models on shutdown."""
	print("Shutting down, unloading all models...")
	loaded_models = await session_manager.get_loaded_models()
	for model_id in loaded_models:
		print(f"Unloading model: {model_id}")
		unload_model(model_id)
	await session_manager.unload_all_models()
	print("All models unloaded.")


def signal_handler(signum, frame):
	"""Handle shutdown signals."""
	print(f"\nReceived signal {signum}, shutting down...")
	sys.exit(0)


def main() -> None:
	token = get_bot_token()
	app = build_application(token)

	# Register shutdown handlers
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGTERM, signal_handler)
	
	# Register shutdown callback
	app.post_shutdown = shutdown_handler

	app.add_handler(CommandHandler("start", cmd_start))
	app.add_handler(CommandHandler("help", cmd_help))
	app.add_handler(CommandHandler("omodels", cmd_omodels))
	app.add_handler(CallbackQueryHandler(cb_select_model, pattern=r"^select:"))
	app.add_handler(CommandHandler("status", cmd_status))
	app.add_handler(CommandHandler("system", cmd_system))
	app.add_handler(CommandHandler("end", cmd_end))
	app.add_handler(CommandHandler("clearhistory", cmd_clearhistory))
	app.add_handler(CommandHandler("cancel", cmd_cancel))
	app.add_handler(CommandHandler("settemp", cmd_settemp))
	app.add_handler(CommandHandler("settopp", cmd_settopp))
	app.add_handler(CommandHandler("setmax", cmd_setmax))
	app.add_handler(CommandHandler("pingollama", cmd_pingollama))
	app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))

	print("Bot is starting... Press Ctrl+C to stop.")
	try:
		app.run_polling()
	except KeyboardInterrupt:
		print("\nShutdown requested by user...")
	finally:
		# Ensure cleanup on any exit
		import asyncio
		asyncio.run(shutdown_handler(app))


if __name__ == "__main__":
	main()
