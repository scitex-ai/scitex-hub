#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: apps/llm_app/consumers.py
"""WebSocket consumers for LLM app.

Handles JS eval relay and UI action forwarding between
Django API endpoints and the user's browser.
"""

import json

from channels.generic.websocket import AsyncWebsocketConsumer


class EvalJSConsumer(AsyncWebsocketConsumer):
    """WebSocket relay for JS evaluation in the user's browser.

    Flow:
        1. Browser connects → joins the group from relay_groups.relay_group_for
           (keyed on the visitor LEASE, not the username — see that module)
        2. MCP tool calls POST /llm/api/eval-js/
        3. Django view sends eval_js message to group
        4. This consumer forwards to browser WebSocket
        5. Browser evaluates JS, sends result back
        6. Consumer stores result in cache for the polling view
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return

        # The group is keyed on the LEASE, not the username. `visitor-007` is a
        # SEAT recycled across people (pool_manager.py:247), and a socket leaves
        # its group only on disconnect (below) — nothing in the slot-release
        # path closes one. Keying on the username alone therefore delivered a
        # later occupant's frames into the previous occupant's still-open
        # browser. See relay_groups.py for why the lease and not the session.
        from .relay_groups import relay_group_for

        self.username = user.username
        self.eval_group = relay_group_for(user)

        await self.channel_layer.group_add(self.eval_group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "eval_group"):
            await self.channel_layer.group_discard(self.eval_group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """Receive JS eval result from browser."""
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get("type")
        if msg_type == "eval_js_result":
            request_id = data.get("request_id")
            result = data.get("result")
            if request_id:
                from django.core.cache import cache

                cache_key = f"eval_js_result_{request_id}"
                cache.set(cache_key, result, timeout=60)

    async def eval_js(self, event):
        """Forward eval_js request to browser."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "eval_js",
                    "code": event["code"],
                    "request_id": event["request_id"],
                }
            )
        )

    async def ui_action(self, event):
        """Forward UI action request to browser."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "ui_action",
                    "steps": event["steps"],
                    "delay_ms": event.get("delay_ms", 900),
                }
            )
        )


# EOF
