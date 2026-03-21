"""Text-to-Speech using Google TTS (free, reliable)."""

import asyncio
import io
import logging
import tempfile

from gtts import gTTS

logger = logging.getLogger(__name__)


async def text_to_speech(text: str) -> bytes | None:
    """Convert text to OGG audio bytes for Telegram voice message."""
    try:
        # gTTS is synchronous, run in executor
        loop = asyncio.get_event_loop()
        audio_bytes = await loop.run_in_executor(None, _generate_audio, text)
        if audio_bytes:
            logger.info("TTS generated: %d bytes", len(audio_bytes))
        return audio_bytes
    except Exception as e:
        logger.error("TTS error: %s", e, exc_info=True)
        return None


def _generate_audio(text: str) -> bytes | None:
    """Generate OGG audio from text (runs in thread)."""
    import os

    # Generate MP3 with gTTS
    tts = gTTS(text=text, lang="ru")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
        tmp_mp3_path = tmp_mp3.name
        tts.save(tmp_mp3_path)

    # Convert MP3 to OGG (Telegram voice format) using ffmpeg
    tmp_ogg_path = tmp_mp3_path.replace(".mp3", ".ogg")

    import subprocess
    result = subprocess.run(
        ["ffmpeg", "-i", tmp_mp3_path, "-c:a", "libopus", "-b:a", "64k", "-y", tmp_ogg_path],
        capture_output=True,
    )

    audio_bytes = None
    if result.returncode == 0:
        with open(tmp_ogg_path, "rb") as f:
            audio_bytes = f.read()

    # Cleanup
    for path in (tmp_mp3_path, tmp_ogg_path):
        try:
            os.unlink(path)
        except OSError:
            pass

    return audio_bytes if audio_bytes else None
