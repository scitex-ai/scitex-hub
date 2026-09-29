#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SciTeX-logging transports for scitex-hub's presentation surface (PS-220).

PS-220 forbids builtin ``print``, Rich ``Console.print`` and stdlib
``logging.getLogger`` in shippable SciTeX source. The hazard is not the text —
it is that library code writes **unconditionally** to a stream the caller
cannot silence, redirect, filter or level: there is no flag, no handler and no
level. ``scitex_logging`` supplies all four.

The CLI's human output is *not* diagnostics, so it must not be moved to
stderr: ``scitex_logging.getLogger`` writes to stderr, and a caller that pipes
``scitex-hub ... `` output would silently receive nothing. The rule sanctions
exactly one stdout-preserving transport, :func:`scitex_logging.getConsole`, and
this module is hub's single factory for it — the same migration scitex-dev made
for itself (commit 04a2e156, ``src/scitex_dev/_core/streams.py``).

Why a renderer rather than a plain logger
-----------------------------------------

Rich ``Console.print`` accepts a *renderable* — a ``Table``, a ``Panel``, or a
string carrying markup like ``[red]Cannot reach …[/red]``. Handing that string
straight to a ``logging`` call would print the tags literally
(``[red]Cannot reach …[/red]``); handing a ``Table`` to it would not render at
all. So :class:`Console` renders the renderable with Rich's own renderer —
``Console.render_lines`` — and emits the resulting text as ONE levelled record.
The console stream is never written to, so the table a reader sees is
byte-identical while the operator gains the level.

The four methods are the four SciTeX levels, so a call site states its severity
instead of encoding it in colour markup alone.
"""

from __future__ import annotations

from typing import Any

import scitex_logging as slogging
from rich.console import Console as _RichConsole

__all__ = ["Console", "get_console"]

#: One stdout sink for the whole hub CLI. A single name (rather than one per
#: module) keeps severity filtering coherent across the command tree: an
#: operator silencing hub's presentation output has one logger to set.
DEFAULT_CONSOLE_NAME = "scitex_hub"


def _to_text(renderable: Any) -> str:
    """Render a Rich renderable (or a markup string) to plain terminal text.

    Parameters
    ----------
    renderable : Any
        Any Rich renderable: a ``rich.table.Table``, a markup ``str``, …

    Returns
    -------
    str
        The rendered text, trailing newline removed. Markup is resolved to
        styled segments and the segment text is concatenated, so callers that
        pass ``[red]…[/red]`` do not leak the tags into a log line.
    """
    rich_console = _RichConsole()
    lines = rich_console.render_lines(
        renderable, rich_console.options, pad=False
    )
    text = "\n".join(
        "".join(segment.text for segment in line) for line in lines
    )
    return text.rstrip("\n")


class Console:
    """A SciTeX level-aware replacement for Rich's ``Console``.

    Exposes the four SciTeX levels — ``info`` / ``success`` / ``warning`` /
    ``error`` — instead of Rich's prefix-free ``print``. Each method renders the
    argument and emits one labelled record to **stdout** via
    :func:`scitex_logging.getConsole`, so stdout is preserved for callers that
    parse it while the record gains a level, an aligned
    ``INFO:``/``SUCC:``/``WARN:``/``ERRO:`` prefix and a searchable name.

    Parameters
    ----------
    name : str | None
        Logger name. Defaults to :data:`DEFAULT_CONSOLE_NAME`.
    """

    __slots__ = ("_name",)

    def __init__(self, name: str | None = None) -> None:
        self._name = name or DEFAULT_CONSOLE_NAME

    def _emit(self, level: str, renderable: Any) -> None:
        getattr(slogging.getConsole(self._name), level)(_to_text(renderable))

    def info(self, renderable: Any) -> None:
        """Emit *renderable* at INFO (``INFO:``)."""
        self._emit("info", renderable)

    def success(self, renderable: Any) -> None:
        """Emit *renderable* at SUCCESS (``SUCC:``)."""
        self._emit("success", renderable)

    def warning(self, renderable: Any) -> None:
        """Emit *renderable* at WARNING (``WARN:``)."""
        self._emit("warning", renderable)

    def error(self, renderable: Any) -> None:
        """Emit *renderable* at ERROR (``ERRO:``)."""
        self._emit("error", renderable)


def get_console(name: str | None = None) -> Console:
    """Return the SciTeX **stdout** presentation sink for *name*.

    Parameters
    ----------
    name : str | None
        Logger name — pass ``__name__`` from the call site. ``None`` uses
        :data:`DEFAULT_CONSOLE_NAME`.

    Returns
    -------
    Console
        A level-aware renderer/sink. It has no ``print`` method: Rich's
        prefix-free ``print`` is exactly the primitive PS-220 removes.
    """
    return Console(name)


# EOF
