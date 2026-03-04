from __future__ import annotations

from polymarket_bot.polymarket.client import PolymarketClient


def test_client_base_url_override() -> None:
    client = PolymarketClient(base_url="https://example.com")
    assert client.base_url == "https://example.com"
    client.close()

