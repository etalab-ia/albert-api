from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers.models import ModelRegistry
from app.schemas.chunks import Chunk
from app.schemas.search import Search, SearchMethod
from app.helpers._multiagents import MultiAgents
from app.utils.settings import settings


@pytest.mark.asyncio
async def test_search_web_search_disabled_fallback_to_3():
    """
    Tests that if _get_rank returns 4 (web search) but settings.web_search is None,
    the choice falls back to 3 and no web search is performed.
    """
    # 1. Setup Mocks
    multi_agents = MultiAgents(model=MagicMock(spec=ModelRegistry), ranker_model=MagicMock(spec=ModelRegistry))

    mock_doc_search = AsyncMock()
    mock_session = MagicMock(spec=AsyncSession)

    # Mock initial searches
    initial_search_item = Search(
        method=SearchMethod.SEMANTIC,
        chunk=Chunk(id=1, content="Initial content", document_id="doc1", collection_id="col1", metadata={"document_name": "doc_name_1"}),
        score=0.9,
    )
    initial_searches = [initial_search_item]
    prompt_text = "Test prompt"
    k_val = 5

    # 2. Configure settings: Disable web search
    original_web_search_setting = settings.web_search
    settings.web_search = None

    # 3. Mock _get_rank to return choice 4 (request web search)
    with patch("app.helpers._multiagents.MultiAgents._get_rank", new_callable=AsyncMock) as mock_get_rank:
        mock_get_rank.return_value = [4]  # Agent decides to go for web search

        # 4. Call MultiAgents.search
        result_searches = await multi_agents.search(
            doc_search=mock_doc_search,
            searches=initial_searches,
            prompt=prompt_text,
            session=mock_session,
            k=k_val,
        )

        # 5. Assertions
        # Assert _get_rank was called
        mock_get_rank.assert_called_once()

        # Assert doc_search was NOT called for a web search
        web_search_call_found = False
        for call_args in mock_doc_search.call_args_list:
            kwargs = call_args.kwargs
            if kwargs.get("web_search") is True:
                web_search_call_found = True
                break
        assert not web_search_call_found, "doc_search should not have been called with web_search=True"

        # Assert that the choice in metadata is 3
        assert len(result_searches) == 1
        assert result_searches[0].chunk.metadata.get("choice") == 3

    # Restore original settings
    settings.web_search = original_web_search_setting


@pytest.mark.asyncio
async def test_search_web_search_enabled_and_chosen():
    """
    Tests that if _get_rank returns 4 and settings.web_search is enabled,
    a web search is performed.
    """
    multi_agents = MultiAgents(model=MagicMock(spec=ModelRegistry), ranker_model=MagicMock(spec=ModelRegistry))

    mock_doc_search = AsyncMock()
    # Simulate doc_search returning some new searches when called for web_search
    web_search_chunk = Chunk(
        id=1, content="Web search result", document_id="web_doc1", collection_id="web_col1", metadata={"document_name": "web_doc_name_1"}
    )
    web_search_item = Search(chunk=web_search_chunk, score=0.95, method=SearchMethod.SEMANTIC)
    mock_doc_search.return_value = [web_search_item]  # Simulate web search returning a result

    mock_session = MagicMock(spec=AsyncSession)

    initial_search_item = Search(
        method=SearchMethod.SEMANTIC,
        chunk=Chunk(id=1, content="Initial content", document_id="doc1", collection_id="col1", metadata={"document_name": "doc_name_1"}),
        score=0.9,
    )
    initial_searches = [initial_search_item]
    prompt_text = "Test prompt for web search"
    k_val = 3

    original_web_search_setting = settings.web_search
    # Ensure web_search setting is something that evaluates to True (e.g., a dummy config object)
    settings.web_search = MagicMock()

    with patch("app.helpers._multiagents.MultiAgents._get_rank", new_callable=AsyncMock) as mock_get_rank:
        mock_get_rank.return_value = [4]  # Agent decides to go for web search

        result_searches = await multi_agents.search(
            doc_search=mock_doc_search,
            searches=initial_searches,
            prompt=prompt_text,
            session=mock_session,
            k=k_val,
        )

        mock_get_rank.assert_called_once()

        # Assert doc_search was called with web_search=True
        mock_doc_search.assert_called_with(
            session=mock_session,
            collection_ids=[],
            prompt=prompt_text,
            method=SearchMethod.SEMANTIC,
            k=k_val,
            rff_k=5,
            web_search=True,
        )

        assert len(result_searches) == 1
        assert result_searches[0].chunk.id == 1
        # Ensure results from web_search are returned
        assert result_searches[0].chunk.metadata.get("choice") == 4

        from app.helpers._multiagents import _get_explain_choice as actual_get_explain_choice

        expected_desc_for_choice_4 = actual_get_explain_choice()[4]  # Web search is enabled here
        assert result_searches[0].chunk.metadata.get("choice_desc") == expected_desc_for_choice_4

    settings.web_search = original_web_search_setting


# It might be good to also test the _get_explain_choice and _get_prompt_choicer directly
# to ensure their behavior changes based on settings.web_search


def test_get_explain_choice_web_search_disabled():
    original_web_search_setting = settings.web_search
    settings.web_search = None

    from app.helpers._multiagents import _get_explain_choice

    choices = _get_explain_choice()

    assert 4 not in choices

    settings.web_search = original_web_search_setting


def test_get_prompt_choicer_web_search_disabled():
    original_web_search_setting = settings.web_search
    settings.web_search = None

    from app.helpers._multiagents import _get_prompt_choicer

    prompt = _get_prompt_choicer()

    assert "réponds 4" not in prompt  # The option to choose 4 should not be in the prompt
    assert "uniquement 0, 1, 2, 3." in prompt or "uniquement 0, 1, 2, 3\n" in prompt  # Max choice is 3

    settings.web_search = original_web_search_setting


def test_get_prompt_choicer_web_search_enabled():
    original_web_search_setting = settings.web_search
    settings.web_search = MagicMock()  # Enable web search

    from app.helpers._multiagents import _get_prompt_choicer

    prompt = _get_prompt_choicer()

    assert "réponds 4" in prompt  # The option to choose 4 should be in the prompt
    assert "uniquement 0, 1, 2, 3 ou 4." in prompt or "uniquement 0, 1, 2, 3 ou 4\n" in prompt  # Max choice is 4

    settings.web_search = original_web_search_setting
