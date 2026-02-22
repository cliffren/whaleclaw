"""Tests for Feishu webhook verification and decryption."""

from __future__ import annotations

import hashlib
import json

from whaleclaw.channels.feishu.webhook import decrypt_event, verify_signature


class TestVerifySignature:
    def test_valid_signature(self) -> None:
        ts = "1234567890"
        nonce = "abc"
        key = "secret"
        body = b'{"test": true}'
        content = f"{ts}{nonce}{key}".encode() + body
        sig = hashlib.sha256(content).hexdigest()
        assert verify_signature(ts, nonce, key, body, sig)

    def test_invalid_signature(self) -> None:
        assert not verify_signature("ts", "nonce", "key", b"body", "bad")


class TestDecryptEvent:
    def test_roundtrip(self) -> None:
        from base64 import b64encode

        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        key_str = "test-encrypt-key"
        key = hashlib.sha256(key_str.encode()).digest()
        iv = b"\x00" * 16
        plaintext = json.dumps({"hello": "world"}).encode()
        pad_len = 16 - len(plaintext) % 16
        padded = plaintext + bytes([pad_len] * pad_len)

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        enc = cipher.encryptor()
        ct = enc.update(padded) + enc.finalize()
        encrypted = b64encode(iv + ct).decode()

        result = decrypt_event(key_str, encrypted)
        assert result == {"hello": "world"}
