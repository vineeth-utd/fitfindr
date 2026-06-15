"""
tests/test_tools.py

Pytest tests for the three FitFindr tools.
LLM-backed tools (suggest_outfit, create_fit_card) have their Groq client
mocked so tests run fully offline.
"""

import pytest
from unittest.mock import patch, MagicMock

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import load_listings, get_example_wardrobe, get_empty_wardrobe


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_item():
    return load_listings()[0]


@pytest.fixture
def example_wardrobe():
    return get_example_wardrobe()


@pytest.fixture
def empty_wardrobe():
    return get_empty_wardrobe()


def _mock_groq(text="A styled outfit suggestion."):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices[0].message.content = text
    return mock_client


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage")
    assert len(results) > 0
    first = results[0]
    for field in ("id", "title", "price"):
        assert field in first


def test_search_no_match_returns_empty_list():
    results = search_listings("xyzzy_no_match_ever")
    assert results == []


def test_search_max_price_filter():
    max_price = 30.0
    results = search_listings("shirt", max_price=max_price)
    for item in results:
        assert item["price"] <= max_price


def test_search_size_filter():
    results = search_listings("jeans", size="M")
    for item in results:
        assert "m" in item["size"].lower()


def test_search_impossible_price_returns_empty_list():
    results = search_listings("vintage", max_price=0)
    assert results == []


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def test_suggest_outfit_empty_wardrobe(sample_item, empty_wardrobe):
    with patch("tools._get_groq_client", return_value=_mock_groq("Style this with slim trousers.")):
        result = suggest_outfit(sample_item, empty_wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_with_wardrobe(sample_item, example_wardrobe):
    with patch("tools._get_groq_client", return_value=_mock_groq("Pair with the Black Skinny Jeans.")):
        result = suggest_outfit(sample_item, example_wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


def test_suggest_outfit_brand_none(sample_item, empty_wardrobe):
    item = dict(sample_item)
    item["brand"] = None
    with patch("tools._get_groq_client", return_value=_mock_groq("Great thrift find.")):
        result = suggest_outfit(item, empty_wardrobe)
    assert isinstance(result, str)
    assert len(result) > 0


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

ERROR_MSG = "Unable to create a fit card because no outfit suggestion was generated."


def test_fit_card_empty_outfit_returns_error(sample_item):
    result = create_fit_card("", sample_item)
    assert result == ERROR_MSG


def test_fit_card_whitespace_outfit_returns_error(sample_item):
    result = create_fit_card("   ", sample_item)
    assert result == ERROR_MSG


def test_fit_card_valid_outfit_returns_caption(sample_item):
    outfit = "Pair these jeans with a white tee and sneakers for a casual look."
    with patch("tools._get_groq_client", return_value=_mock_groq("Thrifted this gem for $38!")):
        result = create_fit_card(outfit, sample_item)
    assert isinstance(result, str)
    assert len(result) > 0


def test_fit_card_brand_none_no_error(sample_item):
    item = dict(sample_item)
    item["brand"] = None
    outfit = "Pair these jeans with a white tee and sneakers for a casual look."
    with patch("tools._get_groq_client", return_value=_mock_groq("Found this on depop for $38.")):
        result = create_fit_card(outfit, item)
    assert isinstance(result, str)
    assert len(result) > 0
