#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The one place a compilation failure is turned into a stated reason.

Extracted verbatim from ``services/writer/compilation.py`` (which still
re-exports it, so every existing import keeps working) for one reason:
``views/editor/api/compilation_full_job.py`` — the FULL-compile path —
needs the same precedence, and that module must not have to import
``scitex``/``scitex_writer._compile`` at module scope just to format an
error string.

Why it matters that both paths share this: until now the full compile
built its result dict with NO ``error`` key at all, while the front-end
(``compilation-queue.ts::handleFailed``) reads
``data.result?.error || "Compilation failed"``. So every full-compile
failure — including the measured ``returncode 127`` /
``bash: /workspace/scripts/shell/compile_manuscript.sh: No such file or
directory`` on live scitex.ai — was announced to the user as the
four-word generic string, with the actual cause visible only if they
opened the log pane. Preview did the right thing; full did not; the
difference was that only preview called this function.

Deliberately dependency-free: stdlib only, so the Django view layer and
the service layer can both import it.
"""

from __future__ import annotations

from typing import Optional

# A TeX engine reports a hard failure as a line starting with "! ", e.g.
#   ! LaTeX Error: Unicode character 」 (U+300D) not set up for use with LaTeX.
# That single line is the whole diagnosis; everything around it is package
# chatter. "! ==> Fatal error occurred" is the epilogue, not the cause, so it
# is only used when nothing better was found.
_TEX_ERROR_PREFIX = "! "
_TEX_EPILOGUE = "! ==> "


def _first_tex_error(*streams: Optional[str]) -> Optional[str]:
    """Return the first real ``! ...`` message across ``streams``, if any.

    TeX hard-wraps its own diagnostics, so the sentence continues on the
    following indented line(s) up to the first blank one:

        ! LaTeX Error: Unicode character 」 (U+300D)
                       not set up for use with LaTeX.

    Reporting only the first line would cut the message mid-sentence, so
    the continuation is folded back in.
    """
    fallback = None
    for stream in streams:
        lines = (stream or "").splitlines()
        for index, raw_line in enumerate(lines):
            line = raw_line.strip()
            if not line.startswith(_TEX_ERROR_PREFIX):
                continue
            if line.startswith(_TEX_EPILOGUE):
                fallback = fallback or line
                continue
            parts = [line]
            for continuation in lines[index + 1 :]:
                if not continuation.strip() or not continuation[:1].isspace():
                    break
                parts.append(continuation.strip())
            return " ".join(parts)
    return fallback


def _ensure_error_and_log(raw: dict) -> dict:
    """Guarantee the ``error`` / ``log`` keys the UI actually reads.

    scitex.writer.compile.content() reports a failure through
    ``message`` / ``errors`` / ``stderr`` / ``stdout`` / ``exit_code``. The
    Writer front-end reads ``result.error`` and ``result.log`` and nothing
    else (compilation-preview.ts), so a failure arrived with BOTH keys
    absent and the user was shown the client-side fallback string with no
    cause at all — measured on production 2026-08-16, where the real reason
    was a stray 」 that pdflatex cannot typeset:

        exit_code=12, message='Compilation failed with exit code 12',
        error=None, log=None,
        stdout=... '! LaTeX Error: Unicode character 」 (U+300D) ...'

    Populating the two documented keys is what turns that into an
    actionable message. Existing non-empty values are never overwritten.
    """
    stdout = raw.get("stdout")
    stderr = raw.get("stderr")

    if not raw.get("log"):
        raw["log"] = "\n".join(part for part in (stdout, stderr) if part)

    if raw.get("success") or raw.get("error"):
        return raw

    # Most specific first: the engine's own error line, then any collected
    # errors[], then the generic exit-code message.
    detail = _first_tex_error(stdout, stderr)
    if not detail:
        collected = [str(item) for item in (raw.get("errors") or []) if item]
        detail = collected[0] if collected else None

    message = raw.get("message")
    if detail and message:
        raw["error"] = f"{message}: {detail}"
    else:
        raw["error"] = detail or message or "Compilation failed"
    return raw


# EOF
