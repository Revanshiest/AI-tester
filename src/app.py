import os
import signal
from typing import Final

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters, JobQueue

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
from .texts import START_TEXT, HELP_TEXT, BOT_SHUTTING_DOWN, BOT_STARTED
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
		# Add user to active users
		await session_manager.add_active_user(update.effective_user.id)
		await update.message.reply_text(START_TEXT)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if update.message:
		# Add user to active users
		await session_manager.add_active_user(update.effective_user.id)
		await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)


def build_application(token: str) -> Application:
    app = ApplicationBuilder().token(token).build()
    # Ensure JobQueue is available (avoid PTBUserWarning and enable inactivity timer)
    if getattr(app, "job_queue", None) is None:
        try:
            jq = JobQueue()
            jq.set_application(app)
            jq.start()
            app.job_queue = jq
        except RuntimeError:
            print("[WARN] JobQueue is not available. Inactivity timeout disabled. Install python-telegram-bot[job-queue].")
    return app


async def shutdown_handler(app: Application) -> None:
	"""Unload all models on shutdown."""
	print("Shutting down, notifying users and unloading all models...")
	
	# Notify all active users about shutdown
	active_users = await session_manager.get_active_users()
	if active_users:
		print(f"Notifying {len(active_users)} active users about shutdown...")
		for user_id in active_users:
			try:
				await app.bot.send_message(user_id, BOT_SHUTTING_DOWN)
			except Exception as e:
				print(f"Failed to notify user {user_id}: {e}")
	
	# Unload all models
	loaded_models = await session_manager.get_loaded_models()
	for model_id in loaded_models:
		print(f"Unloading model: {model_id}")
		unload_model(model_id)
	await session_manager.unload_all_models()
	print("All models unloaded.")


async def startup_notify(app: Application) -> None:
	"""Notify all active users about bot startup."""
	active_users = await session_manager.get_active_users()
	if active_users:
		print(f"Notifying {len(active_users)} active users about startup...")
		for user_id in active_users:
			try:
				await app.bot.send_message(user_id, BOT_STARTED)
			except Exception as e:
				print(f"Failed to notify user {user_id}: {e}")


def main() -> None:
	token = get_bot_token()
	app = build_application(token)

	# Register lifecycle callbacks
	app.post_init = startup_notify
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
	app.run_polling()


if __name__ == "__main__":
	main()
