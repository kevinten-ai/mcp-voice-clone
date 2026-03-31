"""Fish Audio provider — Best Chinese voice cloning + TTS."""

from __future__ import annotations
import os

import httpx

from . import (
    AudioResult,
    BaseSFXProvider,
    BaseTTSProvider,
    BaseVoiceCloningProvider,
    VoiceInfo,
)


class FishAudioProvider(BaseTTSProvider, BaseVoiceCloningProvider):
    """Fish Audio: high-quality Chinese voice cloning and TTS.

    API docs: https://docs.fish.audio
    """

    BASE_URL = "https://api.fish.audio"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "fish-audio"

    @property
    def description(self) -> str:
        return "Fish Audio — Best Chinese voice cloning & TTS. Clone any voice from a short audio sample."

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
        }

    async def clone_voice(
        self,
        audio_path: str,
        name: str,
        description: str | None = None,
    ) -> VoiceInfo:
        """Clone a voice from an audio sample.

        POST /v1/voices — multipart upload with name, description, and audio file.
        Returns a VoiceInfo with the new voice_id.
        """
        audio_path_resolved = os.path.expanduser(audio_path)
        if not os.path.isfile(audio_path_resolved):
            raise FileNotFoundError(f"Audio file not found: {audio_path_resolved}")

        filename = os.path.basename(audio_path_resolved)

        # Determine content type from extension
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".flac": "audio/flac",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
            ".aac": "audio/aac",
            ".webm": "audio/webm",
        }
        content_type = content_types.get(ext, "audio/mpeg")

        with open(audio_path_resolved, "rb") as f:
            audio_bytes = f.read()

        files = {
            "voices": (filename, audio_bytes, content_type),
        }
        data: dict[str, str] = {
            "visibility": "private",
        }
        if description:
            data["description"] = description
        # Fish Audio uses multipart form: title field for the name, voices for audio
        data["title"] = name

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/model",
                headers=self._headers(),
                data=data,
                files=files,
                timeout=120.0,
            )

            if resp.status_code not in (200, 201):
                try:
                    err = resp.json()
                    msg = err.get("message", err.get("detail", resp.text))
                except Exception:
                    msg = resp.text
                raise RuntimeError(f"Fish Audio clone_voice failed (HTTP {resp.status_code}): {msg}")

            result = resp.json()
            voice_id = result.get("_id", result.get("id", ""))
            return VoiceInfo(
                voice_id=voice_id,
                name=name,
                description=description,
                provider=self.name,
            )

    async def speak(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
    ) -> AudioResult:
        """Generate speech with a cloned or preset voice.

        POST /v1/tts — JSON body with text, reference_id, speed.
        Returns raw audio bytes (MP3).
        """
        body = {
            "text": text,
            "reference_id": voice_id,
            "format": "mp3",
            "mp3_bitrate": 128,
            "normalize": True,
            "latency": "normal",
        }

        # Fish Audio TTS API uses chunk_length and speed differently
        if speed != 1.0:
            body["prosody"] = {"speed": speed}

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/v1/tts",
                headers={
                    **self._headers(),
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=120.0,
            )

            if resp.status_code != 200:
                try:
                    err = resp.json()
                    msg = err.get("message", err.get("detail", resp.text))
                except Exception:
                    msg = resp.text
                return AudioResult(status="failed", error=f"Fish Audio TTS failed (HTTP {resp.status_code}): {msg}")

            audio_data = resp.content
            if not audio_data or len(audio_data) == 0:
                return AudioResult(status="failed", error="Fish Audio returned empty audio")

            return AudioResult(status="success", audio_data=audio_data)

    async def list_voices(self) -> list[VoiceInfo]:
        """List available voices.

        GET /model — returns paginated list of voices.
        """
        voices: list[VoiceInfo] = []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/model",
                headers=self._headers(),
                params={"page_size": 100, "page_number": 1, "title": "", "self": True},
                timeout=30.0,
            )

            if resp.status_code != 200:
                return voices

            data = resp.json()
            items = data.get("items", data) if isinstance(data, dict) else data
            if not isinstance(items, list):
                items = []

            for item in items:
                voice_id = item.get("_id", item.get("id", ""))
                name = item.get("title", item.get("name", ""))
                desc = item.get("description", "")
                voices.append(VoiceInfo(
                    voice_id=voice_id,
                    name=name,
                    description=desc,
                    provider=self.name,
                ))

        return voices
