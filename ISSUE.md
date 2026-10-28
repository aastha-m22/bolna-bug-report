## Summary

While evaluating `bolna` (v0.11.10, latest on PyPI) for a personal project, I found that the high-level `Assistant` / `add_task()` / `execute()` API shown in the README's quickstart examples (`examples/text_only_assistant.py` and `examples/simple_assistant.py`) does not actually work -- it fails before any LLM/STT/TTS call is made, for three separate reasons. I also found that a fully non-OpenAI pipeline still requires `OPENAI_API_KEY`. Minimal, self-contained repro scripts and full tracebacks for all three are below.

Environment: Python 3.11, `bolna==0.11.10` installed fresh via `pip install bolna`.

---

## Bug 1: `Assistant.add_task()` never stores a configured `transcriber`, and `TaskManager` crashes without one

**Repro:** `repro_1_text_only_crash.py` (follows the README's `text_only_assistant.py` pattern)

**Traceback:**
```
Traceback (most recent call last):
  File "repro_1_text_only_crash.py", line 16, in main
  File ".../bolna/assistant.py", line 49, in execute
    async for index, task_output in self.manager.run():
  File ".../bolna/agent_manager/assistant_manager.py", line 60, in run
    task_manager = TaskManager(
                   ^^^^^^^^^^^^
  File ".../bolna/agent_manager/task_manager.py", line 997, in __init__
    self.__setup_synthesizer(self.llm_config)
  File ".../bolna/agent_manager/task_manager.py", line 1972, in __setup_synthesizer
    self.task_config["tools_config"]["transcriber"]["language"] == DEFAULT_LANGUAGE_CODE
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
TypeError: 'NoneType' object is not subscriptable
```

**Root cause:** in `bolna/assistant.py`, `Assistant.add_task()` has this:

```python
if transcriber is None:
    pipelines.append(["llm"])
    tools_config_args["transcriber"] = transcriber
```

`tools_config_args["transcriber"]` is only ever set when `transcriber is None` -- i.e. it's set to `None` when there's no transcriber, and **never set at all** (so it defaults to whatever `ToolsConfig` defaults to) when a real transcriber *is* passed in. Either way, `TaskManager.__setup_synthesizer` (line 1972) then does an unguarded `self.task_config["tools_config"]["transcriber"]["language"]`, which crashes whenever `transcriber` ends up `None`.

This means the text-only quickstart (no transcriber at all) always crashes here.

**Suggested fix:** in `add_task()`, always set `tools_config_args["transcriber"] = transcriber` regardless of whether it's `None` (so the key exists either way), and in `__setup_synthesizer`, guard the access, e.g.:

```python
transcriber_cfg = self.task_config["tools_config"].get("transcriber")
if transcriber_cfg and transcriber_cfg["language"] == DEFAULT_LANGUAGE_CODE:
    ...
```

---

## Bug 2: `TaskManager.__init__` assumes a synthesizer always exists

**Repro:** `repro_2_missing_synthesizer_crash.py` (builds the task config directly, with a transcriber + LLM but no synthesizer -- a valid "speech in, text out" pipeline shape)

**Traceback:**
```
Traceback (most recent call last):
  File "repro_2_missing_synthesizer_crash.py", line 34, in main
  File ".../bolna/agent_manager/assistant_manager.py", line 60, in run
    task_manager = TaskManager(
                   ^^^^^^^^^^^^
  File ".../bolna/agent_manager/task_manager.py", line 999, in __init__
    self.synthesizer_monitor_task = asyncio.create_task(self.tools["synthesizer"].monitor_connection())
                                                        ~~~~~~~~~~^^^^^^^^^^^^^^^
KeyError: 'synthesizer'
```

**Root cause:** `TaskManager.__init__` unconditionally does `self.tools["synthesizer"].monitor_connection()`, assuming every task has a synthesizer configured. A task with no synthesizer (e.g. STT + LLM only) raises `KeyError` instead of being accepted as a valid configuration.

**Suggested fix:**
```python
if "synthesizer" in self.tools:
    self.synthesizer_monitor_task = asyncio.create_task(self.tools["synthesizer"].monitor_connection())
```

---

## Bug 3: a fully non-OpenAI pipeline still requires `OPENAI_API_KEY`

**Repro:** `repro_3_hardcoded_openai_dependency.py` (full pipeline, every provider set to a non-OpenAI one: `groq` for the LLM, `deepgram` for STT, `elevenlabs` for TTS; `OPENAI_API_KEY` deliberately left unset)

**Traceback:**
```
Traceback (most recent call last):
  ...
  File ".../bolna/agent_manager/task_manager.py", line 2225, in __setup_tasks
    self.tools["llm_agent"] = self.__get_agent_object(llm, agent_type, assistant_config)
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File ".../bolna/agent_manager/task_manager.py", line 2115, in __get_agent_object
    llm_agent = StreamingContextualAgent(llm)
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File ".../bolna/agent_types/contextual_conversational_agent.py", line 19, in __init__
    self.conversation_completion_llm = OpenAiLLM(model=os.getenv("CHECK_FOR_COMPLETION_LLM", llm.model))
                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File ".../bolna/llms/openai_llm.py", line 243, in __init__
    self.async_client = AsyncOpenAI(api_key=llm_key, http_client=http_client)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
openai.OpenAIError: Missing credentials. Please pass an `api_key` ... or set the `OPENAI_API_KEY` ... environment variable.
```

**Root cause:** `StreamingContextualAgent.__init__` (`bolna/agent_types/contextual_conversational_agent.py`, line 19) always builds a second, internal "conversation completion" LLM via a hardcoded `OpenAiLLM(...)` call, regardless of which provider the task's main LLM is configured with. The same pattern appears in `knowledgebase_agent.py` (`__init__`, line 42). This silently requires `OPENAI_API_KEY` even for a pipeline that never otherwise touches OpenAI.

**Suggested fix:** either make the completion-check LLM's provider configurable (e.g. reuse the main `llm`'s provider/config instead of hardcoding `OpenAiLLM`), or make this check opt-in/skippable when no OpenAI key is present.

---

## Why this matters

The README's own quickstart examples (`examples/text_only_assistant.py`, `examples/simple_assistant.py`) hit bug #1 immediately, so a new user following the documented "fastest way to get started" path cannot get a working agent without first discovering and working around these three issues. Happy to open these as separate issues instead of one, or to turn any of the suggested fixes above into a PR if that's useful -- saw in the README that you're looking for maintainers.
