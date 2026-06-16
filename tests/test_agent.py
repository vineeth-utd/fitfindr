"""
tests/test_agent.py

Integration tests for run_agent() in agent.py.
All offline tests patch the three tool functions in the agent module namespace
so no Groq API key is required.

Live smoke test at the bottom is skipped automatically unless GROQ_API_KEY
is set in the environment.
"""

import os
import pytest
from unittest.mock import patch

from agent import run_agent
from utils.data_loader import get_example_wardrobe


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def fake_item():
    return {"id": "t1", "title": "Vintage Graphic Tee", "price": 20.0, "size": "M", "brand": "Hanes"}


@pytest.fixture
def fake_wardrobe():
    return get_example_wardrobe()


# ── Integration tests (offline) ───────────────────────────────────────────────

def test_happy_path_session_fully_populated(fake_item, fake_wardrobe):
    with patch("agent.search_listings", return_value=[fake_item]), \
         patch("agent.suggest_outfit", return_value="Pair with black jeans and white sneakers."), \
         patch("agent.create_fit_card", return_value="Thrifted this gem for $20!"):
        session = run_agent("vintage tee size M under $30", fake_wardrobe)

    assert session["error"] is None
    assert session["search_results"] == [fake_item]
    assert session["selected_item"] == fake_item
    assert session["outfit_suggestion"] == "Pair with black jeans and white sneakers."
    assert session["fit_card"] == "Thrifted this gem for $20!"


def test_no_results_stops_early(fake_wardrobe):
    with patch("agent.search_listings", return_value=[]), \
         patch("agent.suggest_outfit") as mock_suggest, \
         patch("agent.create_fit_card") as mock_fit_card:
        session = run_agent("designer ballgown size XXS under $5", fake_wardrobe)

    assert session["error"] is not None
    assert session["selected_item"] is None
    assert session["outfit_suggestion"] is None
    assert session["fit_card"] is None
    mock_suggest.assert_not_called()
    mock_fit_card.assert_not_called()


def test_state_flows_between_tools(fake_item, fake_wardrobe):
    outfit_text = "Pair with black jeans and white sneakers."

    with patch("agent.search_listings", return_value=[fake_item]), \
         patch("agent.suggest_outfit", return_value=outfit_text) as mock_suggest, \
         patch("agent.create_fit_card", return_value="Fit card text.") as mock_fit_card:
        run_agent("vintage tee size M under $30", fake_wardrobe)

    mock_suggest.assert_called_once_with(fake_item, fake_wardrobe)
    mock_fit_card.assert_called_once_with(outfit_text, fake_item)


def test_empty_outfit_suggestion_stops_early(fake_item, fake_wardrobe):
    with patch("agent.search_listings", return_value=[fake_item]), \
         patch("agent.suggest_outfit", return_value=""), \
         patch("agent.create_fit_card") as mock_fit_card:
        session = run_agent("vintage tee size M under $30", fake_wardrobe)

    assert session["error"] is not None
    assert session["fit_card"] is None
    mock_fit_card.assert_not_called()


def test_query_parsing_extracts_size_and_price(fake_item, fake_wardrobe):
    with patch("agent.search_listings", return_value=[fake_item]), \
         patch("agent.suggest_outfit", return_value="Great look."), \
         patch("agent.create_fit_card", return_value="Fit card."):
        session = run_agent("vintage tee size M under $30", fake_wardrobe)

    assert session["parsed"]["size"] == "M"
    assert session["parsed"]["max_price"] == 30.0


def test_query_with_no_price_sets_max_price_none(fake_item, fake_wardrobe):
    with patch("agent.search_listings", return_value=[fake_item]), \
         patch("agent.suggest_outfit", return_value="Great look."), \
         patch("agent.create_fit_card", return_value="Fit card."):
        session = run_agent("vintage tee size M", fake_wardrobe)

    assert session["parsed"]["max_price"] is None


# ── Live smoke test (requires GROQ_API_KEY) ───────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set — skipping live smoke test",
)
def test_live_smoke():
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    assert session["error"] is None
    assert isinstance(session["fit_card"], str)
    assert len(session["fit_card"]) > 0
