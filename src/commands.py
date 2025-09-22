from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from .ollama_client import ping_ollama, list_ollama_models, chat_with_model, stream_chat_with_model, warm_up_model, unload_model, stop_model_cli
from .session import session_manager
from .constants import MAX_TELEGRAM_CHUNK, MAX_HISTORY_MESSAGES, INACTIVITY_TIMEOUT_SECONDS
from . import texts


# --- Inactivity timeout helpers ---
async def _on_inactivity(context: ContextTypes.DEFAULT_TYPE) -> None:
	job = context.job
	if not job:
		return
	data = job.data or {}
	user_id = data.get("user_id")
	chat_id = data.get("chat_id")
	if user_id is None or chat_id is None:
		return
	# End the session and unload model
	sess = await session_manager.get_status(user_id)
	if sess.model_id:
		# Unload model on timeout
		unload_model(sess.model_id)
	model_id = await session_manager.end_session(user_id)
	try:
		await context.bot.send_message(chat_id, texts.INACTIVITY_ENDED)
	except Exception:
		pass


def _job_name(user_id: int) -> str:
	return f"inactivity-{user_id}"


async def _reset_inactivity_timer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	jq = context.application.job_queue if context.application else None
	if not jq:
		return
	user_id = update.effective_user.id if update.effective_user else None
	chat_id = update.effective_chat.id if update.effective_chat else None
	if user_id is None or chat_id is None:
		return
	for j in jq.get_jobs_by_name(_job_name(user_id)):
		j.schedule_removal()
	jq.run_once(
		_on_inactivity,
		when=INACTIVITY_TIMEOUT_SECONDS,
		data={"user_id": user_id, "chat_id": chat_id},
		name=_job_name(user_id),
	)


async def _cancel_inactivity_timer(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
	jq = context.application.job_queue if context.application else None
	if not jq:
		return
	for j in jq.get_jobs_by_name(_job_name(user_id)):
		j.schedule_removal()


async def cmd_pingollama(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	info = ping_ollama()
	msg = texts.OLLAMA_DOWN if info is None else f"Оllama доступна: {info}"
	if update.message:
		await update.message.reply_text(msg)


async def cmd_omodels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	ids = list_ollama_models()
	if not ids:
		if update.message:
			await update.message.reply_text("Ollama не вернула список моделей. Убедитесь, что сервис запущен и модели установлены.")
		return
	keyboard = [[InlineKeyboardButton(text=mid, callback_data=f"select:{mid}")] for mid in ids]
	markup = InlineKeyboardMarkup(keyboard)
	if update.message:
		await update.message.reply_text("Выберите модель:", reply_markup=markup)


async def cb_select_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	query = update.callback_query
	if not query:
		return
	data = query.data or ""
	if not data.startswith("select:"):
		await query.answer()
		return
	model_id = data[len("select:"):]
	user_id = query.from_user.id if query.from_user else 0
	ok, msg = await session_manager.select_model(user_id, model_id)
	await query.answer(text=msg, show_alert=not ok)
	try:
		await query.edit_message_text(f"{msg}")
	except Exception:
		pass
	if ok:
		await _reset_inactivity_timer(update, context)
		await query.message.reply_text("Загружаю модель в память...")
		result = warm_up_model(model_id)
		if result.get("ok"):
			await query.message.reply_text("Модель готова к работе.")
		else:
			await query.message.reply_text(f"Не удалось подготовить модель: {result.get('error')}")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message:
		return
	sess = await session_manager.get_status(update.effective_user.id)
	locked_by = await session_manager.who_locked(sess.model_id) if sess.model_id else None
	lines = ["Статус:"]
	lines.append(f"Текущая модель: {sess.model_id or '—'}")
	if sess.model_id:
		lines.append(f"Занята пользователем: {locked_by if locked_by is not None else 'нет'}")
	lines.append(f"temperature={sess.temperature}, top_p={sess.top_p}, max_tokens={sess.max_tokens}")
	lines.append(texts.STATUS_SYSTEM_SET if sess.system_prompt else texts.STATUS_SYSTEM_NOT_SET)
	await update.message.reply_text("\n".join(lines))
	if sess.model_id:
		await _reset_inactivity_timer(update, context)


async def cmd_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message:
		return
	sess = await session_manager.get_status(update.effective_user.id)
	if sess.model_id:
		await update.message.reply_text("Выгружаю модель из памяти...")
		res = unload_model(sess.model_id)
		if not res.get("ok"):
			# Fallback to CLI stop
			cli = stop_model_cli(sess.model_id)
			if cli.get("ok"):
				await update.message.reply_text("Модель выгружена (CLI).")
			else:
				await update.message.reply_text(f"Не удалось выгрузить модель: {res.get('error') or cli.get('error')}")
		else:
			await update.message.reply_text("Модель выгружена.")
	model_id = await session_manager.end_session(update.effective_user.id)
	await _cancel_inactivity_timer(context, update.effective_user.id)
	await update.message.reply_text("Сессия завершена. Модель и настройки сброшены.")


async def cmd_clearhistory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message:
		return
	sess = await session_manager.get_status(update.effective_user.id)
	sess.history.clear()
	await update.message.reply_text("История диалога очищена (модель не перезапускалась).")
	if sess.model_id:
		await _reset_inactivity_timer(update, context)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message:
		return
	await session_manager.set_pending(update.effective_user.id, None)
	await update.message.reply_text("Ожидание ввода отменено.")


async def cmd_settemp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message:
		return
	await session_manager.set_pending(update.effective_user.id, "settemp")
	await update.message.reply_text(texts.PROMPT_ENTER_TEMP)
	await _reset_inactivity_timer(update, context)


async def cmd_settopp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message:
		return
	await session_manager.set_pending(update.effective_user.id, "settopp")
	await update.message.reply_text(texts.PROMPT_ENTER_TOPP)
	await _reset_inactivity_timer(update, context)


async def cmd_setmax(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message:
		return
	await session_manager.set_pending(update.effective_user.id, "setmax")
	await update.message.reply_text(texts.PROMPT_ENTER_MAX)
	await _reset_inactivity_timer(update, context)


async def cmd_system(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message:
		return
	await session_manager.set_pending(update.effective_user.id, "system")
	await update.message.reply_text(texts.PROMPT_ENTER_SYSTEM)
	await _reset_inactivity_timer(update, context)


def _chunk_text(text: str, size: int = MAX_TELEGRAM_CHUNK):
	for i in range(0, len(text), size):
		yield text[i:i+size]


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not update.message:
		return
	text = (update.message.text or "").strip()
	sess = await session_manager.get_status(update.effective_user.id)
	if sess.pending_action:
		if sess.pending_action == "settemp":
			try:
				val = float(text.replace(",", "."))
				if not (0.0 <= val <= 2.0):
					raise ValueError
			except ValueError:
				await update.message.reply_text(texts.ERR_TEMP)
				return
			sess.temperature = val
			await session_manager.set_pending(update.effective_user.id, None)
			await update.message.reply_text(f"temperature = {val}")
			await _reset_inactivity_timer(update, context)
			return
		if sess.pending_action == "settopp":
			try:
				val = float(text.replace(",", "."))
				if not (0.0 <= val <= 1.0):
					raise ValueError
			except ValueError:
				await update.message.reply_text(texts.ERR_TOPP)
				return
			sess.top_p = val
			await session_manager.set_pending(update.effective_user.id, None)
			await update.message.reply_text(f"top_p = {val}")
			await _reset_inactivity_timer(update, context)
			return
		if sess.pending_action == "setmax":
			try:
				val = int(text)
				if val <= 0:
					raise ValueError
			except ValueError:
				await update.message.reply_text(texts.ERR_MAX)
				return
			sess.max_tokens = val
			await session_manager.set_pending(update.effective_user.id, None)
			await update.message.reply_text(f"max_tokens = {val}")
			await _reset_inactivity_timer(update, context)
			return
		if sess.pending_action == "system":
			sess.system_prompt = text
			await session_manager.set_pending(update.effective_user.id, None)
			await update.message.reply_text("Системный промпт задан.")
			await _reset_inactivity_timer(update, context)
			return

	if not sess.model_id:
		await update.message.reply_text(texts.NEED_SELECT_MODEL)
		return

	messages = []
	if sess.system_prompt:
		messages.append({"role": "system", "content": sess.system_prompt})
	for role, content in sess.history[-(MAX_HISTORY_MESSAGES - 1):]:
		messages.append({"role": role, "content": content})
	messages.append({"role": "user", "content": text})

	await update.message.chat.send_action("typing")
	resp = chat_with_model(
		sess.model_id,
		messages,
		temperature=sess.temperature,
		top_p=sess.top_p,
		num_predict=sess.max_tokens,
	)
	if not resp.get("ok"):
		await update.message.reply_text(f"Ошибка запроса к модели: {resp.get('error')}")
		return

	answer = resp.get("text") or ""
	sess.history.append(("user", text))
	sess.history.append(("assistant", answer))
	if len(sess.history) > MAX_HISTORY_MESSAGES:
		sess.history = sess.history[-MAX_HISTORY_MESSAGES:]

	for chunk in _chunk_text(answer):
		await update.message.reply_text(chunk)
	await _reset_inactivity_timer(update, context)
