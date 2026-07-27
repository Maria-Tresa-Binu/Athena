"""Speech output adapters for Athena."""

import json
import shutil
import subprocess
from typing import Protocol


class Speaker(Protocol):
    def speak(self, text: str) -> None: ...


class SilentSpeaker:
    """No-op speaker used by tests and text-only sessions."""

    def speak(self, text: str) -> None:
        return


class WindowsSpeaker:
    """Use Windows' built-in System.Speech engine without extra Python packages."""

    def __init__(self, rate: int = 0, volume: int = 100) -> None:
        self.rate = max(-10, min(10, rate))
        self.volume = max(0, min(100, volume))
        self.executable = shutil.which("powershell") or shutil.which("pwsh")

    @property
    def available(self) -> bool:
        return self.executable is not None

    def speak(self, text: str) -> None:
        if not self.executable or not text.strip():
            return
        # JSON encoding safely quotes the text before it is embedded in PowerShell.
        safe_text = json.dumps(text.replace("http://", "").replace("https://", ""))
        script = (
            "Add-Type -AssemblyName System.Speech; "
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {self.rate}; $s.Volume = {self.volume}; "
            f"$s.Speak({safe_text}); $s.Dispose()"
        )
        subprocess.run([self.executable, "-NoProfile", "-NonInteractive", "-Command", script], check=False, capture_output=True)


def create_speaker(text_only: bool = False) -> Speaker:
    if text_only:
        return SilentSpeaker()
    speaker = WindowsSpeaker()
    return speaker if speaker.available else SilentSpeaker()
