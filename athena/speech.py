"""Speech output adapters for Athena."""

import json
import html
import os
import re
import shutil
import subprocess
from typing import Protocol


class Speaker(Protocol):
    def speak(self, text: str) -> None: ...


class SilentSpeaker:
    """No-op speaker used by tests and text-only sessions."""

    def speak(self, text: str) -> None:
        return


def prepare_for_speech(text: str) -> str:
    """Convert model/tool output into natural text for speech synthesis."""
    text = html.unescape(text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"[*_`#{}\[\]<>|]", " ", text)
    text = text.replace("&", " and ")
    text = text.replace("@", " at ")
    text = text.replace("/", " ").replace("\\", " ")
    text = re.sub(r"[-–—]+", " ", text)
    # Keep normal sentence punctuation, while removing emoji and control symbols.
    text = re.sub(r"[^\w\s.,?!:;']", " ", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


class WindowsSpeaker:
    """Use Windows' built-in System.Speech engine without extra Python packages."""

    def __init__(self, rate: int = 0, volume: int = 100, voice: str | None = None) -> None:
        self.rate = max(-10, min(10, rate))
        self.volume = max(0, min(100, volume))
        self.voice = voice or os.getenv("ATHENA_VOICE", "Microsoft Aria Online (Natural)")
        self.executable = shutil.which("powershell") or shutil.which("pwsh")

    @property
    def available(self) -> bool:
        return self.executable is not None

    def speak(self, text: str) -> None:
        if not self.executable or not text.strip():
            return
        text = prepare_for_speech(text)
        if not text:
            return
        # JSON encoding safely quotes the text before it is embedded in PowerShell.
        safe_text = json.dumps(text)
        safe_voice = json.dumps(self.voice)
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$preferred = {safe_voice}; "
            "$installed = @($s.GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }); "
            "$chosen = $installed | Where-Object { $_ -eq $preferred } | Select-Object -First 1; "
            "if (-not $chosen) { $chosen = $installed | Where-Object { $_ -match 'Zira|Hazel|Susan|Jenny|Aria|Female' } | Select-Object -First 1 }; "
            "if ($chosen) { $s.SelectVoice($chosen) }; "
            f"$s.Rate = {self.rate}; $s.Volume = {self.volume}; "
            f"$s.Speak({safe_text}); $s.Dispose()"
        )
        subprocess.run([self.executable, "-NoProfile", "-NonInteractive", "-Command", script], check=False, capture_output=True)


def create_speaker(text_only: bool = False) -> Speaker:
    if text_only:
        return SilentSpeaker()
    speaker = WindowsSpeaker()
    return speaker if speaker.available else SilentSpeaker()
