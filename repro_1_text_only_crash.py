"""
Repro for Bug 1: the documented text-only quickstart crashes.

This follows README.md's `examples/text_only_assistant.py` pattern (Assistant +
add_task(enable_textual_input=True), no transcriber/synthesizer) almost verbatim.
It crashes with `TypeError: 'NoneType' object is not subscriptable` before any
LLM call is made -- so this is not an LLM/network/API-key issue.

Only requirement to reproduce: `pip install bolna` and any string for
LITELLM_MODEL_API_KEY (the crash happens before that key is ever used).
"""

import asyncio
import os

os.environ.setdefault("LITELLM_MODEL_API_KEY", "dummy-key-not-used-before-crash")

from bolna.assistant import Assistant
from bolna.models import LlmAgent


async def main():
    assistant = Assistant(name="text_only_repro")

    llm_agent = LlmAgent(
        agent_type="simple_llm_agent",
        agent_flow_type="streaming",
        # Passed as a plain dict, NOT a SimpleLlmAgent(...) instance -- the README's
        # own example passes a SimpleLlmAgent object, which fails Pydantic validation
        # in LlmAgent.validate_llm_config() ("llm_config must be a dict, got ..."),
        # a second, separate bug. Using a dict here isolates bug #1 from that one.
        llm_config={
            "provider": "groq",
            "model": "groq/llama-3.3-70b-versatile",
            "temperature": 0.3,
            "max_tokens": 50,
        },
    )

    assistant.add_task(
        task_type="conversation",
        llm_agent=llm_agent,
        enable_textual_input=True,
    )

    async for chunk in assistant.execute():
        print("CHUNK:", chunk)


if __name__ == "__main__":
    asyncio.run(main())
