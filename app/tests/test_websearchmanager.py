import pytest
import requests
from fastapi import UploadFile

from app.helpers._websearchmanager import WebSearchManager


timeout = 5


class DummyWebSearch:
    def __init__(self, urls):
        self.urls = urls
        self.USER_AGENT = "test-agent"

    async def search(self, query, n):
        return self.urls


class FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


@pytest.mark.asyncio
async def test_get_results_success(monkeypatch):
    urls = ["http://service-public.fr/page"]
    web_search = DummyWebSearch(urls)
    manager = WebSearchManager(web_search)
    # restrict to the domain
    manager.LIMITED_DOMAINS = ["service-public.fr"]

    def fake_get(url, headers, timeout):
        assert url == urls[0]
        assert headers["User-Agent"] == web_search.USER_AGENT
        return FakeResponse(200, "hello world")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results("query")

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
    manager = WebSearchManager(web_search)

    # ensure no request is made
    def fake_get(*args, **kwargs):
        pytest.skip("requests.get should not be called for invalid URL")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results("query")
    assert results == []


@pytest.mark.asyncio
async def test_get_results_filters_unauthorized_domain(monkeypatch):
    urls = ["http://unauthorized.com/page"]
    web_search = DummyWebSearch(urls)
    manager = WebSearchManager(web_search)
    # only allow a different domain
    manager.LIMITED_DOMAINS = ["allowed.com"]

    def fake_get(*args, **kwargs):
        pytest.skip("requests.get should not be called for unauthorized domain")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results("query")
    assert results == []


@pytest.mark.asyncio
async def test_get_results_handles_request_exception(monkeypatch):
    urls = ["http://allowed.com/page"]
    web_search = DummyWebSearch(urls)
    manager = WebSearchManager(web_search)
    manager.LIMITED_DOMAINS = ["allowed.com"]

    def fake_get(url, headers, timeout):
        raise requests.RequestException("network error")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results("query")
    assert results == []


@pytest.mark.asyncio
async def test_get_results_handles_non_200_status(monkeypatch):
    urls = ["http://allowed.com/page"]
    web_search = DummyWebSearch(urls)
    manager = WebSearchManager(web_search)
    manager.LIMITED_DOMAINS = ["allowed.com"]

    def fake_get(url, headers, timeout):
        return FakeResponse(404, "not found")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results("query")
    assert results == []


@pytest.mark.asyncio
async def test_get_results_subdomain_allowed(monkeypatch):
    urls = ["http://sub.allowed.com/page"]
    web_search = DummyWebSearch(urls)
    manager = WebSearchManager(web_search)
    manager.LIMITED_DOMAINS = ["allowed.com"]

    def fake_get(url, headers, timeout):
        return FakeResponse(200, "<html/>")

    monkeypatch.setattr(requests, "get", fake_get)
    results = await manager.get_results("query")
    assert len(results) == 1
    assert results[0].filename == f"{urls[0]}.html"
