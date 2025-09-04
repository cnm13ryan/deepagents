# Testing Guide — Benchmarks (pytest-benchmark)

Benchmark hot paths (e.g., conversation pruning) with `pytest-benchmark`.

## Patterns
- Microbenchmarks:
  ```python
  def test_prune_perf(benchmark):
      from inspect_agents._conversation import prune_messages
      msgs = ...  # build representative message list
      benchmark(lambda: prune_messages(msgs, keep_last=40))
  ```
- Compare runs: `pytest --benchmark-compare`
- Save/inspect: `--benchmark-save=name` and `--benchmark-autosave`

## Tips
- Disable in CI by default unless stability is required.
- Keep inputs realistic and deterministic; avoid network/IO.

## Examples
- Microbenchmark for pruning utility:
  ```python
  from inspect_agents._conversation import prune_messages

  def test_prune_perf(benchmark):
      # construct a small synthetic conversation
      msgs = [{"role":"system"}, {"role":"user"}] + [{"role":"assistant","content":"x"}] * 100
      benchmark(lambda: prune_messages(msgs, keep_last=40))
  ```

## References
- pytest-benchmark docs (usage, compare, saving).
