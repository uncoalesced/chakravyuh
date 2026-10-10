# Live dashboard (Jammy)

Shows a call as it happens: persona state, the conversation, captured details with their format check, the caller
time counter (labelled SIMULATED, cost is illustrative) and the report at the end.

```
pip install -e ".[dashboard]"                  # websockets
cd dashboard/web && npm install && npm run build && cd ../..
python dashboard/server.py --corpus digital_arrest --speed 2 --loop
```
Open http://127.0.0.1:8000. For front-end work, `npm run dev` in `dashboard/web` serves on :5173 with hot reload
and talks to the same backend (`?ws=ws://host:port` overrides the feed URL).

Sources:
- `--corpus <id>`: text-only replay of a corpus script at its own pace. No models needed; the safe demo path.
- `--wav a.wav b.wav ...`: the full audio pipeline (`chakravyuh.pipeline.run_pipeline`) over recorded clips. Needs
  the `audio` extra, the Silero model and a Piper voice (see `bench/README.md`).

Events follow `docs/CONTRACTS.md`; the backend adds the 1 Hz `metrics` event. Both servers bind to 127.0.0.1 only,
because the feed carries captured identifiers.
