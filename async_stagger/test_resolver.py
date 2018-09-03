import asyncio
import itertools
import socket
from typing import AsyncIterable, List, Iterable, Iterator

import pytest

from . import resolver


IPV6_ADDRINFOS = [
    (socket.AF_INET6, 0, 0, '', ('2001:db8::1', 1)),
    (socket.AF_INET6, 0, 0, '', ('2001:db8::2', 2)),
    (socket.AF_INET6, 0, 0, '', ('2001:db8::3', 3)),
    (socket.AF_INET6, 0, 0, '', ('2001:db8::4', 4)),
]

IPV4_ADDRINFOS = [
    (socket.AF_INET, 0, 0, '', ('192.0.2.1', 1)),
    (socket.AF_INET, 0, 0, '', ('192.0.2.2', 2)),
    (socket.AF_INET, 0, 0, '', ('192.0.2.3', 3)),
    (socket.AF_INET, 0, 0, '', ('192.0.2.4', 4)),
]


async def list_from_aiter(
        aiterable: AsyncIterable,
        delay: float = 0,
) -> List:
    new_list = []
    async for item in aiterable:
        await asyncio.sleep(delay)
        new_list.append(item)
    return new_list


def roundrobin(*iters: Iterable) -> Iterator:
    # Note: iters should not contain None
    return (a for a in itertools.chain.from_iterable(
                itertools.zip_longest(*iters)
            ) if a is not None)


@pytest.mark.asyncio
async def test_async_resolver_gai_empty(
        event_loop: asyncio.AbstractEventLoop, mocker):

    async def empty_gai(*args, **kwargs):
        return []

    mocker.patch.object(event_loop, 'getaddrinfo', side_effect=empty_gai)

    with pytest.raises(OSError):
        await list_from_aiter(resolver.async_builtin_resolver('localhost', 80))


@pytest.mark.asyncio
async def test_async_resolver_gai_exc(
        event_loop: asyncio.AbstractEventLoop, mocker):

    async def empty_gai(*args, **kwargs):
        raise socket.gaierror

    mocker.patch.object(event_loop, 'getaddrinfo', side_effect=empty_gai)

    with pytest.raises(OSError):
        await list_from_aiter(resolver.async_builtin_resolver('localhost', 80))


@pytest.mark.asyncio
async def test_async_resolver_ipv6_exc(
        event_loop: asyncio.AbstractEventLoop, mocker):

    async def mock_gai(host, port, *, family=0, type=0, proto=0, flags=0):
        if family == socket.AF_INET:
            return IPV4_ADDRINFOS
        else:
            raise socket.gaierror

    mocker.patch.object(event_loop, 'getaddrinfo', side_effect=mock_gai)

    infos = await list_from_aiter(
        resolver.async_builtin_resolver('localhost', 80))
    assert infos == IPV4_ADDRINFOS


@pytest.mark.asyncio
async def test_async_resolver_ipv4_exc(
        event_loop: asyncio.AbstractEventLoop, mocker):

    async def mock_gai(host, port, *, family=0, type=0, proto=0, flags=0):
        if family == socket.AF_INET6:
            return IPV6_ADDRINFOS
        else:
            raise socket.gaierror

    mocker.patch.object(event_loop, 'getaddrinfo', side_effect=mock_gai)

    infos = await list_from_aiter(
        resolver.async_builtin_resolver('localhost', 80))
    assert infos == IPV6_ADDRINFOS


@pytest.mark.asyncio
async def test_async_resolver_both(
        event_loop: asyncio.AbstractEventLoop, mocker):

    async def mock_gai(host, port, *, family=0, type=0, proto=0, flags=0):
        if family == socket.AF_INET6:
            return IPV6_ADDRINFOS
        else:
            return IPV4_ADDRINFOS

    mocker.patch.object(event_loop, 'getaddrinfo', side_effect=mock_gai)

    infos = await list_from_aiter(
        resolver.async_builtin_resolver('localhost', 80),
        0.25,
    )
    assert infos == list(roundrobin(IPV6_ADDRINFOS, IPV4_ADDRINFOS))


@pytest.mark.asyncio
async def test_async_resolver_ipv6_slightly_slow(
        event_loop: asyncio.AbstractEventLoop, mocker):

    async def mock_gai(host, port, *, family=0, type=0, proto=0, flags=0):
        if family == socket.AF_INET:
            return IPV4_ADDRINFOS
        else:
            await asyncio.sleep(0.3)
            return IPV6_ADDRINFOS

    mocker.patch.object(event_loop, 'getaddrinfo', side_effect=mock_gai)

    infos = await list_from_aiter(
        resolver.async_builtin_resolver('localhost', 80, resolution_delay=0.5),
        0.25,
    )
    assert infos == list(roundrobin(IPV6_ADDRINFOS, IPV4_ADDRINFOS))


@pytest.mark.asyncio
async def test_async_resolver_ipv6_very_slow(
        event_loop: asyncio.AbstractEventLoop, mocker):

    async def mock_gai(host, port, *, family=0, type=0, proto=0, flags=0):
        if family == socket.AF_INET:
            return IPV4_ADDRINFOS
        else:
            await asyncio.sleep(0.3)
            return IPV6_ADDRINFOS

    mocker.patch.object(event_loop, 'getaddrinfo', side_effect=mock_gai)

    infos = await list_from_aiter(
        resolver.async_builtin_resolver('localhost', 80, resolution_delay=0.05),
        0.25,
    )
    assert infos == list(roundrobin(IPV4_ADDRINFOS, IPV6_ADDRINFOS))


@pytest.mark.asyncio
async def test_async_resolver_ipv6_very_slow_2(
        event_loop: asyncio.AbstractEventLoop, mocker):

    async def mock_gai(host, port, *, family=0, type=0, proto=0, flags=0):
        if family == socket.AF_INET:
            return IPV4_ADDRINFOS
        else:
            await asyncio.sleep(0.3)
            return IPV6_ADDRINFOS

    mocker.patch.object(event_loop, 'getaddrinfo', side_effect=mock_gai)

    infos = await list_from_aiter(
        resolver.async_builtin_resolver('localhost', 80, resolution_delay=0.05),
        0,
    )
    assert infos == IPV4_ADDRINFOS + IPV6_ADDRINFOS


@pytest.mark.asyncio
async def test_async_resolver_fafc(
        event_loop: asyncio.AbstractEventLoop, mocker):

    async def mock_gai(host, port, *, family=0, type=0, proto=0, flags=0):
        if family == socket.AF_INET6:
            return IPV6_ADDRINFOS
        else:
            return IPV4_ADDRINFOS

    mocker.patch.object(event_loop, 'getaddrinfo', side_effect=mock_gai)

    infos = await list_from_aiter(
        resolver.async_builtin_resolver(
            'localhost', 80, first_addr_family_count=2),
        0.1,
    )
    assert infos == [
        IPV6_ADDRINFOS[0],
        IPV6_ADDRINFOS[1],
        IPV4_ADDRINFOS[0],
        IPV6_ADDRINFOS[2],
        IPV4_ADDRINFOS[1],
        IPV6_ADDRINFOS[3],
        IPV4_ADDRINFOS[2],
        IPV4_ADDRINFOS[3],
    ]


@pytest.mark.asyncio
async def test_async_resolver_family_af_inet(
        event_loop: asyncio.AbstractEventLoop, mocker):

    async def mock_gai(host, port, *, family=0, type=0, proto=0, flags=0):
        if family == socket.AF_INET6:
            return IPV6_ADDRINFOS
        else:
            return IPV4_ADDRINFOS

    mocker.patch.object(event_loop, 'getaddrinfo', side_effect=mock_gai)

    infos = await list_from_aiter(
        resolver.async_builtin_resolver('localhost', 80, family=socket.AF_INET),
        0.25,
    )
    assert infos == IPV4_ADDRINFOS


@pytest.mark.asyncio
async def test_async_resolver_family_af_inet6(
        event_loop: asyncio.AbstractEventLoop, mocker):

    async def mock_gai(host, port, *, family=0, type=0, proto=0, flags=0):
        if family == socket.AF_INET6:
            return IPV6_ADDRINFOS
        else:
            return IPV4_ADDRINFOS

    mocker.patch.object(event_loop, 'getaddrinfo', side_effect=mock_gai)

    infos = await list_from_aiter(
        resolver.async_builtin_resolver(
            'localhost', 80, family=socket.AF_INET6),
        0.25,
    )
    assert infos == IPV6_ADDRINFOS
