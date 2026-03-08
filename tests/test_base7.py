"""Tests for base-7 utilities."""

import pytest
from septa.common.base7 import (
    BASE,
    MAX_WORD,
    MEMORY_SIZE,
    SEPTITS_PER_WORD,
    format_balanced,
    format_base7,
    parse_balanced,
    parse_base7,
    parse_decimal,
    validate_word,
)
from septa.common.config import RadixConfig, set_config, reset_config


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


# ---- Task 1: Balanced RadixConfig ----


class TestBalancedConfig:
    """Tests for balanced representation in RadixConfig."""

    def test_balanced_default_false(self):
        cfg = RadixConfig(base=7, word_width=12)
        assert cfg.balanced is False

    def test_balanced_true_odd_base(self):
        cfg = RadixConfig(base=7, word_width=12, balanced=True)
        assert cfg.balanced is True
        assert cfg.base == 7

    def test_balanced_even_base_raises(self):
        with pytest.raises(ValueError, match="odd base"):
            RadixConfig(base=6, word_width=12, balanced=True)
        with pytest.raises(ValueError, match="odd base"):
            RadixConfig(base=2, word_width=4, balanced=True)

    def test_word_min_unsigned(self):
        cfg = RadixConfig(base=7, word_width=2)
        assert cfg.word_min == 0

    def test_word_min_balanced(self):
        # base=7, word_width=2, modulus=49, half=24
        cfg = RadixConfig(base=7, word_width=2, balanced=True)
        assert cfg.word_min == -24

    def test_word_max_unsigned(self):
        cfg = RadixConfig(base=7, word_width=2)
        assert cfg.word_max == 48  # 49 - 1

    def test_word_max_balanced(self):
        cfg = RadixConfig(base=7, word_width=2, balanced=True)
        assert cfg.word_max == 24

    def test_bool_true_unsigned_base7(self):
        cfg = RadixConfig(base=7, word_width=12)
        assert cfg.bool_true == 6

    def test_bool_true_balanced_base7(self):
        cfg = RadixConfig(base=7, word_width=12, balanced=True)
        assert cfg.bool_true == 3  # (7-1)//2

    def test_bool_true_balanced_base3(self):
        cfg = RadixConfig(base=3, word_width=3, balanced=True)
        assert cfg.bool_true == 1  # (3-1)//2

    def test_wrap_word_unsigned(self):
        cfg = RadixConfig(base=7, word_width=2)
        # modulus = 49
        assert cfg.wrap_word(0) == 0
        assert cfg.wrap_word(48) == 48
        assert cfg.wrap_word(49) == 0
        assert cfg.wrap_word(50) == 1
        assert cfg.wrap_word(-1) == 48

    def test_wrap_word_balanced(self):
        # base=7, word_width=2, modulus=49, half=24, range [-24, 24]
        cfg = RadixConfig(base=7, word_width=2, balanced=True)
        assert cfg.wrap_word(0) == 0
        assert cfg.wrap_word(24) == 24
        assert cfg.wrap_word(25) == -24
        assert cfg.wrap_word(-24) == -24
        assert cfg.wrap_word(-25) == 24
        assert cfg.wrap_word(1) == 1
        assert cfg.wrap_word(-1) == -1

    def test_wrap_word_balanced_base3(self):
        # base=3, word_width=3, modulus=27, half=13, range [-13, 13]
        cfg = RadixConfig(base=3, word_width=3, balanced=True)
        assert cfg.wrap_word(0) == 0
        assert cfg.wrap_word(13) == 13
        assert cfg.wrap_word(14) == -13
        assert cfg.wrap_word(-13) == -13
        assert cfg.wrap_word(-14) == 13


# ---- Task 2: Balanced format/parse ----


class TestBalancedFormat:
    """Tests for format_balanced()."""

    def setup_method(self):
        set_config(RadixConfig(base=7, word_width=12, balanced=True))

    def teardown_method(self):
        reset_config()

    def test_format_zero(self):
        assert format_balanced(0) == "0"

    def test_format_small_positive(self):
        assert format_balanced(3) == "3"

    def test_format_needs_carry(self):
        # 5 = 1*7 + (-2), so "1B"
        assert format_balanced(5) == "1B"

    def test_format_negative(self):
        # -5 = (-1)*7 + 2, so "A2"
        assert format_balanced(-5) == "A2"

    def test_format_negative_one(self):
        assert format_balanced(-1) == "A"

    def test_format_seven(self):
        assert format_balanced(7) == "10"

    def test_format_base3(self):
        set_config(RadixConfig(base=3, word_width=3, balanced=True))
        # 5 = 1*9 + (-1)*3 + (-1)*1, so "1TT"
        assert format_balanced(5) == "1TT"


class TestBalancedParse:
    """Tests for parse_balanced()."""

    def setup_method(self):
        set_config(RadixConfig(base=7, word_width=12, balanced=True))

    def teardown_method(self):
        reset_config()

    def test_parse_zero(self):
        assert parse_balanced("0") == 0

    def test_parse_positive_digit(self):
        assert parse_balanced("3") == 3

    def test_parse_with_negative_digit(self):
        # "1B" = 1*7 + (-2) = 5
        assert parse_balanced("1B") == 5

    def test_parse_negative(self):
        # "A2" = (-1)*7 + 2 = -5
        assert parse_balanced("A2") == -5

    def test_parse_base3(self):
        set_config(RadixConfig(base=3, word_width=3, balanced=True))
        # "1TT" = 1*9 + (-1)*3 + (-1)*1 = 5
        assert parse_balanced("1TT") == 5

    def test_roundtrip(self):
        for val in [0, 1, -1, 3, -3, 5, -5, 7, -7, 24, -24]:
            assert parse_balanced(format_balanced(val)) == val
