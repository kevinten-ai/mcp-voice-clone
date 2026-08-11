"""Fish Audio provider — Best Chinese voice cloning + TTS."""

from __future__ import annotations

import httpx

from . import (
    AudioResult,
    BaseTTSProvider,
    BaseVoiceCloningProvider,
    MAX_AUDIO_RESPONSE_BYTES,
    VoiceInfo,
    load_audio_sample,
    read_error_text,
    read_limited_json,
    read_limited_stream,
    validate_audio_content_type,
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

        POST /model — multipart upload with name, description, and audio file.
        Returns a VoiceInfo with the new voice_id.
        """
        filename, audio_bytes, content_type = load_audio_sample(audio_path)

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
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/model",
                headers=self._headers(),
                data=data,
                files=files,
                timeout=120.0,
            ) as resp:
                try:
                    result = await read_limited_json(resp)
                except ValueError as e:
                    raise RuntimeError(
                        f"Fish Audio clone_voice failed (HTTP {resp.status_code}): {e}"
                    ) from e

            if resp.status_code not in (200, 201):
                if isinstance(result, dict):
                    msg = result.get("message", result.get("detail", "unknown error"))
                else:
                    msg = result
                raise RuntimeError(
                    f"Fish Audio clone_voice failed (HTTP {resp.status_code}): {str(msg)[:1_000]}"
                )

            if not isinstance(result, dict):
                raise RuntimeError(
                    "Fish Audio clone_voice returned an invalid response"
                )
            voice_id = result.get("_id", result.get("id", ""))
            if not isinstance(voice_id, str) or not voice_id:
                raise RuntimeError("Fish Audio clone_voice returned no voice ID")
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
            async with client.stream(
                "POST",
                f"{self.BASE_URL}/v1/tts",
                headers={
                    **self._headers(),
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=120.0,
            ) as resp:
                if resp.status_code != 200:
                    msg = await read_error_text(resp)
                    return AudioResult(
                        status="failed",
                        error=f"Fish Audio TTS failed (HTTP {resp.status_code}): {msg}",
                    )

                try:
                    validate_audio_content_type(resp.headers.get("content-type"))
                    audio_data = await read_limited_stream(
                        resp, MAX_AUDIO_RESPONSE_BYTES
                    )
                except ValueError as e:
                    return AudioResult(status="failed", error=str(e))
                if not audio_data:
                    return AudioResult(
                        status="failed", error="Fish Audio returned empty audio"
                    )

            return AudioResult(status="success", audio_data=audio_data)

    async def list_voices(self) -> list[VoiceInfo]:
        """List available voices.

        GET /model — returns paginated list of voices.
        """
        voices: list[VoiceInfo] = []

        async with httpx.AsyncClient() as client:
            async with client.stream(
                "GET",
                f"{self.BASE_URL}/model",
                headers=self._headers(),
                params={"page_size": 100, "page_number": 1, "title": "", "self": True},
                timeout=30.0,
            ) as resp:
                if resp.status_code != 200:
                    return voices
                try:
                    data = await read_limited_json(resp)
                except ValueError:
                    return voices
                items = data.get("items", data) if isinstance(data, dict) else data
            if not isinstance(items, list):
                items = []

            for item in items:
                if not isinstance(item, dict):
                    continue
                voice_id = item.get("_id", item.get("id", ""))
                name = item.get("title", item.get("name", ""))
                desc = item.get("description", "")
                voices.append(
                    VoiceInfo(
                        voice_id=voice_id,
                        name=name,
                        description=desc,
                        provider=self.name,
                    )
                )

        return voices
