from __future__ import annotations

from backend.agent.nodes.ocr import _is_bad_ocr, _normalize_ocr_text


class TestNormalizeOcrText:
    def test_none_returns_empty(self):
        assert _normalize_ocr_text(None) == ""

    def test_empty_returns_empty(self):
        assert _normalize_ocr_text("") == ""

    def test_whitespace_returns_empty(self):
        assert _normalize_ocr_text("   ") == ""

    def test_sentinel_no_text_detected(self):
        assert _normalize_ocr_text("[NO TEXT DETECTED]") == ""

    def test_sentinel_ocr_failed(self):
        assert _normalize_ocr_text("[OCR FAILED - TEXT UNAVAILABLE]") == ""

    def test_valid_text_passes_through(self):
        assert _normalize_ocr_text("Hello world") == "Hello world"

    def test_strips_whitespace(self):
        assert _normalize_ocr_text("  Hello world  ") == "Hello world"

    def test_strips_leading_code_fence(self):
        assert _normalize_ocr_text("```\nsome text\n```") == "some text"

    def test_strips_triple_backticks_only(self):
        assert _normalize_ocr_text("```\nhello world\n```") == "hello world"


class TestIsBadOcrBasic:
    def test_empty_string(self):
        assert _is_bad_ocr("") is True

    def test_very_short_text(self):
        assert _is_bad_ocr("Hi") is True

    def test_fewer_than_min_words(self):
        assert _is_bad_ocr("yes no maybe") is True

    def test_single_word_repeated(self):
        text = " ".join(["the"] * 20)
        assert _is_bad_ocr(text) is True

    def test_two_words_dominating(self):
        words = ["the", "the", "the", "the", "the", "the", "the", "the", "and", "and"]
        assert _is_bad_ocr(" ".join(words)) is True

    def test_low_unique_ratio(self):
        words = ["abc", "abc", "abc", "abc", "def"]
        text = " ".join(words * 4)
        assert _is_bad_ocr(text) is True

    def test_good_text_passes(self):
        text = "The quick brown fox jumps over the lazy dog near the river bank"
        assert _is_bad_ocr(text) is False

    def test_good_text_with_numbers_and_symbols(self):
        text = "PUMP-101 is RUNNING at 1500 RPM. Temperature is 85.2 C. Pressure is 3.5 bar."
        assert _is_bad_ocr(text) is False

    def test_arabic_text_passes(self):
        text = "\u0647\u0630\u0627 \u0627\u062e\u062a\u0628\u0627\u0631 \u0644\u0644\u0646\u0635 \u0627\u0644\u0639\u0631\u0628\u064a \u0641\u064a \u0627\u0644\u0635\u0648\u0631\u0629"
        assert _is_bad_ocr(text) is False

    def test_arabic_rejected_when_repeated(self):
        text = " ".join(["\u0647\u0630\u0627"] * 15)
        assert _is_bad_ocr(text) is True

    def test_mixed_good_text(self):
        text = "Safety valve PSV-101 set at 200 psig. Inspected on 2024-01-15. Next inspection due 2025-01-15."
        assert _is_bad_ocr(text) is False

    def test_exactly_at_threshold(self):
        words = ["a"] * 6 + ["b", "c", "d", "e"]
        text = " ".join(words)
        assert _is_bad_ocr(text) is False

    def test_just_above_threshold(self):
        words = ["a"] * 7 + ["b", "c", "d"]
        text = " ".join(words)
        assert _is_bad_ocr(text) is True


class TestIsBadOcrModelMismatch:
    def test_model_mismatch_triggers_bad(self):
        text = "Safety valve PSV-101 set at 200 psig. Inspected on 2024-01-15. Next due."
        assert _is_bad_ocr(text) is False
        assert _is_bad_ocr(
            text,
            expected_model="gemma4:12b",
            cached_model="joe-speedboat/Gemma-4-Uncensored-HauhauCS-Aggressive:e4b",
        ) is True

    def test_model_match_passes(self):
        text = "Safety valve PSV-101 set at 200 psig. Inspected on 2024-01-15. Next due."
        assert _is_bad_ocr(
            text,
            expected_model="gemma4:12b",
            cached_model="gemma4:12b",
        ) is False

    def test_no_model_args_ignores(self):
        text = "Safety valve PSV-101 set at 200 psig. Inspected on 2024-01-15. Next due."
        assert _is_bad_ocr(text) is False


class TestIsBadOcrReal11pngFailure:
    def test_11png_meta_commentary(self):
        text = "[\n:\n] \n(The text is mostly composed of single characters or very short words/symbols)"
        norm = _normalize_ocr_text(text)
        assert _is_bad_ocr(norm) is True

    def test_11png_with_code_fence(self):
        text = "```\n[\n:\n] \n(The text is mostly composed of single characters or very short words/symbols)\n```"
        norm = _normalize_ocr_text(text)
        assert _is_bad_ocr(norm) is True

    def test_1png_prompt_echo(self):
        text = "[:]\nExtract all text from this image.\n[:]\n[:]\n[:]\n[:]"
        norm = _normalize_ocr_text(text)
        assert _is_bad_ocr(norm) is True

    def test_4png_auto_repeat(self):
        assert _is_bad_ocr("Auto Auto Auto Auto Auto Auto Auto") is True

    def test_auto_multiline(self):
        text = "Auto\nAuto\nAuto\nAuto\nAuto\nAuto\nAuto\nAuto\nAuto\nAuto"
        assert _is_bad_ocr(text) is True

    def test_symbol_only_lines(self):
        text = "[:]\n[:]\n[:]\n[:]\n[:]\n[:]\n[:]\n[:]\n[:]\n[:]\n[:]"
        assert _is_bad_ocr(text) is True

    def test_brackets_colon_lines(self):
        text = "[\n:\n]\n[\n:\n]\n[\n:\n]\n[\n:\n]"
        assert _is_bad_ocr(text) is True


class TestIsBadOcrSubstrings:
    def test_please_upload(self):
        assert _is_bad_ocr("Please upload an image so I can process it") is True

    def test_please_provide(self):
        assert _is_bad_ocr("Please provide an image for OCR processing") is True

    def test_i_cannot_see(self):
        assert _is_bad_ocr("I cannot see any image attached here sorry") is True

    def test_i_cannot_read(self):
        assert _is_bad_ocr("I cannot read the text in this image clearly") is True

    def test_no_meaningful_text(self):
        assert _is_bad_ocr("There is no meaningful text in this image to extract") is True

    def test_no_visible_text(self):
        assert _is_bad_ocr("No visible text was found in the provided image") is True

    def test_unable_to_extract(self):
        assert _is_bad_ocr("Unable to extract text due to low quality") is True

    def test_no_legible_text(self):
        assert _is_bad_ocr("No legible text could be identified in the picture") is True
