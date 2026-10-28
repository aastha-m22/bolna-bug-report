"""
Repro for Bug 3: a fully-configured non-OpenAI pipeline still requires
OPENAI_API_KEY.

This builds a complete, valid task (LLM + transcriber + synthesizer, all
configured for non-OpenAI providers: Groq for the LLM, Deepgram for STT,
ElevenLabs for TTS) and still fails with
`openai.OpenAIError: Missing credentials ... set the OPENAI_API_KEY
environment variable`.

Root cause: StreamingContextualAgent.__init__ (bolna/agent_types/
contextual_conversational_agent.py) always builds a second, internal
"conversation completion" LLM via `OpenAiLLM(...)`, regardless of which
provider the task's main LLM is configured to use. The same
unconditional `OpenAiLLM(...)` pattern also appears in
knowledgebase_agent.py. This silently defeats any attempt to run Bolna
entirely on a free/non-OpenAI provider.
"""

import asyncio
import os

os.environ.setdefault("LITELLM_MODEL_API_KEY", "dummy-key-not-used-before-crash")
os.environ.setdefault("ELEVENLABS_API_KEY", "dummy-key-not-used-before-crash")
# Deliberately NOT setting OPENAI_API_KEY, to demonstrate it's required
# even though nothing in this config asks for OpenAI.

from bolna.agent_manager import AssistantManager
from bolna.models import LlmAgent, Transcriber, Synthesizer, ToolsConfig, ToolsChainModel, Task


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
    synthesizer = Synthesizer(
        provider="elevenlabs",
        provider_config={"voice": "Rachel", "voice_id": "21m00Tcm4TlvDq8ikWAM", "model": "eleven_turbo_v2_5"},
        stream=False,
        audio_format="wav",
    )

    tools_config = ToolsConfig(
        llm_agent=llm_agent,
        transcriber=transcriber,
        synthesizer=synthesizer,
        input={"format": "wav", "provider": "default"},
        output={"format": "wav", "provider": "default"},
    )
    toolchain = ToolsChainModel(execution="parallel", pipelines=[["transcriber", "llm", "synthesizer"]])
    task = Task(tools_config=tools_config, toolchain=toolchain, task_type="conversation").model_dump()

    agent_config = {"agent_name": "openai_dependency_repro", "tasks": [task]}
    manager = AssistantManager(agent_config, ws=None, input_queue=None, output_queue=None)

    # Raises openai.OpenAIError here, even though every provider configured
    # above is non-OpenAI.
    async for index, task_output in manager.run():
        print("OUTPUT:", task_output)


if __name__ == "__main__":
    asyncio.run(main())
