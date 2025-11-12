# AgentBeats Finance Track

Scaffolding for the FutureBench-Finance evaluator (green agent) and predictor (purple agent).

## Getting Started

1. Create a virtual environment and install dependencies:
   ```bash
   uv venv && source .venv/bin/activate
   pip install -e .
   ```
2. Run the CLI help:
   ```bash
   agentbeats --help
   ```

## CLI workflows

- Generate fresh purple-agent fixture predictions (reads `data/fixtures/resolutions/sample_events.jsonl`, writes JSONL under `data/fixtures/predictions/`):
  ```bash
  agentbeats run-predictor
  ```
- Evaluate any predictions/resolutions pair using the MVP scorer:
  ```bash
  agentbeats run-evaluator \
    --predictions-path data/fixtures/predictions/generated_predictions.jsonl \
    --resolutions-path data/fixtures/resolutions/sample_resolutions.jsonl
  ```

See `docs/evaluator-plan.md` and `docs/purple-agent-responsibilities.md` for the roadmap and predictor contract.
