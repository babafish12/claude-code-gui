from __future__ import annotations

import stat
import subprocess
from pathlib import Path

import pytest

from claude_code_gui.services import speech_transcribe

pytestmark = pytest.mark.unit


def _touch_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR)


def test_transcribe_audio_file_reports_missing_whisper_cpp_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "sample.webm"
    audio.write_bytes(b"audio")

    monkeypatch.delenv("CLAUDE_CODE_GUI_WHISPER_CPP_BIN", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_GUI_WHISPER_CPP_MODEL", raising=False)
    monkeypatch.setattr(speech_transcribe.shutil, "which", lambda _name: None)

    transcript, error = speech_transcribe.transcribe_audio_file(audio)

    assert transcript == ""
    assert "whisper.cpp binary not found" in error


def test_transcribe_audio_file_reports_missing_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "sample.webm"
    audio.write_bytes(b"audio")
    fake_bin = tmp_path / "whisper-cli"
    _touch_executable(fake_bin)

    monkeypatch.setenv("CLAUDE_CODE_GUI_WHISPER_CPP_BIN", str(fake_bin))
    monkeypatch.setenv("CLAUDE_CODE_GUI_WHISPER_CPP_MODEL", str(tmp_path / "missing-model.bin"))

    transcript, error = speech_transcribe.transcribe_audio_file(audio)

    assert transcript == ""
    assert "model not found" in error


def test_transcribe_audio_file_runs_whisper_cpp_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    audio = tmp_path / "sample.webm"
    audio.write_bytes(b"audio")
    fake_bin = tmp_path / "whisper-cli"
    fake_model = tmp_path / "ggml-base.bin"
    _touch_executable(fake_bin)
    fake_model.write_bytes(b"model")

    monkeypatch.setenv("CLAUDE_CODE_GUI_WHISPER_CPP_BIN", str(fake_bin))
    monkeypatch.setenv("CLAUDE_CODE_GUI_WHISPER_CPP_MODEL", str(fake_model))

    ffmpeg_bin = "/usr/bin/ffmpeg"

    def _fake_which(name: str) -> str | None:
        if name == "ffmpeg":
            return ffmpeg_bin
        return None

    def _fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> subprocess.CompletedProcess[str]:
        assert check is False
        assert capture_output is True
        assert text is True
        assert timeout >= 10

        if command[0] == ffmpeg_bin:
            wav_path = Path(command[-1])
            wav_path.write_bytes(b"wav")
            return subprocess.CompletedProcess(command, 0, "", "")

        if command[0] == str(fake_bin):
            output_prefix = command[command.index("-of") + 1]
            transcript_path = Path(output_prefix + ".txt")
            transcript_path.write_text("hallo welt", encoding="utf-8")
            return subprocess.CompletedProcess(command, 0, "", "")

        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(speech_transcribe.shutil, "which", _fake_which)
    monkeypatch.setattr(speech_transcribe.subprocess, "run", _fake_run)

    transcript, error = speech_transcribe.transcribe_audio_file(
        audio,
        language="de-CH",
    )

    assert error == ""
    assert transcript == "hallo welt"
