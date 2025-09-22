from typing import Optional, List, Dict, Any, Iterator
import os
import time
import subprocess
import requests


def get_ollama_base_url() -> str:
	return os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")


def ping_ollama(timeout: float = 2.0) -> Optional[str]:
	base = get_ollama_base_url()
	try:
		resp = requests.get(f"{base}/api/version", timeout=timeout)
		if resp.status_code == 200:
			data = resp.json()
			return str(data)
		return None
	except Exception:
		return None


def list_ollama_models(timeout: float = 3.0) -> List[str]:
	base = get_ollama_base_url()
	try:
		resp = requests.get(f"{base}/api/tags", timeout=timeout)
		resp.raise_for_status()
		data = resp.json() or {}
		items = data.get("models", []) or []
		return [str(it.get("name", "")).strip() for it in items if it.get("name")]
	except Exception:
		return []


def chat_with_model(
	model: str,
	messages: List[Dict[str, str]],
	*,
	temperature: float = 0.7,
	top_p: float = 0.9,
	num_predict: int = 512,
	timeout: float = 120.0,
) -> Dict[str, Any]:
	"""Non-streaming chat request to Ollama."""
	base = get_ollama_base_url()
	payload = {
		"model": model,
		"messages": messages,
		"stream": False,
		"options": {
			"temperature": temperature,
			"top_p": top_p,
			"num_predict": num_predict,
		},
	}
	try:
		resp = requests.post(
			f"{base}/api/chat",
			json=payload,
			timeout=timeout,
		)
		resp.raise_for_status()
		data = resp.json() or {}
		message = (data.get("message") or {})
		text = message.get("content") or data.get("response")
		if not isinstance(text, str):
			text = str(text) if text is not None else ""
		return {"ok": True, "text": text, "error": None}
	except Exception as e:
		return {"ok": False, "text": None, "error": str(e)}


def stream_chat_with_model(
	model: str,
	messages: List[Dict[str, str]],
	*,
	temperature: float = 0.7,
	top_p: float = 0.9,
	num_predict: int = 512,
	timeout: float = 300.0,
) -> Iterator[str]:
	"""Streaming chat request to Ollama. Yields text deltas as they arrive.

	This uses the streaming API (stream=true) and yields incremental content.
	"""
	base = get_ollama_base_url()
	payload = {
		"model": model,
		"messages": messages,
		"stream": True,
		"options": {
			"temperature": temperature,
			"top_p": top_p,
			"num_predict": num_predict,
		},
	}
	with requests.post(f"{base}/api/chat", json=payload, stream=True, timeout=timeout) as resp:
		resp.raise_for_status()
		for line in resp.iter_lines(decode_unicode=True):
			if not line:
				continue
			try:
				data = requests.utils.json.loads(line)
				msg = (data.get("message") or {})
				chunk = msg.get("content") or data.get("response") or ""
				if chunk:
					yield str(chunk)
			except Exception:
				# ignore malformed lines
				continue


def warm_up_model(model: str, timeout: float = 180.0) -> Dict[str, Any]:
	"""Trigger a tiny non-stream generation to load model into memory."""
	base = get_ollama_base_url()
	payload = {
		"model": model,
		"prompt": "ok",
		"stream": False,
		"options": {
			"num_predict": 1,
			"temperature": 0.0,
		},
	}
	try:
		resp = requests.post(f"{base}/api/generate", json=payload, timeout=timeout)
		resp.raise_for_status()
		return {"ok": True}
	except Exception as e:
		return {"ok": False, "error": str(e)}


def stop_model_cli(model: str, timeout: float = 30.0) -> Dict[str, Any]:
	"""Fallback: call `ollama stop <model>` via CLI."""
	try:
		proc = subprocess.run([
			"ollama", "stop", model
		], check=False, capture_output=True, text=True, timeout=timeout)
		if proc.returncode == 0:
			return {"ok": True}
		return {"ok": False, "error": proc.stderr.strip() or proc.stdout.strip()}
	except Exception as e:
		return {"ok": False, "error": str(e)}


def unload_model(model: str, timeout: float = 60.0) -> Dict[str, Any]:
	"""Unload a model using the Ollama CLI stop command (requested behavior)."""
	return stop_model_cli(model, timeout=timeout)
