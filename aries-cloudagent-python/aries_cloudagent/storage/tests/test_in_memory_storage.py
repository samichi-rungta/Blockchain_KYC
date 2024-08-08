import pytest

from aries_cloudagent.tests import mock

from ...core.in_memory import InMemoryProfile
from ...storage.error import (
    StorageDuplicateError,
    StorageError,
    StorageNotFoundError,
    StorageSearchError,
)
from ...storage.in_memory import InMemoryStorage, tag_query_match, tag_value_match
from ...storage.record import StorageRecord


@pytest.fixture()
def store():
    profile = InMemoryProfile.test_profile()
    yield InMemoryStorage(profile)


@pytest.fixture()
def store_search():
    profile = InMemoryProfile.test_profile()
    yield InMemoryStorage(profile)


class TestInMemoryStorage:
    def test_repr(self, store):
        assert store.__class__.__name__ in str(store)

    @pytest.mark.asyncio
    async def test_add_required(self, store):
        with pytest.raises(StorageError):
            await store.add_record(None)

    @pytest.mark.asyncio
    async def test_add_id_required(self, store, record_factory):
        record = record_factory()._replace(id=None)
        with pytest.raises(StorageError):
            await store.add_record(record)

    @pytest.mark.asyncio
    async def test_retrieve_missing(self, store, missing: StorageRecord):
        with pytest.raises(StorageNotFoundError):
            await store.get_record(missing.type, missing.id)

    @pytest.mark.asyncio
    async def test_add_retrieve(self, store, record_factory):
        record = record_factory()
        await store.add_record(record)
        result = await store.get_record(record.type, record.id)
        assert result
        assert result.id == record.id
        assert result.type == record.type
        assert result.value == record.value
        assert result.tags == record.tags

        with pytest.raises(StorageDuplicateError):
            await store.add_record(record)

    @pytest.mark.asyncio
    async def test_delete(self, store, record_factory):
        record = record_factory()
        await store.add_record(record)
        await store.delete_record(record)
        with pytest.raises(StorageNotFoundError):
            await store.get_record(record.type, record.id)

    @pytest.mark.asyncio
    async def test_delete_missing(self, store, missing: StorageRecord):
        with pytest.raises(StorageNotFoundError):
            await store.delete_record(missing)

    @pytest.mark.asyncio
    async def test_update_record(self, store, record_factory):
        init_value = "a"
        init_tags = {"a": "a", "b": "b"}
        upd_value = "b"
        upd_tags = {"a": "A", "c": "C"}
        record = record_factory(init_tags)._replace(value=init_value)
        await store.add_record(record)
        assert record.value == init_value
        assert record.tags == init_tags
        await store.update_record(record, upd_value, upd_tags)
        result = await store.get_record(record.type, record.id)
        assert result.value == upd_value
        assert result.tags == upd_tags

    @pytest.mark.asyncio
    async def test_update_missing(self, store, missing: StorageRecord):
        with pytest.raises(StorageNotFoundError):
            await store.update_record(missing, missing.value, {})

    @pytest.mark.asyncio
    async def test_find_record(self, store, record_factory):
        record = record_factory()
        await store.add_record(record)

        # search with find_record
        found = await store.find_record(record.type, {}, None)
        assert found
        assert found.id == record.id
        assert found.type == record.type
        assert found.value == record.value
        assert found.tags == record.tags

        # search again with find_record on no rows
        with pytest.raises(StorageNotFoundError):
            _ = await store.find_record("NOT-MY-TYPE", {}, None)

        # search again with find_row on multiple rows
        record = record_factory()
        await store.add_record(record)
        with pytest.raises(StorageDuplicateError):
            await store.find_record(record.type, {}, None)

    @pytest.mark.asyncio
    async def test_find_all(self, store, record_factory):
        record = record_factory()
        await store.add_record(record)

        # search
        rows = await store.find_all_records(record.type, {}, None)
        assert len(rows) == 1
        found = rows[0]
        assert found.id == record.id
        assert found.type == record.type
        assert found.value == record.value
        assert found.tags == record.tags

    @pytest.mark.asyncio
    async def test_find_paginated_records(self, store, record_factory):
        stored_records = [record_factory(tags={"index": str(i)}) for i in range(10)]
        for record in stored_records:
            await store.add_record(record)

        # retrieve first 5 records
        rows_1 = await store.find_paginated_records("TYPE", {}, limit=5, offset=0)
        assert len(rows_1) == 5  # We expect 5 rows to be returned
        assert all(record in stored_records for record in rows_1)  # All records valid

        # retrieve next 5 records
        rows_2 = await store.find_paginated_records("TYPE", {}, limit=5, offset=5)
        assert len(rows_2) == 5
        assert all(record in stored_records for record in rows_2)  # All records valid
        assert all(record not in rows_1 for record in rows_2)  # Not repeating records

        # retrieve with limit greater than available records
        rows_3 = await store.find_paginated_records("TYPE", {}, limit=15, offset=0)
        assert len(rows_3) == 10  # returns all available records
        assert all(record in stored_records for record in rows_3)  # All records valid

        # retrieve with offset beyond available records
        rows_empty = await store.find_paginated_records("TYPE", {}, limit=5, offset=15)
        assert len(rows_empty) == 0

    @pytest.mark.asyncio
    async def test_delete_all(self, store, record_factory):
        record = record_factory({"tag": "one"})
        await store.add_record(record)

        await store.delete_all_records(record.type, {"tag": "two"})
        assert await store.find_record(record.type, {}, None)

        await store.delete_all_records(record.type, {"tag": "one"})
        with pytest.raises(StorageNotFoundError):
            await store.find_record(record.type, {}, None)


class TestInMemoryStorageSearch:
    @pytest.mark.asyncio
    async def test_search(self, store_search, record_factory):
        record = record_factory()
        await store_search.add_record(record)

        # search
        search = store_search.search_records(record.type, {}, None)
        assert search.__class__.__name__ in str(search)
        rows = await search.fetch(100)
        assert len(rows) == 1
        found = rows[0]
        assert found.id == record.id
        assert found.type == record.type
        assert found.value == record.value
        assert found.tags == record.tags
        more = await search.fetch(100)
        assert len(more) == 0

        # search again with fetch-all
        rows = await store_search.find_all_records(record.type, {}, None)
        assert len(rows) == 1

        # search again with with iterator mystery error
        search = store_search.search_records(record.type, {}, None)
        with mock.patch.object(search, "fetch", mock.CoroutineMock()) as mock_fetch:
            mock_fetch.return_value = mock.MagicMock(
                pop=mock.MagicMock(side_effect=IndexError())
            )
            async for row in search:
                pytest.fail("Should not arrive here")

    @pytest.mark.asyncio
    async def test_iter_search(self, store_search, record_factory):
        record = record_factory()
        await store_search.add_record(record)
        count = 0
        search = store_search.search_records(record.type, {}, None)
        async for found in search:
            assert found.id == record.id
            assert found.type == record.type
            assert found.value == record.value
            assert found.tags == record.tags
            count += 1
        assert count == 1

    @pytest.mark.asyncio
    async def test_closed_search(self, store_search):
        search = store_search.search_records("TYPE", {}, None)
        _rows = await search.fetch()
        with pytest.raises(StorageSearchError):
            await search.fetch(100)


class TestInMemoryTagQuery:
    @pytest.mark.asyncio
    async def test_tag_value_match(self, store, record_factory):
        TAGS = {"a": "aardvark", "b": "bear", "z": "0"}
        record = record_factory(TAGS)
        await store.add_record(record)

        assert not tag_value_match(None, {"$neq": "octopus"})
        assert not tag_value_match(TAGS["a"], {"$in": ["cat", "dog"]})
        assert tag_value_match(TAGS["a"], {"$neq": "octopus"})
        assert tag_value_match(TAGS["z"], {"$gt": "-0.5"})
        assert tag_value_match(TAGS["z"], {"$gte": "0"})
        assert tag_value_match(TAGS["z"], {"$lt": "1"})
        assert tag_value_match(TAGS["z"], {"$lte": "0"})

        with pytest.raises(StorageSearchError) as excinfo:
            tag_value_match(TAGS["z"], {"$gt": "-1", "$lt": "1"})
        assert "Unsupported subquery" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_value_match(TAGS["a"], {"$in": "aardvark"})
        assert "Expected list" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_value_match(TAGS["z"], {"$gte": -1})
        assert "Expected string" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_value_match(TAGS["z"], {"$near": "-1"})
        assert "Unsupported match operator" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_tag_query_match(self, store, record_factory):
        TAGS = {"a": "aardvark", "b": "bear", "z": "0"}
        record = record_factory(TAGS)
        await store.add_record(record)

        assert tag_query_match(None, None)
        assert not tag_query_match(None, {"a": "aardvark"})
        assert tag_query_match(TAGS, {"$or": [{"a": "aardvark"}, {"a": "alligator"}]})
        assert tag_query_match(TAGS, {"$not": {"a": "alligator"}})
        assert tag_query_match(TAGS, {"z": {"$gt": "-1"}})

        with pytest.raises(StorageSearchError) as excinfo:
            tag_query_match(TAGS, {"$or": "-1"})
        assert "Expected list" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_query_match(TAGS, {"$not": [{"z": "-1"}, {"z": "1"}]})
        assert "Expected dict for $not filter value" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_query_match(TAGS, {"$and": {"z": "-1"}})
        assert "Expected list for $and filter value" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_query_match(TAGS, {"$near": {"z": "-1"}})
        assert "Unexpected filter operator" in str(excinfo.value)

        with pytest.raises(StorageSearchError) as excinfo:
            tag_query_match(TAGS, {"a": -1})
        assert "Expected string or dict for filter value" in str(excinfo.value)
