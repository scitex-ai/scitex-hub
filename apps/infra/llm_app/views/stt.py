"""Speech-to-text endpoint using whisper.cpp."""

import os
import subprocess
import tempfile

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

# Paths match the baked-in Dockerfile location (same across dev/staging/production)
_WHISPER_CLI = "/opt/whisper/bin/whisper-cli"
_MODELS_DIR = "/opt/whisper/models"
_DEFAULT_MODEL = "ggml-base.en"

# Models that whisper.cpp supports (name → display label)
_KNOWN_MODELS = [
    ("ggml-tiny.en", "tiny.en (fast, ~39 MB)"),
    ("ggml-tiny", "tiny (fast, multilingual, ~75 MB)"),
    ("ggml-base.en", "base.en (balanced, ~142 MB)"),
    ("ggml-base", "base (multilingual, ~142 MB)"),
    ("ggml-small.en", "small.en (accurate, ~466 MB)"),
    ("ggml-small", "small (multilingual, ~466 MB)"),
]


def _whisper_cli() -> str:
    return os.environ.get("WHISPER_CLI", _WHISPER_CLI)


def _models_dir() -> str:
    return os.environ.get("WHISPER_MODELS_DIR", _MODELS_DIR)


def _available_models() -> list[dict]:
    """List whisper models found on disk in the models directory."""
    mdir = _models_dir()
    if not os.path.isdir(mdir):
        return []
    found = []
    for name, label in _KNOWN_MODELS:
        path = os.path.join(mdir, f"{name}.bin")
        if os.path.isfile(path):
            found.append({"name": name, "label": label, "path": path})
    return found


def _resolve_model(requested: str | None) -> str | None:
    """Return the model file path for the given model name, or None if not found."""
    mdir = _models_dir()
    if not requested:
        # Default: prefer base.en, then fall back to first available
        for name, _ in _KNOWN_MODELS:
            path = os.path.join(mdir, f"{name}.bin")
            if os.path.isfile(path):
                return path
        return None

    # Normalise: strip trailing .bin if provided
    name = requested.removesuffix(".bin")
    path = os.path.join(mdir, f"{name}.bin")
    return path if os.path.isfile(path) else None


@login_required
@require_http_methods(["GET"])
def api_stt_models(request):
    """List available whisper models found on disk.

    Returns: {"models": [{"name": "ggml-tiny.en", "label": "..."}, ...], "default": "ggml-base.en"}
    """
    cli = _whisper_cli()
    if not os.path.isfile(cli):
        return JsonResponse({"models": [], "default": None, "available": False})

    models = [{"name": m["name"], "label": m["label"]} for m in _available_models()]
    # Choose default: prefer base.en, then first available
    default = None
    for m in models:
        if m["name"] == _DEFAULT_MODEL:
            default = m["name"]
            break
    if default is None and models:
        default = models[0]["name"]

    return JsonResponse(
        {"models": models, "default": default, "available": bool(models)}
    )


@login_required
@require_http_methods(["POST"])
def api_stt(request):
    """Transcribe uploaded audio using whisper.cpp.

    Accepts multipart POST with:
      - 'audio': audio file (webm or wav)
      - 'model': optional model name (e.g. 'ggml-tiny.en', default: ggml-base.en)

    Returns: {"text": "...", "model": "ggml-base.en"} or {"error": "..."}.
    """
    cli = _whisper_cli()
    if not os.path.isfile(cli):
        return JsonResponse(
            {"error": "Speech-to-text unavailable (whisper-cli not installed)"},
            status=503,
        )

    requested_model = request.POST.get("model") or None
    model_path = _resolve_model(requested_model)
    if not model_path:
        return JsonResponse(
            {"error": "Speech-to-text unavailable (no whisper model found)"},
            status=503,
        )

    model_name = os.path.basename(model_path).removesuffix(".bin")

    audio_file = request.FILES.get("audio")
    if not audio_file:
        return JsonResponse({"error": "audio file required"}, status=400)

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write uploaded audio to disk
        raw_path = os.path.join(tmpdir, "input.webm")
        with open(raw_path, "wb") as fh:
            for chunk in audio_file.chunks():
                fh.write(chunk)

        # Convert to 16 kHz mono WAV
        wav_path = os.path.join(tmpdir, "input.wav")
        ffmpeg = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                raw_path,
                "-ar",
                "16000",
                "-ac",
                "1",
                "-f",
                "wav",
                wav_path,
            ],
            capture_output=True,
            timeout=30,
        )
        if ffmpeg.returncode != 0:
            return JsonResponse(
                {"error": "Audio conversion failed (ffmpeg error)"},
                status=500,
            )

        # Run whisper-cli transcription
        result = subprocess.run(
            [
                cli,
                "--language",
                "en",
                "--model",
                model_path,
                "--no-timestamps",
                "--file",
                wav_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return JsonResponse({"error": "Transcription failed"}, status=500)

        # Clean output: strip timestamp lines like [00:00:00 --> 00:00:05]
        lines = [
            ln.strip()
            for ln in result.stdout.splitlines()
            if ln.strip() and not ln.strip().startswith("[")
        ]
        text = " ".join(lines).strip()
        return JsonResponse({"text": text, "model": model_name})
