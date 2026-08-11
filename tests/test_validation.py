import asyncio

import pytest

from voice_clone import providers, server
from voice_clone.providers import AudioResult
from voice_clone.providers import elevenlabs


def test_save_audio_writes_new_mp3(tmp_path):
    output = tmp_path / "speech.mp3"

    result = server._save_audio_bytes(
        b"audio", str(tmp_path), "speech", output_path=str(output)
    )

    assert result == str(output)
    assert output.read_bytes() == b"audio"


def test_save_audio_refuses_existing_output(tmp_path):
    output = tmp_path / "speech.mp3"
    output.write_bytes(b"keep-me")

    with pytest.raises(FileExistsError, match="already exists"):
        server._save_audio_bytes(
            b"replacement", str(tmp_path), "speech", output_path=str(output)
        )

    assert output.read_bytes() == b"keep-me"


def test_save_audio_requires_mp3_extension(tmp_path):
    with pytest.raises(ValueError, match=r"\.mp3"):
        server._save_audio_bytes(
            b"audio", str(tmp_path), "speech", output_path=str(tmp_path / "speech.wav")
        )


def test_save_audio_rejects_oversized_provider_result(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "MAX_AUDIO_OUTPUT_BYTES", 4)

    with pytest.raises(ValueError, match="too large"):
        server._save_audio_bytes(b"12345", str(tmp_path), "speech")


def test_load_audio_sample_validates_extension_and_size(tmp_path, monkeypatch):
    unsupported = tmp_path / "sample.txt"
    unsupported.write_bytes(b"audio")
    with pytest.raises(ValueError, match="Unsupported audio sample format"):
        providers.load_audio_sample(str(unsupported))

    sample = tmp_path / "sample.wav"
    sample.write_bytes(b"12345")
    monkeypatch.setattr(providers, "MAX_CLONE_SAMPLE_BYTES", 4)
    with pytest.raises(ValueError, match="too large"):
        providers.load_audio_sample(str(sample))


def test_load_audio_sample_reports_matching_content_type(tmp_path):
    sample = tmp_path / "sample.wav"
    sample.write_bytes(b"audio")

    filename, data, content_type = providers.load_audio_sample(str(sample))

    assert filename == "sample.wav"
    assert data == b"audio"
    assert content_type == "audio/wav"


def test_load_audio_sample_rechecks_actual_read_size(tmp_path, monkeypatch):
    sample = tmp_path / "sample.wav"
    sample.write_bytes(b"1234")
    monkeypatch.setattr(providers, "MAX_CLONE_SAMPLE_BYTES", 5)
    original_validate = providers.validate_audio_sample_path

    def grow_after_validation(audio_path):
        result = original_validate(audio_path)
        sample.write_bytes(b"123456")
        return result

    monkeypatch.setattr(providers, "validate_audio_sample_path", grow_after_validation)

    with pytest.raises(ValueError, match="too large"):
        providers.load_audio_sample(str(sample))


def test_limited_stream_rejects_oversized_response():
    class FakeResponse:
        async def aiter_bytes(self):
            yield b"123"
            yield b"456"

    with pytest.raises(ValueError, match="too large"):
        asyncio.run(providers.read_limited_stream(FakeResponse(), 5))


def test_elevenlabs_sends_speed_and_streams_audio(monkeypatch):
    captured = {}

    class FakeResponse:
        status_code = 200
        headers = {"content-type": "audio/mpeg"}

        async def aiter_bytes(self):
            yield b"audio"

    class FakeStream:
        async def __aenter__(self):
            return FakeResponse()

        async def __aexit__(self, *_args):
            return None

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        def stream(self, method, url, **kwargs):
            captured.update(method=method, url=url, kwargs=kwargs)
            return FakeStream()

    monkeypatch.setattr(elevenlabs.httpx, "AsyncClient", FakeClient)
    provider = elevenlabs.ElevenLabsTTSProvider("test-key")

    result = asyncio.run(provider.speak("hello", "voice-id", speed=1.2))

    assert result.status == "success"
    assert result.audio_data == b"audio"
    assert captured["kwargs"]["json"]["voice_settings"]["speed"] == 1.2


def test_speak_rejects_existing_output_before_provider_call(tmp_path, monkeypatch):
    output = tmp_path / "speech.mp3"
    output.write_bytes(b"keep-me")

    class FakeProvider:
        name = "fake"
        description = "fake provider"
        called = False

        async def speak(self, *_args, **_kwargs):
            self.called = True
            return AudioResult(status="success", audio_data=b"replacement")

    fake = FakeProvider()
    monkeypatch.setattr(server, "get_all_tts", lambda: {"fake": fake})

    result = asyncio.run(
        server.handle_call_tool(
            "speak",
            {
                "text": "hello",
                "voice_id": "voice",
                "provider": "fake",
                "output_path": str(output),
            },
        )
    )

    assert "already exists" in result[0].text
    assert fake.called is False
    assert output.read_bytes() == b"keep-me"


def test_sfx_rejects_invalid_duration_before_provider_call(tmp_path, monkeypatch):
    class FakeProvider:
        name = "fake"
        called = False

        async def generate_sfx(self, *_args, **_kwargs):
            self.called = True
            return AudioResult(status="success", audio_data=b"audio")

    fake = FakeProvider()
    monkeypatch.setattr(server, "get_all_sfx", lambda: {"fake": fake})

    result = asyncio.run(
        server.handle_call_tool(
            "generate_sfx",
            {
                "prompt": "rain",
                "duration": 31,
                "output_path": str(tmp_path / "sfx.mp3"),
            },
        )
    )

    assert "duration" in result[0].text
    assert fake.called is False


def test_tool_schemas_publish_runtime_limits(monkeypatch):
    class FakeTTS:
        name = "fake"
        description = "fake provider"

    class FakeSFX:
        name = "fake"

    monkeypatch.setattr(server, "get_all_tts", lambda: {"fake": FakeTTS()})
    monkeypatch.setattr(server, "get_all_sfx", lambda: {"fake": FakeSFX()})

    tools = {tool.name: tool for tool in asyncio.run(server.handle_list_tools())}
    speak = tools["speak"].inputSchema["properties"]
    sfx = tools["generate_sfx"].inputSchema["properties"]

    assert speak["text"]["maxLength"] == server.MAX_TTS_TEXT_CHARS
    assert speak["speed"]["minimum"] == server.MIN_SPEECH_SPEED
    assert speak["speed"]["maximum"] == server.MAX_SPEECH_SPEED
    assert sfx["duration"]["minimum"] == server.MIN_SFX_DURATION
    assert sfx["duration"]["maximum"] == server.MAX_SFX_DURATION
