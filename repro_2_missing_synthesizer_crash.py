"""
Repro for Bug 2: a task with a transcriber + LLM but no synthesizer crashes.

This bypasses Assistant.add_task() (see bug #1 and bug #3's writeups for why)
and builds the task config directly, matching what add_task() is meant to
produce. Even with a correctly-shaped config, TaskManager.__init__
unconditionally does `self.tools["synthesizer"].monitor_connection()`,
which raises KeyError when no synthesizer was configured for the task
(a perfectly valid configuration -- e.g. an STT-and-LLM-only pipeline).
"""

import asyncio
import os

os.environ.setdefault("LITELLM_MODEL_API_KEY", "dummy-key-not-used-before-crash")

from bolna.agent_manager import AssistantManager
from bolna.models import LlmAgent, Transcriber, ToolsConfig, ToolsChainModel, Task


async def main():
    llm_agent = LlmAgent(
        agent_type="simple_llm_agent",
        agent_flow_type="streaming",
        llm_config={
            "provider": "groq",
            "model": "groq/llama-3.3-70b-versatile",
            "temperature": 0.3,
            "max_tokens": 50,
        },
    )
    transcriber = Transcriber(provider="deepgram", model="nova-2", stream=False, language="en")

    tools_config = ToolsConfig(
        llm_agent=llm_agent,
        transcriber=transcriber,
        # No synthesizer -- a valid pipeline shape (e.g. speech-in, text-out).
        input={"format": "wav", "provider": "default"},
        output={"format": "wav", "provider": "default"},
    )
    toolchain = ToolsChainModel(execution="parallel", pipelines=[["transcriber", "llm"]])
    task = Task(tools_config=tools_config, toolchain=toolchain, task_type="conversation").model_dump()

    agent_config = {"agent_name": "missing_synth_repro", "tasks": [task]}
    manager = AssistantManager(agent_config, ws=None, input_queue=None, output_queue=None)

    async for index, task_output in manager.run():
        print("OUTPUT:", task_output)


if __name__ == "__main__":
    asyncio.run(main())
