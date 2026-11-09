from __future__ import annotations

import pytest

from custom_components.bosch_compress6000.crypto import (
    build_key,
    decrypt,
    encrypt,
    normalize_gateway_password,
)
from custom_components.bosch_compress6000.errors import InvalidKeyError

# Worked example from the KM200 protocol notes (public documentation values, not real credentials).
EXAMPLE_KEY = "91df2cd7631c309f2027b89a5126a481bf39ade2565b0af0947faad456a5cc9c"


def test_key_derivation_matches_the_documented_example() -> None:
    assert build_key("NeUCsyQMLVYqKJec", "HnE75f+a%aXP").hex() == EXAMPLE_KEY


def test_gateway_password_dashes_and_spaces_are_ignored() -> None:
    assert normalize_gateway_password("NeUC-syQM LVYq-KJec") == "NeUCsyQMLVYqKJec"
    assert build_key("NeUC-syQM-LVYq-KJec", "HnE75f+a%aXP").hex() == EXAMPLE_KEY


def test_round_trip_is_zero_padded_to_the_block_size() -> None:
    key = build_key("NeUCsyQMLVYqKJec", "HnE75f+a%aXP")
    text = '{"value":"start"}'
    assert decrypt(key, encrypt(key, text)) == text
    exact = '{"value":"abcdef"}'[:16]
    assert len(exact) == 16
    assert encrypt(key, exact) == encrypt(key, exact + "")
    assert len(encrypt(key, exact)) == 24  # base64 of exactly one block, no extra padding block


@pytest.mark.parametrize("body", ["", "not base64!!", "AAAA", "QUJD"])
def test_garbage_replies_raise_invalid_key(body: str) -> None:
    with pytest.raises(InvalidKeyError):
        decrypt(build_key("a", "b"), body)


def test_wrong_key_raises_invalid_key() -> None:
    good = build_key("NeUCsyQMLVYqKJec", "HnE75f+a%aXP")
    bad = build_key("NeUCsyQMLVYqKJec", "other")
    with pytest.raises(InvalidKeyError):
        decrypt(bad, encrypt(good, '{"value": 1, "type": "floatValue"}'))
