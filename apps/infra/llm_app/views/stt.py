"""Speech-to-text endpoint.

Transcription itself lives in the ``scitex-audio`` package (``scitex_audio.transcribe``),
which owns the ffmpeg-convert -> whisper.cpp -> parse pipeline. This module only does what
is genuinely hub's job: resolve the deployment's baked-in whisper paths, validate the
request, and shape the HTTP response.

Hub deliberately keeps its own model DISCOVERY because the paths (``/opt/whisper``) are
baked into hub's container image and differ from the package's own search paths; the
resolved binary and model are handed to the package as explicit overrides.
"""

import os
import tempfile

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

# Paths match the baked-in Dockerfile location (same across dev/staging/production)
_WHISPER_CLI = "/opt/whisper/bin/whisper-cli"
_MODELS_DIR = "/opt/whisper/models"

# Models that whisper.cpp supports (name → display label).
# MULTILINGUAL FIRST: the ``.en`` weights cannot transcribe anything but English, and this
# endpoint serves Japanese dictation, so an English-only model must never be the default.
_KNOWN_MODELS = [
    ("ggml-base", "base (multilingual, ~142 MB)"),
    ("ggml-small", "small (multilingual, ~466 MB)"),
    ("ggml-medium", "medium (multilingual, ~1.5 GB)"),
    ("ggml-large-v3-turbo", "large-v3-turbo (multilingual, ~1.6 GB)"),
    ("ggml-tiny", "tiny (fast, multilingual, ~75 MB)"),
    ("ggml-base.en", "base.en (English only, ~142 MB)"),
    ("ggml-small.en", "small.en (English only, ~466 MB)"),
    ("ggml-tiny.en", "tiny.en (English only, ~39 MB)"),
]

# Preferred default, when the caller does not name a model. Multilingual on purpose.
_DEFAULT_MODEL = "ggml-base"

# ``None`` means "let whisper auto-detect the language". Deployments that know their
# audience can pin one (e.g. "ja") without touching code.
_DEFAULT_LANGUAGE = os.environ.get("STT_DEFAULT_LANGUAGE") or None


def _whisper_cli() -> str:
    return os.environ.get("WHISPER_CLI", _WHISPER_CLI)


def _models_dir() -> str:
    return os.environ.get("WHISPER_MODELS_DIR", _MODELS_DIR)


def _available_models(models_dir: str | None = None) -> list[dict]:
    """List whisper models found on disk in the models directory."""
    mdir = models_dir or _models_dir()
    if not os.path.isdir(mdir):
        return []
    found = []
    for name, label in _KNOWN_MODELS:
        path = os.path.join(mdir, f"{name}.bin")
        if os.path.isfile(path):
            found.append({"name": name, "label": label, "path": path})
    return found


def _resolve_model(requested: str | None, models_dir: str | None = None) -> str | None:
    """Return the model file path for the given model name, or None if not found."""
    mdir = models_dir or _models_dir()
    if not requested:
        # Default: prefer the multilingual default, then the first available in
        # _KNOWN_MODELS order (which is multilingual-first by design).
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

    Returns: {"models": [{"name": "ggml-base", "label": "..."}, ...], "default": "ggml-base"}
    """
    cli = _whisper_cli()
    if not os.path.isfile(cli):
        return JsonResponse({"models": [], "default": None, "available": False})

    models = [{"name": m["name"], "label": m["label"]} for m in _available_models()]
    # Choose default: prefer the multilingual default, then first available
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
    """Transcribe uploaded audio.

    Accepts multipart POST with:
      - 'audio': audio file (webm or wav)
      - 'model': optional model name (e.g. 'ggml-tiny', default: ggml-base)
      - 'language': optional language code (e.g. 'ja', 'en'). Omit to auto-detect.

    Returns: {"text": "...", "model": "ggml-base", "language": "ja"} or {"error": "..."}.
    """
    from scitex_audio import transcribe

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

    language = request.POST.get("language") or _DEFAULT_LANGUAGE

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write uploaded audio to disk. scitex_audio.transcribe accepts any format
        # ffmpeg can read and does the 16 kHz mono conversion itself.
        raw_path = os.path.join(tmpdir, "input.webm")
        with open(raw_path, "wb") as fh:
            for chunk in audio_file.chunks():
                fh.write(chunk)

        result = transcribe(
            raw_path,
            language=language,
            whisper_cli=cli,
            model_path=model_path,
        )

    if not result.get("success"):
        return JsonResponse(
            {"error": result.get("error") or "Transcription failed"}, status=500
        )

    return JsonResponse(
        {
            "text": (result.get("text") or "").strip(),
            "model": model_name,
            "language": result.get("language") or language,
        }
    )
