"""ElevenLabs provider — English voice cloning, TTS, and sound effects."""

from __future__ import annotations

import httpx

from . import (
    AudioResult,
    BaseSFXProvider,
    BaseTTSProvider,
    BaseVoiceCloningProvider,
    VoiceInfo,
)


class ElevenLabsTTSProvider(BaseTTSProvider):
    """ElevenLabs: high-quality English TTS with cloned voices.

    API docs: https://docs.elevenlabs.io/api-reference
    """

    BASE_URL = "https://api.elevenlabs.io"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "elevenlabs"

    @property
    def description(self) -> str:
        return "ElevenLabs — Premium English TTS with voice cloning support. Natural and expressive voices."

    def _headers(self) -> dict[str, str]:
        return {
            "xi-api-key": self.api_key,
        }

    async def speak(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
    ) -> AudioResult:
        """Generate speech with a cloned or preset voice.

        POST /v1/text-to-speech/{voice_id} — JSON body with text, model_id, voice_settings.
        Returns streamed audio bytes (MP3).
        """
        body: dict = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/v1/text-to-speech/{voice_id}",
                headers={
                    **self._headers(),
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json=body,
                timeout=120.0,
            )

            if resp.status_code != 200:
                try:
                    err = resp.json()
                    msg = err.get("detail", {})
                    if isinstance(msg, dict):
                        msg = msg.get("message", resp.text)
                    elif isinstance(msg, list) and msg:
                        msg = str(msg[0])
                except Exception:
                    msg = resp.text
                return AudioResult(status="failed", error=f"ElevenLabs TTS failed (HTTP {resp.status_code}): {msg}")

            audio_data = resp.content
            if not audio_data or len(audio_data) == 0:
                return AudioResult(status="failed", error="ElevenLabs returned empty audio")

            return AudioResult(status="success", audio_data=audio_data)

    async def list_voices(self) -> list[VoiceInfo]:
        """List available voices.

        GET /v1/voices — returns list of all voices (preset + cloned).
        """
        voices: list[VoiceInfo] = []

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/v1/voices",
                headers=self._headers(),
                timeout=30.0,
            )

            if resp.status_code != 200:
                return voices

            data = resp.json()
            items = data.get("voices", [])

            for item in items:
                voice_id = item.get("voice_id", "")
                name = item.get("name", "")
                labels = item.get("labels", {})
                category = item.get("category", "")
                desc_parts = []
                if category:
                    desc_parts.append(f"[{category}]")
                if labels:
                    label_str = ", ".join(f"{k}: {v}" for k, v in labels.items())
                    desc_parts.append(label_str)
                desc = " ".join(desc_parts) if desc_parts else None

                voices.append(VoiceInfo(
                    voice_id=voice_id,
                    name=name,
                    description=desc,
                    provider=self.name,
                ))

        return voices


class ElevenLabsVoiceCloningProvider(BaseVoiceCloningProvider):
    """ElevenLabs voice cloning — add a cloned voice via the API.

    Note: Instant voice cloning (IVC) is available on all paid plans.
    """

    BASE_URL = "https://api.elevenlabs.io"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "xi-api-key": self.api_key,
        }

    async def clone_voice(
        self,
        audio_path: str,
        name: str,
        description: str | None = None,
    ) -> VoiceInfo:
        """Clone a voice from an audio sample.

        POST /v1/voices/add — multipart upload with name, description, and audio files.
        Returns a VoiceInfo with the new voice_id.
        """
        import os

        audio_path_resolved = os.path.expanduser(audio_path)
        if not os.path.isfile(audio_path_resolved):
            raise FileNotFoundError(f"Audio file not found: {audio_path_resolved}")

        filename = os.path.basename(audio_path_resolved)

        with open(audio_path_resolved, "rb") as f:
            audio_bytes = f.read()

        files = {
            "files": (filename, audio_bytes, "audio/mpeg"),
        }
        data: dict[str, str] = {
            "name": name,
        }
        if description:
            data["description"] = description

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/v1/voices/add",
                headers=self._headers(),
                data=data,
                files=files,
                timeout=120.0,
            )

            if resp.status_code != 200:
                try:
                    err = resp.json()
                    msg = err.get("detail", {})
                    if isinstance(msg, dict):
                        msg = msg.get("message", resp.text)
                except Exception:
                    msg = resp.text
                raise RuntimeError(f"ElevenLabs clone_voice failed (HTTP {resp.status_code}): {msg}")

            result = resp.json()
            voice_id = result.get("voice_id", "")
            return VoiceInfo(
                voice_id=voice_id,
                name=name,
                description=description,
                provider="elevenlabs",
            )


class ElevenLabsSFXProvider(BaseSFXProvider):
    """ElevenLabs Sound Effects — generate sound effects from text prompts.

    POST /v1/sound-generation — JSON body with text and optional duration.
    """

    BASE_URL = "https://api.elevenlabs.io"

    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "elevenlabs"

    def _headers(self) -> dict[str, str]:
        return {
            "xi-api-key": self.api_key,
        }

    async def generate_sfx(
        self,
        prompt: str,
        duration: float | None = None,
    ) -> AudioResult:
        """Generate a sound effect from a text description.

        POST /v1/sound-generation — returns audio bytes.
        """
        body: dict = {
            "text": prompt,
        }
        if duration is not None:
            body["duration_seconds"] = duration

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.BASE_URL}/v1/sound-generation",
                headers={
                    **self._headers(),
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json=body,
                timeout=120.0,
            )

            if resp.status_code != 200:
                try:
                    err = resp.json()
                    msg = err.get("detail", {})
                    if isinstance(msg, dict):
                        msg = msg.get("message", resp.text)
                    elif isinstance(msg, list) and msg:
                        msg = str(msg[0])
                except Exception:
                    msg = resp.text
                return AudioResult(status="failed", error=f"ElevenLabs SFX failed (HTTP {resp.status_code}): {msg}")

            audio_data = resp.content
            if not audio_data or len(audio_data) == 0:
                return AudioResult(status="failed", error="ElevenLabs SFX returned empty audio")

            return AudioResult(status="success", audio_data=audio_data)
