# Independent Tourist Chatbot QA — v7.2

This suite runs the application **offline with both provider keys disabled**.
It checks routing, state edits, trip stop coverage, privacy, safety fallbacks,
validation, language and multi-turn questions. It is not a test of live Gemini.

From project root after installing `backend/requirements-dev.txt`:

```bash
python qa_chatbot/blackbox_probe.py
python qa_chatbot/acceptance_evaluation.py
```

`blackbox_probe.py` produces 67 API samples in `raw_responses.json`.
`acceptance_evaluation.py` evaluates **52 corrected criteria**, produces
`acceptance_results.json` and exits with code 1 on failure. The original v7
acceptance checks are archived unmodified as `legacy_acceptance_v7.py`.

**Traceability:** The only corrected expectations are Q49 and Q52:
* Q49 previously demanded the word `Hurghada` *after* the user had successfully
  replaced it with `Sharm El Sheikh`. Now it requires the new beach phase and
  the absence of the old city.
* Q52 previously demanded an edit-failure message even though the edit was
  successful. Now it requires a successful state change and no false failure.

The original unmodified checks pass **50/52** because of those contradictory
assertions; the corrected checks pass **52/52** in the tested offline run.

See `docs/V7_2_52_OF_52_QA_AR.md` for limitations and reproduction commands.
Do not publish model API keys or `.env` files.
