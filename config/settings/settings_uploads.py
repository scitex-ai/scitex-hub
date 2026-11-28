#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Request-body memory limits, shared by every environment.

FILE_UPLOAD_MAX_MEMORY_SIZE: an uploaded file larger than this is written to a
temporary file on disk while it streams in, instead of being held in RAM. The
overall upload size limit is nginx's ``client_max_body_size`` and the per-user
storage quota (``config/settings/quotas.py``), not this value.

DATA_UPLOAD_MAX_MEMORY_SIZE: the largest NON-file body Django reads into memory
(``request.body`` and form fields; file parts are excluded). It used to be
100 MB for base64 images in AI chat, but the chat endpoints cap their own body
at 128 KiB (``llm_app/views/chat.py``), so nothing needs that much. The largest
legitimate JSON body left is a browser screenshot posted as base64 (console
on-site capture); 20 MiB covers it with room to spare. A larger body is refused
with 400 before it is buffered.
"""

FILE_UPLOAD_MAX_MEMORY_SIZE = 2_621_440  # 2.5 MiB (Django's default, explicit)
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024  # 20 MiB  # stx-allow: STX-NL001
