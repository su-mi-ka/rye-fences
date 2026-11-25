# 形その一: test_ の名を持つが、pytest が拾う物が一つも無い。import されるだけで一度も走らない。
import asyncio


async def run_it():
    await asyncio.sleep(0)
    return "looks like a test, is not"
