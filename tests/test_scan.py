import asyncio

import pytest

from aioelasticsearch import NotFoundError
from aioelasticsearch.helpers import Scan

from tests.utils import populate


def test_scan_initial_raises(loop, es):
    scan = Scan(es)

    with pytest.raises(AssertionError):
        scan.scroll_id

    with pytest.raises(AssertionError):
        scan.total

    with pytest.raises(AssertionError):
        scan.has_more

    with pytest.raises(AssertionError):
        next(scan)

    with pytest.raises(AssertionError):
        loop.run_until_complete(scan.search())


@pytest.mark.parametrize('scroll_size', [
    1,
    5,
    7,
    10,
    15,
])
@pytest.mark.run_loop
@asyncio.coroutine
def test_scan_equal_chunks(loop, es, scroll_size):
    index = 'test_aioes'
    doc_type = 'type_1'
    n = 10
    yield from populate(es, index, doc_type, n, loop=loop)

    ids = set()
    data = []
    with Scan(
        es,
        index=index,
        doc_type=doc_type,
        size=scroll_size,
    ) as scan:
        yield from scan.scroll()

        for scroll in scan:
            docs = yield from scroll
            data.append(docs)

            for doc in docs:
                ids.add(doc['_id'])

        # check number of unique doc ids
        assert len(ids) == n == scan.total

    # check number of docs in a scroll
    expected_scroll_sizes = [scroll_size] * (n // scroll_size)
    if n % scroll_size != 0:
        expected_scroll_sizes.append(n % scroll_size)

    scroll_sizes = [len(scroll) for scroll in data]
    assert scroll_sizes == expected_scroll_sizes


@pytest.mark.run_loop
@asyncio.coroutine
def test_scan_has_more(loop, es):
    index = 'test_aioes'
    doc_type = 'type_1'
    n = 10
    scroll_size = 3
    yield from populate(es, index, doc_type, n, loop=loop)

    with Scan(
        es,
        index=index,
        doc_type=doc_type,
        size=scroll_size,
    ) as scan:
        yield from scan.scroll()
        assert scan.has_more

        for scroll in scan:
            yield from scroll

        with pytest.raises(StopIteration):
            next(scan)

        assert not scan.has_more


@pytest.mark.run_loop
@asyncio.coroutine
def test_scan_clear_scroll(loop, es):
    index = 'test_aioes'
    doc_type = 'type_1'
    n = 10
    scroll_size = 3
    yield from populate(es, index, doc_type, n, loop=loop)

    with Scan(
        es,
        index=index,
        doc_type=doc_type,
        size=scroll_size,
    ) as scan:
        yield from scan.scroll()

        yield from scan.clear_scroll()

        with pytest.raises(NotFoundError):
            for scroll in scan:
                yield from scroll

        # run cleared scroll
        with pytest.raises(AssertionError):
            yield from scan.scroll()
