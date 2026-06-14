"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform
    """
    listings = load_listings()

    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]

    if size is not None:
        listings = [l for l in listings if size.lower() in l["size"].lower()]

    keywords = description.lower().split()

    def score_listing(listing):
        parts = [
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
            " ".join(listing["colors"]),
        ]
        if listing["brand"]:
            parts.append(listing["brand"])
        combined = " ".join(parts).lower()
        return sum(1 for kw in keywords if kw in combined)

    scored = [(s, l) for l in listings for s in [score_listing(l)] if s > 0]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [l for _, l in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.
    """
    items = wardrobe.get("items", [])

    colors = ", ".join(new_item.get("colors", []))
    tags = ", ".join(new_item.get("style_tags", []))
    brand = new_item.get("brand") or "N/A"
    item_block = (
        f"Item: {new_item.get('title', '')}\n"
        f"Description: {new_item.get('description', '')}\n"
        f"Category: {new_item.get('category', '')}\n"
        f"Style tags: {tags}\n"
        f"Colors: {colors}\n"
        f"Size: {new_item.get('size', '')}\n"
        f"Condition: {new_item.get('condition', '')}\n"
        f"Price: ${new_item.get('price', 0):.2f}\n"
        f"Brand: {brand}\n"
        f"Platform: {new_item.get('platform', '')}"
    )

    system_message = (
        "You are a helpful fashion stylist for a thrift-shopping assistant. "
        "Give practical, specific, and realistic styling advice. "
        "Use the item's style, colors, and vibe when making recommendations. "
        "Output plain text only — no markdown, no bullet symbols, no headers. "
        "Do not invent wardrobe items that were not provided."
    )

    if not items:
        prompt = (
            f"I just thrifted this item:\n{item_block}\n\n"
            "I don't have other clothes yet. Suggest 1-2 outfit ideas describing what types of "
            "clothes, shoes, or accessories would pair well with this item and what vibe or "
            "occasion each outfit suits. Do not mention specific pieces I own — I have none."
        )
    else:
        wardrobe_lines = []
        for i, piece in enumerate(items, 1):
            parts = []
            for key in ["name", "category", "colors", "style_tags", "notes"]:
                if key in piece:
                    val = piece[key]
                    if isinstance(val, list):
                        val = ", ".join(val)
                    parts.append(str(val))
            line = " | ".join(parts) if parts else str(piece)
            wardrobe_lines.append(f"{i}. {line}")
        wardrobe_list = "\n".join(wardrobe_lines)

        prompt = (
            f"I just thrifted this item:\n{item_block}\n\n"
            f"Here are the clothes I already own:\n{wardrobe_list}\n\n"
            "Suggest 1-2 outfits using my new item and specific pieces from my wardrobe. "
            "Reference each wardrobe piece by name. Do not invent items I did not list."
        )

    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return response.choices[0].message.content


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)
    """
    if not outfit or not outfit.strip():
        return "Unable to create a fit card because no outfit suggestion was generated."

    colors = ", ".join(new_item.get("colors", []))
    tags = ", ".join(new_item.get("style_tags", []))
    brand = new_item.get("brand") or "N/A"
    item_block = (
        f"Item: {new_item.get('title', '')}\n"
        f"Description: {new_item.get('description', '')}\n"
        f"Category: {new_item.get('category', '')}\n"
        f"Style tags: {tags}\n"
        f"Colors: {colors}\n"
        f"Size: {new_item.get('size', '')}\n"
        f"Condition: {new_item.get('condition', '')}\n"
        f"Price: ${new_item.get('price', 0):.2f}\n"
        f"Brand: {brand}\n"
        f"Platform: {new_item.get('platform', '')}"
    )

    system_message = (
        "You are a fashion stylist and social media creator writing Instagram and TikTok "
        "outfit captions for a thrift-shopping app. "
        "Write captions that feel casual, authentic, and personal — like a real OOTD post, "
        "not a product listing or advertisement. "
        "Output plain text only. No markdown, no hashtags, no emojis, no bullet points. "
        "Use natural, shareable wording that captures the outfit vibe in specific terms."
    )

    prompt = (
        f"Here is the thrifted item I found:\n{item_block}\n\n"
        f"Here is the outfit suggestion I'm going for:\n{outfit}\n\n"
        "Write a 2-4 sentence caption for this outfit. Mention the item name exactly once, "
        "the price exactly once, and the platform exactly once — naturally, not as a product "
        "listing. Capture the outfit vibe in specific terms. Keep it casual and personal."
    )

    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt},
        ],
        temperature=1.0,
    )
    return response.choices[0].message.content
