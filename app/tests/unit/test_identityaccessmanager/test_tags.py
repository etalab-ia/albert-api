import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._identityaccessmanager import IdentityAccessManager
from app.utils.exceptions import TagAlreadyExistsException, TagNotFoundException


class TestIdentityAccessManagerTags:
    """Tag management tests extracted from the previous monolithic suite."""

    @pytest.fixture
    def iam(self):
        return IdentityAccessManager()

    @pytest.fixture
    def mock_session(self):
        return AsyncMock(spec=AsyncSession)

    # ----------------------------- Create ---------------------------------
    @pytest.mark.asyncio
    async def test_create_tag_success(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 456
        mock_session.execute.return_value = mock_result

        tag_id = await iam.create_tag(session=mock_session, name="admin")

        assert tag_id == 456
        assert mock_session.execute.call_count == 1
        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_create_tag_already_exists(self, iam, mock_session):
        mock_session.execute.side_effect = IntegrityError(statement="INSERT INTO tag", params={}, orig=Exception("unique constraint"))

        with pytest.raises(TagAlreadyExistsException):
            await iam.create_tag(session=mock_session, name="existing_tag")

        # No rollback in implementation; ensure not called.
        assert mock_session.rollback.call_count == 0

    @pytest.mark.asyncio
    async def test_create_tag_empty_name(self, iam, mock_session):
        """Database-level constraints allow empty strings; validation is schema-side."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = 789
        mock_session.execute.return_value = mock_result

        tag_id = await iam.create_tag(session=mock_session, name="")
        assert tag_id == 789

    # ----------------------------- Delete --------------------------------
    @pytest.mark.asyncio
    async def test_delete_tag_success(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = MagicMock()
        mock_session.execute.return_value = mock_result

        await iam.delete_tag(session=mock_session, tag_id=123)

        assert mock_session.execute.call_count == 2
        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_delete_tag_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = NoResultFound()
        mock_session.execute.return_value = mock_result

        with pytest.raises(TagNotFoundException):
            await iam.delete_tag(session=mock_session, tag_id=999)

    @pytest.mark.asyncio
    async def test_delete_tag_with_user_associations(self, iam, mock_session):
        """CASCADE delete should allow tag removal even if users reference it."""
        mock_result = MagicMock()
        mock_result.scalar_one.return_value = MagicMock()
        mock_session.execute.return_value = mock_result

        await iam.delete_tag(session=mock_session, tag_id=123)

        assert mock_session.execute.call_count == 2
        assert mock_session.commit.call_count == 1

    # ----------------------------- Update --------------------------------
    @pytest.mark.asyncio
    async def test_update_tag_success(self, iam, mock_session):
        mock_result = MagicMock()
        mock_tag = MagicMock(id=123)
        mock_result.scalar_one.return_value = mock_tag
        mock_session.execute.return_value = mock_result

        await iam.update_tag(session=mock_session, tag_id=123, name="updated_tag")

        assert mock_session.execute.call_count == 2  # select + update
        assert mock_session.commit.call_count == 1

    @pytest.mark.asyncio
    async def test_update_tag_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.scalar_one.side_effect = NoResultFound()
        mock_session.execute.return_value = mock_result

        with pytest.raises(TagNotFoundException):
            await iam.update_tag(session=mock_session, tag_id=999, name="new_name")

    @pytest.mark.asyncio
    async def test_update_tag_duplicate_name(self, iam, mock_session):
        """Renaming a tag to an existing name should raise TagAlreadyExistsException."""
        mock_tag_result = MagicMock()
        mock_tag = MagicMock(id=123)
        mock_tag_result.scalar_one.return_value = mock_tag

        call_count = {"n": 0}

        def side_effect(*_args, **_kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return mock_tag_result  # select
            raise IntegrityError(statement="UPDATE tag", params={}, orig=Exception("unique constraint"))

        mock_session.execute.side_effect = side_effect

        with pytest.raises(TagAlreadyExistsException):
            await iam.update_tag(session=mock_session, tag_id=123, name="existing_name")

        # Implementation does not rollback on IntegrityError
        assert mock_session.rollback.call_count == 0

    @pytest.mark.asyncio
    async def test_update_tag_no_name_provided(self, iam, mock_session):
        """Calling update_tag without a new name should be a no-op."""
        mock_result = MagicMock()
        mock_tag = MagicMock(id=123)
        mock_result.scalar_one.return_value = mock_tag
        mock_session.execute.return_value = mock_result

        await iam.update_tag(session=mock_session, tag_id=123, name=None)

        assert mock_session.execute.call_count == 1  # select only
        assert mock_session.commit.call_count == 0

    # ----------------------------- Get -----------------------------------
    @pytest.mark.asyncio
    async def test_get_tags_all_success(self, iam, mock_session):
        mock_result = MagicMock()
        mock_row1 = MagicMock()
        mock_row1._mapping = {"id": 1, "name": "tag1", "created_at": 1000, "updated_at": 1100}
        mock_row2 = MagicMock()
        mock_row2._mapping = {"id": 2, "name": "tag2", "created_at": 2000, "updated_at": 2100}
        mock_result.all.return_value = [mock_row1, mock_row2]
        mock_session.execute.return_value = mock_result

        tags = await iam.get_tags(session=mock_session, offset=5, limit=20, order_by="name", order_direction="desc")

        assert [t.id for t in tags] == [1, 2]

    @pytest.mark.asyncio
    async def test_get_tag_by_id_success(self, iam, mock_session):
        mock_result = MagicMock()
        mock_row = MagicMock()
        mock_row._mapping = {"id": 123, "name": "specific_tag", "created_at": 3000, "updated_at": 3100}
        mock_result.all.return_value = [mock_row]
        mock_session.execute.return_value = mock_result

        tags = await iam.get_tags(session=mock_session, tag_id=123)
        tag = tags[0]

        assert tag.id == 123
        assert tag.name == "specific_tag"

    @pytest.mark.asyncio
    async def test_get_tag_by_id_not_found(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        with pytest.raises(TagNotFoundException):
            await iam.get_tags(session=mock_session, tag_id=999)

    @pytest.mark.asyncio
    async def test_get_tags_empty_result(self, iam, mock_session):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result

        tags = await iam.get_tags(session=mock_session)

        assert tags == []
