"""Text-to-Speech using Microsoft Edge TTS (free, high quality)."""

import io
import logging
import tempfile

import edge_tts

logger = logging.getLogger(__name__)

# Russian male voice (natural sounding)
VOICE = "ru-RU-DmitryNeural"


async def text_to_speech(text: str) -> bytes | None:
    """Convert text to OGG audio bytes for Telegram voice message."""
    try:
        communicate = edge_tts.Communicate(text, VOICE)

        # Save MP3 first
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_mp3:
            tmp_mp3_path = tmp_mp3.name

        await communicate.save(tmp_mp3_path)

        # Convert MP3 to OGG (Telegram voice format) using ffmpeg
        import asyncio
        tmp_ogg_path = tmp_mp3_path.replace(".mp3", ".ogg")

        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", tmp_mp3_path,
            "-c:a", "libopus", "-b:a", "64k",
            "-y", tmp_ogg_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        with open(tmp_ogg_path, "rb") as f:
            audio_bytes = f.read()

        # Cleanup
        import os
        for path in (tmp_mp3_path, tmp_ogg_path):
            try:
                os.unlink(path)
            except OSError:
                pass

        logger.info("TTS generated: %d bytes", len(audio_bytes))
        return audio_bytes if audio_bytes else None

    except Exception as e:
        logger.error("TTS error: %s", e, exc_info=True)
        return None
