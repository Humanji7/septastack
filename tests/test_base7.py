"""Tests for base-7 utilities."""

import pytest
from septa.common.base7 import (
    BASE,
    MAX_WORD,
    MEMORY_SIZE,
    SEPTITS_PER_WORD,
    format_base7,
    parse_base7,
    parse_decimal,
    validate_word,
)


class TestConstants:
    def test_base(self):
        assert BASE == 7

    def test_septits_per_word(self):
        assert SEPTITS_PER_WORD == 12

    def test_max_word(self):
        assert MAX_WORD == 7**12 - 1

    def test_memory_size(self):
        assert MEMORY_SIZE == 7**5
        assert MEMORY_SIZE == 16807


class TestParseBase7:
    def test_zero(self):
        assert parse_base7("0") == 0

    def test_single_digit(self):
        for d in range(7):
            assert parse_base7(str(d)) == d

    def test_10_is_seven(self):
        assert parse_base7("10") == 7

    def test_16_is_thirteen(self):
        assert parse_base7("16") == 13

    def test_100_is_49(self):
        assert parse_base7("100") == 49

    def test_666_is_342(self):
        # 6*49 + 6*7 + 6 = 294 + 42 + 6 = 342
        assert parse_base7("666") == 342

    def test_multi_digit(self):
        # 123 in base 7 = 1*49 + 2*7 + 3 = 66
        assert parse_base7("123") == 66

    def test_invalid_digit_7(self):
        with pytest.raises(ValueError, match="invalid base-7 digit: '7'"):
            parse_base7("17")

    def test_invalid_digit_8(self):
        with pytest.raises(ValueError, match="invalid base-7 digit: '8'"):
            parse_base7("8")

    def test_invalid_digit_9(self):
        with pytest.raises(ValueError, match="invalid base-7 digit: '9'"):
            parse_base7("9")

    def test_empty_string(self):
        with pytest.raises(ValueError, match="empty"):
            parse_base7("")

    def test_max_word(self):
        max_base7 = "6" * 12
        assert parse_base7(max_base7) == MAX_WORD

    def test_overflow(self):
        # 13 septits — too large
        with pytest.raises(ValueError, match="exceeds"):
            parse_base7("1" + "0" * 12)


class TestParseDecimal:
    def test_zero(self):
        assert parse_decimal("0") == 0

    def test_ten(self):
        assert parse_decimal("10") == 10

    def test_max_word(self):
        assert parse_decimal(str(MAX_WORD)) == MAX_WORD

    def test_overflow(self):
        with pytest.raises(ValueError, match="exceeds"):
            parse_decimal(str(MAX_WORD + 1))

    def test_empty(self):
        with pytest.raises(ValueError, match="empty"):
            parse_decimal("")


class TestFormatBase7:
    def test_zero(self):
        assert format_base7(0) == "0"

    def test_six(self):
        assert format_base7(6) == "6"

    def test_seven_is_10(self):
        assert format_base7(7) == "10"

    def test_thirteen_is_16(self):
        assert format_base7(13) == "16"

    def test_forty_nine_is_100(self):
        assert format_base7(49) == "100"

    def test_roundtrip(self):
        for n in [0, 1, 6, 7, 13, 49, 342, 1000, 16806]:
            assert parse_base7(format_base7(n)) == n

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="negative"):
            format_base7(-1)


class TestValidateWord:
    def test_zero(self):
        assert validate_word(0) == 0

    def test_max(self):
        assert validate_word(MAX_WORD) == MAX_WORD

    def test_negative(self):
        with pytest.raises(ValueError):
            validate_word(-1)

    def test_overflow(self):
        with pytest.raises(ValueError):
            validate_word(MAX_WORD + 1)
