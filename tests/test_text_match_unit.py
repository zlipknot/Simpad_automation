import pytest
from simpad_automation.core.verify import normalize_text, compare_tokens

@pytest.mark.noreport
def test_normalize_basic():
    assert normalize_text("  Unable  to  retrieve  technical  information ") \
           == "unable to retrieve technical information"

@pytest.mark.noreport
def test_compare_tokens_fuzzy_ok():
    target = "Unable to retrieve technical information"
    ocr = "Unable te retrieve technicalinformation"
    assert compare_tokens(target, ocr, ok_ratio=0.7) is True