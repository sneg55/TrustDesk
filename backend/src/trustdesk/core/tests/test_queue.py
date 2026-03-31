import asyncio
import contextlib

import pytest

from trustdesk.core.queue import InMemoryQueue


@pytest.fixture
def queue() -> InMemoryQueue:
    return InMemoryQueue()


async def test_publish_and_receive(queue: InMemoryQueue) -> None:
    received: list[dict] = []

    async def consume():
        async for msg in queue.subscribe("proposals"):  # pragma: no branch
            received.append(msg)
            break

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await queue.publish("proposals", {"proposal_id": "prop_001"})
    await asyncio.wait_for(task, timeout=1.0)
    assert received == [{"proposal_id": "prop_001"}]


async def test_separate_channels(queue: InMemoryQueue) -> None:
    received: list[dict] = []

    async def consume():
        async for msg in queue.subscribe("verdicts"):  # pragma: no branch
            received.append(msg)
            break

    task = asyncio.create_task(consume())
    await asyncio.sleep(0.05)
    await queue.publish("proposals", {"wrong": "channel"})
    await queue.publish("verdicts", {"verdict": "APPROVED"})
    await asyncio.wait_for(task, timeout=1.0)
    assert received == [{"verdict": "APPROVED"}]


async def test_publish_no_subscribers_is_noop(queue: InMemoryQueue) -> None:
    """Publishing to a channel with no subscribers raises no error."""
    await queue.publish("empty_channel", {"data": "ignored"})
    assert True


async def test_finally_block_removes_subscriber(queue: InMemoryQueue) -> None:
    """The finally block in subscribe() removes the subscriber queue on exit.

    We verify this by explicitly calling aclose() on the async generator, which
    is the same mechanism used internally by Python when a for-loop is exited
    (break, exception) or the generator is garbage collected.
    """
    gen = queue.subscribe("test_channel")
    first_msg: list[dict] = []

    async def drive():
        async for msg in gen:  # pragma: no branch
            first_msg.append(msg)
            break

    task = asyncio.create_task(drive())
    await asyncio.sleep(0.05)
    assert len(queue._channels["test_channel"]) == 1

    await queue.publish("test_channel", {"ping": True})
    await asyncio.wait_for(task, timeout=1.0)
    assert first_msg == [{"ping": True}]

    # Explicitly close the generator to trigger the finally block
    await gen.aclose()
    assert len(queue._channels["test_channel"]) == 0


async def test_multiple_subscribers_receive_same_message(queue: InMemoryQueue) -> None:
    """All active subscribers on the same channel receive the published message."""
    received_a: list[dict] = []
    received_b: list[dict] = []

    async def consume_a():
        async for msg in queue.subscribe("broadcast"):  # pragma: no branch
            received_a.append(msg)
            break

    async def consume_b():
        async for msg in queue.subscribe("broadcast"):  # pragma: no branch
            received_b.append(msg)
            break

    task_a = asyncio.create_task(consume_a())
    task_b = asyncio.create_task(consume_b())
    await asyncio.sleep(0.05)

    await queue.publish("broadcast", {"event": "all"})
    await asyncio.wait_for(task_a, timeout=1.0)
    await asyncio.wait_for(task_b, timeout=1.0)

    assert received_a == [{"event": "all"}]
    assert received_b == [{"event": "all"}]


async def test_cancellation_triggers_finally(queue: InMemoryQueue) -> None:
    """Cancelling a subscribe task triggers the finally block.

    The task receives one message (covering the loop body) then is cancelled
    while waiting for the next message.
    """

    async def consume_forever():
        async for _msg in queue.subscribe("cancel_channel"):  # pragma: no branch
            pass  # receive messages until cancelled

    task = asyncio.create_task(consume_forever())
    await asyncio.sleep(0.05)
    assert len(queue._channels["cancel_channel"]) == 1

    # Send a message so the loop body (pass) is exercised before cancellation
    await queue.publish("cancel_channel", {"msg": "hello"})
    await asyncio.sleep(0.05)

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    # finally block must have removed the subscriber
    assert len(queue._channels["cancel_channel"]) == 0
