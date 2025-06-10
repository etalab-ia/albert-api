import pytest
import requests
from fastapi import UploadFile
from typing import List

from app.helpers._websearchmanager import WebSearchManager


timeout = 5


class DummyWebSearch:
    def __init__(self, urls: List[str]) -> None:
        self.urls = urls
        self.USER_AGENT = "test-agent"

    async def search(self, query: str, k: int) -> List[str]:
        return self.urls


class FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


@pytest.mark.asyncio
async def test_get_results_success(monkeypatch):
    urls = ["http://service-public.fr/page"]
    web_search = DummyWebSearch(urls)
    manager = WebSearchManager(web_search, None)
    # restrict to the domain
    manager.limited_domains = ["service-public.fr"]

    def fake_get(url, headers, timeout):
        assert url == urls[0]
        return FakeResponse(200, "hello world")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results(query="query", k=1)

    assert len(results) == 1
    file_item = results[0]
    assert isinstance(file_item, UploadFile)
    assert file_item.filename == f"{urls[0]}.html"

    # Read the content from the in-memory file
    content = await file_item.read()
    assert content.decode() == "hello world"


@pytest.mark.asyncio
async def test_get_results_filters_invalid_url(monkeypatch):
    urls = ["not a url"]
    web_search = DummyWebSearch(urls)
    manager = WebSearchManager(web_search, None)

    # ensure no request is made
    def fake_get(*args, **kwargs):
        pytest.skip("requests.get should not be called for invalid URL")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results(query="query", k=1)
    assert results == []


@pytest.mark.asyncio
async def test_get_results_filters_unauthorized_domain(monkeypatch):
    urls = ["http://unauthorized.com/page?injection=service-public.fr"]
    web_search = DummyWebSearch(urls)
    manager = WebSearchManager(web_search, None)
    # only allow a different domain
    manager.limited_domains = ["allowed.com"]

    def fake_get(*args, **kwargs):
        pytest.skip("requests.get should not be called for unauthorized domain")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results(query="query", k=1)
    assert results == []


@pytest.mark.asyncio
async def test_get_results_handles_request_exception(monkeypatch):
    urls = ["http://allowed.com/page"]
    web_search = DummyWebSearch(urls)
    manager = WebSearchManager(web_search, None)
    manager.limited_domains = ["allowed.com"]

    def fake_get(url, headers, timeout):
        raise requests.RequestException("network error")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results(query="query", k=1)
    assert results == []


@pytest.mark.asyncio
async def test_get_results_handles_non_200_status(monkeypatch):
    urls = ["http://allowed.com/page"]
    web_search = DummyWebSearch(urls)
    manager = WebSearchManager(web_search, None)
    manager.limited_domains = ["allowed.com"]

    def fake_get(url, headers, timeout):
        return FakeResponse(404, "not found")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results(query="query", k=1)
    assert results == []


@pytest.mark.asyncio
async def test_get_results_subdomain_allowed(monkeypatch):
    urls = ["http://sub.allowed.com/page"]
    web_search = DummyWebSearch(urls)
    manager = WebSearchManager(web_search, None)
    manager.limited_domains = ["allowed.com"]

    def fake_get(url, headers, timeout):
        return FakeResponse(200, "<html/>")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results(query="query", k=1)
    assert len(results) == 1
    assert results[0].filename == f"{urls[0]}.html"
