import asyncio
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
		self._model_locks: Dict[str, int] = {}
		self._loaded_models: Set[str] = set()  # Track loaded models
		self._lock = asyncio.Lock()

	async def select_model(self, user_id: int, model_id: str) -> tuple[bool, str]:
		async with self._lock:
			locked_by = self._model_locks.get(model_id)
			if locked_by is not None and locked_by != user_id:
				return False, "Эта модель уже занята другим пользователем. Попробуйте позже."
			# lock model for this user
			self._model_locks[model_id] = user_id
			self._loaded_models.add(model_id)  # Track loaded model
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
			if model_id and self._model_locks.get(model_id) == user_id:
				self._model_locks.pop(model_id, None)
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

	async def who_locked(self, model_id: str) -> Optional[int]:
		async with self._lock:
			return self._model_locks.get(model_id)

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
			self._model_locks.clear()


# singleton instance
session_manager = SessionManager()
