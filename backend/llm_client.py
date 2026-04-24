import json
import importlib
import os
from pathlib import Path
from urllib import error, request

try:
    genai = importlib.import_module("google.generativeai")
except ModuleNotFoundError:
    genai = None


def _load_local_env_file() -> None:
    """Load .env file once for local runs without requiring python-dotenv."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def call_gemini_chat_api(system_prompt: str, user_prompt: str, timeout: int = 40) -> str:
    """Call Google Gemini API using REST generateContent endpoint.

    Required env vars:
    - GOOGLE_API_KEY
    Optional env vars:
    - GOOGLE_GEMINI_MODEL 
    """
    _load_local_env_file()

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    model = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-3.1-flash-lite-preview").strip()

    if not api_key:
        raise RuntimeError(
            "Missing Gemini config. Please set GOOGLE_API_KEY in .env"
        )

    if genai is not None:
        genai.configure(api_key=api_key)
        model_client = genai.GenerativeModel(model_name=model, system_instruction=system_prompt)
        response = model_client.generate_content(user_prompt)
        text = getattr(response, "text", "")
        if not text:
            raise RuntimeError("Gemini SDK returned empty text")
        return text

    api_url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
        },
    }

    req = request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_text = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"LLM API HTTP error: {exc.code} | {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"LLM API connection error: {exc.reason}") from exc

    data = json.loads(response_text)
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini API returned no candidates")

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise RuntimeError("Gemini API response has no text parts")

    return parts[0].get("text", "")
