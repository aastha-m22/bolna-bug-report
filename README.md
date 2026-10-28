# Bolna Quickstart Bug Report

While evaluating [Bolna](https://github.com/bolna-ai/bolna) (an open-source, MIT-licensed
voice AI agent framework) for a personal project, I found that its documented quickstart
API doesn't actually work out of the box -- it fails before any LLM/STT/TTS call is made,
for three separate reasons. This repo has minimal, self-contained repro scripts and full
root-cause analysis for each.

See [`ISSUE.md`](./ISSUE.md) for the full write-up (tracebacks, root causes, suggested
fixes) -- that's the version posted to [the upstream issue tracker](https://github.com/bolna-ai/bolna/issues).

## Background

I'm Aastha Mahajan, a final-year Robotics & AI student at Thapar Institute of Engineering
& Technology. I build RAG/LLM and voice-AI systems, and wanted to build a hands-on demo on
top of Bolna's open-source framework (matching the approach I've used for a few other
Indian AI companies' APIs/models). Rather than finding a working demo, I found that their
own quickstart crashes -- so instead of a demo, this repo is the debugging trail: three
reproducible bugs, each isolated to a minimal script, with exact tracebacks and root
causes traced into Bolna's source.

Portfolio: https://aastha-portfolio-steel.vercel.app/

## Files

| File | What it does |
|---|---|
| `ISSUE.md` | The full bug report (what gets posted upstream) |
| `repro_1_text_only_crash.py` | Reproduces the README's text-only quickstart crashing immediately |
| `repro_2_missing_synthesizer_crash.py` | Reproduces a crash when a task has no synthesizer configured |
| `repro_3_hardcoded_openai_dependency.py` | Reproduces an `OPENAI_API_KEY` requirement even in an all-non-OpenAI pipeline |
| `requirements.txt` | Just `bolna` |

## Running the repros yourself

```bash
pip install bolna
python repro_1_text_only_crash.py
python repro_2_missing_synthesizer_crash.py
python repro_3_hardcoded_openai_dependency.py
```

Each one crashes on its own, with no real API keys needed -- the crashes happen before
any network call is made (dummy placeholder values are set via `os.environ.setdefault`
just so the code reaches the buggy line without an unrelated `KeyError`/`None` on the
env-var lookup itself).

Tested against `bolna==0.11.10` on Python 3.11.

## Note on scope

This isn't a criticism of the project -- Bolna's underlying architecture (pluggable
transcriber/LLM/synthesizer pipeline, support for Groq/Anthropic/Sarvam/Deepgram/
ElevenLabs and others via LiteLLM) is exactly the kind of flexible, open voice-AI
framework I wanted to build on. These are three concrete, fixable bugs in a fast-moving,
actively-developed project (new PyPI releases multiple times a week) -- I'd be glad to
turn the suggested fixes into a PR if that's useful.
