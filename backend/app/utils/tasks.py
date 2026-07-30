"""Background task utilities for MotherCare AI.

Enables safe, thread-safe asynchronous task execution from sync and async contexts.
"""
import asyncio
import logging
from typing import Coroutine

logger = logging.getLogger("mothercare-tasks")

_main_loop = None

def set_main_loop(loop: asyncio.AbstractEventLoop):
    global _main_loop
    _main_loop = loop
    logger.info("Captured main event loop for background tasks.")

def run_in_background(coro: Coroutine):
    """
    Schedule a coroutine to run in the background safely from any thread.
    Falls back to executing synchronously if no event loop is running.
    """
    global _main_loop
    if _main_loop and _main_loop.is_running():
        try:
            asyncio.run_coroutine_threadsafe(coro, _main_loop)
            return
        except Exception as e:
            logger.debug("Failed scheduling task via run_coroutine_threadsafe: %s", e)

    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            loop.create_task(coro)
            return
    except RuntimeError:
        pass

    # Fallback loop execution (crucial for tests/scripts running synchronously)
    try:
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        try:
            new_loop.run_until_complete(coro)
        finally:
            new_loop.close()
    except Exception as e:
        logger.warning("Failed executing task in fallback loop: %s", e)
