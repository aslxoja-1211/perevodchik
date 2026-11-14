import pytest
from app.audio.pcm_utils import (
    compute_pcm16_rms,
    ensure_audio_filename_and_bytes,
    estimate_pcm16_duration_ms,
    pcm16_to_wav,
)


def test_pcm16_to_wav_valid():
    # 100 samples of silence (200 bytes)
    pcm = b"\x00\x00" * 100
    wav = pcm16_to_wav(pcm, sample_rate=16000, channels=1, sample_width=2)
    assert wav.startswith(b"RIFF")
    assert b"WAVE" in wav
    assert len(wav) > 200


def test_pcm16_to_wav_empty():
    with pytest.raises(ValueError):
        pcm16_to_wav(b"")


def test_compute_pcm16_rms():
    silence = b"\x00\x00" * 200
    assert compute_pcm16_rms(silence) == 0.0

    # Max amplitude
    loud = b"\xff\x7f" * 100
    rms = compute_pcm16_rms(loud)
    assert rms > 0.95


def test_ensure_audio_filename_and_bytes():
    pcm = b"\x00\x00" * 50
    fname, payload, ctype = ensure_audio_filename_and_bytes(pcm, "audio/pcm")
    assert fname == "audio.wav"
    assert ctype == "audio/wav"
    assert payload.startswith(b"RIFF")


def test_estimate_pcm16_duration_ms():
    # 16000 samples / sec * 2 bytes/sample = 32000 bytes/sec
    # 32000 bytes = 1000 ms
    assert estimate_pcm16_duration_ms(32000, sample_rate=16000) == 1000.0
