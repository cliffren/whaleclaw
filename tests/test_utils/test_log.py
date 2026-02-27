from __future__ import annotations

from whaleclaw.utils.log import _mask_sensitive_query_values


def test_mask_sensitive_query_values_masks_long_tokens() -> None:
    text = (
        '127.0.0.1 - "WebSocket /ws?token=abcdefghijklmnop'
        '&access_key=1234567890abcdef&x=1" [accepted]'
    )
    masked = _mask_sensitive_query_values(text)
    assert "token=abcd***mnop" in masked
    assert "access_key=1234***cdef" in masked
    assert "x=1" in masked


def test_mask_sensitive_query_values_masks_short_values() -> None:
    text = 'GET /ws?ticket=abcd1234&token=short HTTP/1.1'
    masked = _mask_sensitive_query_values(text)
    assert "ticket=***" in masked
    assert "token=***" in masked
