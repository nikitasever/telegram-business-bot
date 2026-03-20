"""Utilities for extracting content from various media types."""

import asyncio
import base64
import io
import logging
import tempfile

from aiogram import Bot
from aiogram.types import Message

logger = logging.getLogger(__name__)


async def get_image_base64(message: Message, bot: Bot) -> str | None:
    """Download photo from message and return as base64 string."""
    try:
        photo = None
        if message.photo:
            photo = message.photo[-1]
            logger.info("Got photo, file_id: %s", photo.file_id)
        elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
            photo = message.document
            logger.info("Got image document, file_id: %s", photo.file_id)

        if not photo:
            return None

        file = await bot.get_file(photo.file_id)
        buffer = io.BytesIO()
        await bot.download_file(file.file_path, buffer)
        data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        logger.info("Image downloaded, base64 length: %d", len(data))
        return data
    except Exception as e:
        logger.error("Failed to download image: %s", e, exc_info=True)
        return None


async def get_audio_bytes(message: Message, bot: Bot) -> tuple[bytes, str] | tuple[None, None]:
    """Download voice/audio from message and return (bytes, filename)."""
    try:
        if message.voice:
            file = await bot.get_file(message.voice.file_id)
            filename = "voice.ogg"
        elif message.audio:
            file = await bot.get_file(message.audio.file_id)
            filename = message.audio.file_name or "audio.mp3"
        elif message.video_note:
            file = await bot.get_file(message.video_note.file_id)
            filename = "video_note.mp4"
        else:
            return None, None

        buffer = io.BytesIO()
        await bot.download_file(file.file_path, buffer)
        logger.info("Audio downloaded: %s, size: %d bytes", filename, buffer.tell())
        return buffer.getvalue(), filename
    except Exception as e:
        logger.error("Failed to download audio: %s", e, exc_info=True)
        return None, None


async def get_video_frames_base64(message: Message, bot: Bot, max_frames: int = 3) -> list[str]:
    """Extract key frames from video and return as base64 strings."""
    try:
        video = None
        if message.video:
            video = message.video
        elif message.video_note:
            video = message.video_note
        elif message.document and message.document.mime_type and message.document.mime_type.startswith("video/"):
            video = message.document

        if not video:
            return []

        file = await bot.get_file(video.file_id)
        buffer = io.BytesIO()
        await bot.download_file(file.file_path, buffer)

        # Save to temp file for ffmpeg
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp.write(buffer.getvalue())
            tmp_path = tmp.name

        frames = []
        # Extract frames at evenly spaced intervals
        duration_cmd = await asyncio.create_subprocess_exec(
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", tmp_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await duration_cmd.communicate()
        try:
            duration = float(stdout.decode().strip())
        except (ValueError, AttributeError):
            duration = 10.0

        intervals = [duration * i / (max_frames + 1) for i in range(1, max_frames + 1)]

        for t in intervals:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as frame_tmp:
                frame_path = frame_tmp.name

            proc = await asyncio.create_subprocess_exec(
                "ffmpeg", "-ss", str(t), "-i", tmp_path,
                "-frames:v", "1", "-q:v", "5", "-y", frame_path,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            try:
                with open(frame_path, "rb") as f:
                    frame_data = f.read()
                    if frame_data:
                        frames.append(base64.b64encode(frame_data).decode("utf-8"))
            except FileNotFoundError:
                pass

            # Cleanup frame
            import os
            try:
                os.unlink(frame_path)
            except OSError:
                pass

        # Cleanup video
        import os
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

        logger.info("Extracted %d frames from video", len(frames))
        return frames

    except Exception as e:
        logger.error("Failed to extract video frames: %s", e, exc_info=True)
        return []


async def get_document_text(message: Message, bot: Bot) -> str | None:
    """Extract text from PDF or DOCX documents."""
    try:
        doc = message.document
        if not doc or not doc.mime_type:
            return None

        file = await bot.get_file(doc.file_id)
        buffer = io.BytesIO()
        await bot.download_file(file.file_path, buffer)
        buffer.seek(0)

        if doc.mime_type == "application/pdf":
            return _extract_pdf_text(buffer)
        elif doc.mime_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            return _extract_docx_text(buffer)
        elif doc.mime_type.startswith("text/"):
            return buffer.read().decode("utf-8", errors="replace")[:5000]

        return None
    except Exception as e:
        logger.error("Failed to extract document text: %s", e, exc_info=True)
        return None


def _extract_pdf_text(buffer: io.BytesIO) -> str:
    from PyPDF2 import PdfReader
    reader = PdfReader(buffer)
    text_parts = []
    for page in reader.pages[:20]:  # max 20 pages
        text_parts.append(page.extract_text() or "")
    text = "\n".join(text_parts).strip()
    return text[:5000] if text else ""


def _extract_docx_text(buffer: io.BytesIO) -> str:
    from docx import Document
    doc = Document(buffer)
    text_parts = [p.text for p in doc.paragraphs]
    text = "\n".join(text_parts).strip()
    return text[:5000] if text else ""
