"""Local speech transcription helpers backed by whisper.cpp."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

_TRANSCRIPT_MAX_CHARS = 32_000
_WHISPER_CPP_BIN_ENV = "CLAUDE_CODE_GUI_WHISPER_CPP_BIN"
_WHISPER_CPP_MODEL_ENV = "CLAUDE_CODE_GUI_WHISPER_CPP_MODEL"
_WHISPER_CPP_BIN_CANDIDATES = ("whisper-cli", "whisper-cpp")
_DEFAULT_MODEL_FILENAMES = (
    "ggml-base.bin",
    "ggml-small.bin",
    "ggml-medium.bin",
    "ggml-large-v3.bin",
)


def _normalize_language(language: str | None) -> str:
    raw = str(language or "").strip().lower().replace("_", "-")
    if not raw:
        return ""
    primary = raw.split("-", 1)[0]
    if re.fullmatch(r"[a-z]{2,3}", primary):
        return primary
    return ""


def _normalize_transcript(text: str) -> str:
    normalized = " ".join(str(text or "").split()).strip()
    if len(normalized) > _TRANSCRIPT_MAX_CHARS:
        return normalized[:_TRANSCRIPT_MAX_CHARS]
    return normalized


def _first_line(value: str, default: str) -> str:
    text = str(value or "").strip()
    if not text:
        return default
    return text.splitlines()[0][:220]


def _resolve_whisper_cpp_binary() -> str:
    explicit = os.getenv(_WHISPER_CPP_BIN_ENV, "").strip()
    if explicit:
        resolved = shutil.which(explicit) if "/" not in explicit else explicit
        if resolved and os.path.isfile(resolved) and os.access(resolved, os.X_OK):
            return resolved
        return ""

    for candidate in _WHISPER_CPP_BIN_CANDIDATES:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return ""


def _resolve_whisper_cpp_model() -> str:
    explicit = os.getenv(_WHISPER_CPP_MODEL_ENV, "").strip()
    if explicit:
        path = Path(explicit).expanduser()
        return str(path) if path.is_file() else ""

    home = Path.home()
    candidate_dirs = (
        home / ".cache" / "whisper.cpp",
        home / ".cache" / "whisper.cpp" / "models",
        home / ".local" / "share" / "whisper.cpp",
        home / ".local" / "share" / "whisper.cpp" / "models",
        Path.cwd() / "models",
    )
    for directory in candidate_dirs:
        if not directory.is_dir():
            continue
        for filename in _DEFAULT_MODEL_FILENAMES:
            candidate = directory / filename
            if candidate.is_file():
                return str(candidate)
        for wildcard_match in sorted(directory.glob("ggml-*.bin")):
            if wildcard_match.is_file():
                return str(wildcard_match)
    return ""


def _transcode_to_wav(input_path: Path, wav_path: Path, *, timeout_seconds: int) -> tuple[bool, str]:
    ffmpeg_binary = shutil.which("ffmpeg")
    if not ffmpeg_binary:
        return False, "ffmpeg is required for whisper.cpp transcription but was not found."

    command = [
        ffmpeg_binary,
        "-y",
        "-i",
        str(input_path),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        str(wav_path),
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=max(10, int(timeout_seconds)),
        )
    except subprocess.TimeoutExpired:
        return False, "Audio conversion timed out."
    except OSError as error:
        return False, f"Could not start ffmpeg: {error}"

    if result.returncode != 0:
        return False, f"Audio conversion failed: {_first_line(result.stderr or result.stdout, 'ffmpeg error')}"
    if not wav_path.is_file():
        return False, "Audio conversion failed: output file missing."
    return True, ""


def _read_transcript_candidates(paths: list[Path]) -> str:
    for path in paths:
        if not path.is_file():
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError:
            continue
        cleaned = _normalize_transcript(raw)
        if cleaned:
            return cleaned
    return ""


def _run_whisper_cpp(
    whisper_cpp_binary: str,
    model_path: str,
    wav_path: Path,
    *,
    language: str,
    timeout_seconds: int,
) -> tuple[str, str]:
    with tempfile.TemporaryDirectory(prefix="ccg-whispercpp-out-") as output_dir_raw:
        output_dir = Path(output_dir_raw)
        output_prefix = output_dir / "transcript"
        base_command = [
            whisper_cpp_binary,
            "-m",
            model_path,
            "-f",
            str(wav_path),
            "-otxt",
            "-nt",
        ]
        if language:
            base_command.extend(["-l", language])

        attempts: list[tuple[list[str], list[Path]]] = [
            (
                [*base_command, "-of", str(output_prefix)],
                [output_prefix.with_suffix(".txt"), output_dir / "transcript.txt"],
            ),
            (
                list(base_command),
                [Path(str(wav_path) + ".txt"), wav_path.with_suffix(".txt")],
            ),
        ]

        last_error = ""
        for command, transcript_candidates in attempts:
            try:
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=max(10, int(timeout_seconds)),
                )
            except subprocess.TimeoutExpired:
                return "", "whisper.cpp transcription timed out."
            except OSError as error:
                return "", f"Could not start whisper.cpp: {error}"

            if result.returncode != 0:
                last_error = _first_line(
                    result.stderr or result.stdout,
                    "whisper.cpp returned an error.",
                )
                continue

            transcript = _read_transcript_candidates(transcript_candidates)
            if transcript:
                return transcript, ""

            fallback = _normalize_transcript(result.stdout or "")
            if fallback:
                return fallback, ""
            last_error = "whisper.cpp produced no transcript."

        if last_error:
            return "", f"whisper.cpp transcription failed: {last_error}"
        return "", "whisper.cpp transcription failed."


def transcribe_audio_file(
    audio_path: str | Path,
    *,
    language: str | None = None,
    timeout_seconds: int = 180,
) -> tuple[str, str]:
    """Transcribe one local audio file and return `(transcript, error_message)`."""
    source = Path(audio_path)
    if not source.is_file():
        return "", "Voice input file was not found."

    whisper_cpp_binary = _resolve_whisper_cpp_binary()
    if not whisper_cpp_binary:
        return "", "whisper.cpp binary not found. Set CLAUDE_CODE_GUI_WHISPER_CPP_BIN or install whisper-cli."

    model_path = _resolve_whisper_cpp_model()
    if not model_path:
        return (
            "",
            "whisper.cpp model not found. Set CLAUDE_CODE_GUI_WHISPER_CPP_MODEL to a ggml-*.bin model file.",
        )

    normalized_language = _normalize_language(language)
    with tempfile.TemporaryDirectory(prefix="ccg-whispercpp-") as working_dir_raw:
        working_dir = Path(working_dir_raw)
        wav_path = working_dir / "voice-input.wav"
        ok, transcode_error = _transcode_to_wav(
            source,
            wav_path,
            timeout_seconds=timeout_seconds,
        )
        if not ok:
            return "", transcode_error
        return _run_whisper_cpp(
            whisper_cpp_binary,
            model_path,
            wav_path,
            language=normalized_language,
            timeout_seconds=timeout_seconds,
        )
