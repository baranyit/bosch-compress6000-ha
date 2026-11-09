"""KM200 payload crypto: AES-256-ECB, zero padded, base64 on the wire.

The key is the concatenation of two MD5 sums: MD5(gateway password + magic) and
MD5(magic + private password). The gateway password is the 16 characters from the device sticker
(without dashes); the private password is the one set in the vendor app.
"""

from __future__ import annotations

import base64
import binascii
import hashlib

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .errors import InvalidKeyError

MAGIC = bytes(
    [
        0x86, 0x78, 0x45, 0xE9, 0x7C, 0x4E, 0x29, 0xDC, 0xE5, 0x22, 0xB9, 0xA7, 0xD3, 0xA3, 0xE0,
        0x7B, 0x15, 0x2B, 0xFF, 0xAD, 0xDD, 0xBE, 0xD7, 0xF5, 0xFF, 0xD8, 0x42, 0xE9, 0x89, 0x5A,
        0xD1, 0xE4,
    ]
)  # fmt: skip
BLOCK = 16


def normalize_gateway_password(value: str) -> str:
    """Strip the dashes and spaces printed on the sticker."""
    return value.replace("-", "").replace(" ", "").strip()


def build_key(gateway_password: str, private_password: str) -> bytes:
    part1 = hashlib.md5(normalize_gateway_password(gateway_password).encode() + MAGIC).digest()
    part2 = hashlib.md5(MAGIC + private_password.encode()).digest()
    return part1 + part2


def decrypt(key: bytes, body: str) -> str:
    """Decode a gateway reply: base64, AES-ECB, trailing zero bytes removed."""
    try:
        raw = base64.b64decode("".join(body.split()), validate=True)
    except (binascii.Error, ValueError) as err:
        raise InvalidKeyError("reply is not base64") from err
    if not raw or len(raw) % BLOCK:
        raise InvalidKeyError("reply length is not a multiple of the block size")
    decryptor = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    plain = decryptor.update(raw) + decryptor.finalize()
    try:
        text = plain.rstrip(b"\x00").decode("utf-8")
    except UnicodeDecodeError as err:
        raise InvalidKeyError("reply does not decrypt to text") from err
    if not text.lstrip().startswith(("{", "[")):  # every gateway reply is JSON
        raise InvalidKeyError("reply does not decrypt to JSON")
    return text


def encrypt(key: bytes, text: str) -> str:
    """Encrypt a request body: zero padded to the block size, base64 encoded."""
    data = text.encode("utf-8")
    data += b"\x00" * (-len(data) % BLOCK)
    encryptor = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return base64.b64encode(encryptor.update(data) + encryptor.finalize()).decode("ascii")
