"""SSE streaming utilities for LLM chat endpoints."""


async def with_keepalive(aiter, interval_s: float = 15.0):
    """Wrap an async iterator with SSE keepalive comments.

    Sends ``: keepalive`` comments when no data arrives within *interval_s*
    seconds, preventing proxies and browsers from closing idle connections.
    """
    import asyncio
    import json as _json

    ait = aiter.__aiter__()
    while True:
        try:
            event = await asyncio.wait_for(ait.__anext__(), timeout=interval_s)
            yield f"data: {_json.dumps(event)}\n\n"
        except asyncio.TimeoutError:
            yield ": keepalive\n\n"
        except StopAsyncIteration:
            break


def build_multimodal_user_msg(prompt: str, attachments: list) -> dict:
    """Build a user message dict, multimodal if attachments present.

    Returns a standard ``{"role": "user", "content": ...}`` dict where
    *content* is a string (text-only) or a list of content parts (vision).
    """
    if attachments:
        user_content = [{"type": "text", "text": prompt}]
        for att in attachments[:4]:
            mime = att.get("mime", "image/png")
            b64 = att.get("base64", "")
            if b64:
                user_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    }
                )
        return {"role": "user", "content": user_content}
    return {"role": "user", "content": prompt}
