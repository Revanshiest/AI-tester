import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Set


@dataclass
class UserSession:
	user_id: int
	model_id: Optional[str] = None
	# placeholders for future settings/history
	temperature: float = 0.7
	top_p: float = 0.9
	max_tokens: int = 512
	system_prompt: str = ""
	history: list = field(default_factory=list)
	pending_action: Optional[str] = None  # e.g., 'settemp', 'settopp', 'setmax', 'system'


class SessionManager:
	def __init__(self) -> None:
		self._user_sessions: Dict[int, UserSession] = {}
		self._bot_locked_by: Optional[int] = None  # Single user who locked the entire bot
		self._loaded_models: Set[str] = set()  # Track loaded models
		self._active_users: Set[int] = set()  # Track users who have interacted with bot
		self._lock = asyncio.Lock()
		self._users_file = "active_users.json"
		self._load_active_users()

	async def select_model(self, user_id: int, model_id: str) -> tuple[bool, str]:
		async with self._lock:
			# Check if bot is locked by another user
			if self._bot_locked_by is not None and self._bot_locked_by != user_id:
				return False, f"🤖 Бот занят пользователем {self._bot_locked_by}. Попробуйте позже."
			
			# Lock bot for this user
			self._bot_locked_by = user_id
			self._loaded_models.add(model_id)  # Track loaded model
			self._active_users.add(user_id)  # Track active user
			sess = self._user_sessions.get(user_id) or UserSession(user_id=user_id)
			sess.model_id = model_id
			self._user_sessions[user_id] = sess
			return True, f"Модель выбрана: {model_id}"

	async def end_session(self, user_id: int) -> Optional[str]:
		"""End session and return model_id that was unloaded (if any)."""
		async with self._lock:
			sess = self._user_sessions.get(user_id)
			if not sess:
				return None
			model_id = sess.model_id
			
			# Only unlock bot if this user was the one who locked it
			if self._bot_locked_by == user_id:
				self._bot_locked_by = None
				if model_id:
					self._loaded_models.discard(model_id)  # Remove from loaded models
			
			# reset session to defaults
			sess.model_id = None
			sess.pending_action = None
			sess.temperature = 0.7
			sess.top_p = 0.9
			sess.max_tokens = 512
			sess.system_prompt = ""
			sess.history.clear()
			self._user_sessions[user_id] = sess
			return model_id

	async def get_status(self, user_id: int) -> UserSession:
		async with self._lock:
			return self._user_sessions.get(user_id) or UserSession(user_id=user_id)

	async def who_locked_bot(self) -> Optional[int]:
		async with self._lock:
			return self._bot_locked_by

	async def set_pending(self, user_id: int, action: Optional[str]) -> None:
		async with self._lock:
			sess = self._user_sessions.get(user_id) or UserSession(user_id=user_id)
			sess.pending_action = action
			self._user_sessions[user_id] = sess

	async def get_loaded_models(self) -> Set[str]:
		"""Get set of currently loaded models."""
		async with self._lock:
			return self._loaded_models.copy()

	async def unload_all_models(self) -> None:
		"""Unload all tracked models (for shutdown)."""
		async with self._lock:
			self._loaded_models.clear()
			self._bot_locked_by = None

	async def get_active_users(self) -> Set[int]:
		"""Get set of active users (for notifications)."""
		async with self._lock:
			return self._active_users.copy()


	async def is_bot_busy(self) -> bool:
		"""Check if bot is busy (locked by any user)."""
		async with self._lock:
			return self._bot_locked_by is not None

	async def get_busy_info(self) -> Optional[int]:
		"""Get info about who locked the bot."""
		async with self._lock:
			return self._bot_locked_by

	def _load_active_users(self) -> None:
		"""Load active users from file on startup."""
		try:
			if os.path.exists(self._users_file):
				with open(self._users_file, 'r', encoding='utf-8') as f:
					data = json.load(f)
					self._active_users = set(data.get('active_users', []))
					print(f"Loaded {len(self._active_users)} active users from file")
		except Exception as e:
			print(f"Failed to load active users: {e}")

	def _save_active_users(self) -> None:
		"""Save active users to file."""
		try:
			with open(self._users_file, 'w', encoding='utf-8') as f:
				json.dump({'active_users': list(self._active_users)}, f, ensure_ascii=False, indent=2)
		except Exception as e:
			print(f"Failed to save active users: {e}")

	async def add_active_user(self, user_id: int) -> None:
		"""Add user to active users list and save to file."""
		async with self._lock:
			self._active_users.add(user_id)
			self._save_active_users()


# singleton instance
session_manager = SessionManager()
