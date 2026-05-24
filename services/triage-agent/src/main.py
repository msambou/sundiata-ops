from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Any

import nats

from .models import IncidentCreated
from .workflow import build_graph, run_triage_workflow

NATS_URL = os.getenv("NATS_URL", "nats://nats-nats.nats.svc.cluster.local:4222")

logger = logging.getLogger(__name__)


async def process_message(compiled_graph: Any, msg: Any) -> None:
    try:
        incident = IncidentCreated.model_validate_json(msg.data)
        await run_triage_workflow(compiled_graph, incident)
        await msg.ack()
    except Exception:
        logger.exception("failed to process incident")
        await msg.nak()


async def main() -> None:
    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, shutdown_event.set)

    nc = await nats.connect(NATS_URL)
    js = nc.jetstream()
    compiled_graph = build_graph(js)

    async def handle_message(msg: Any) -> None:
        await process_message(compiled_graph, msg)

    sub = await js.subscribe(
        "incident.created",
        durable="triage-agent",
        queue="triage-agent",
        cb=handle_message,
    )
    logger.info("triage-agent subscribed to incident.created")

    await shutdown_event.wait()

    logger.info("triage-agent shutting down")
    await sub.unsubscribe()
    await nc.drain()
    await nc.close()


if __name__ == "__main__":
    asyncio.run(main())
