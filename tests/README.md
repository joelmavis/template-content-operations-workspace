# Tests

`test_content_operations.py` covers blank state, the full content loop, partial metrics, local CSV/XLSX reading, dates, duplicate protection, cumulative snapshots, unknown platforms, repeated titles, safe rendering and external-action boundaries.

`run_acceptance.py` creates a disposable copy and exercises the ten-step workflow from the Development Brief. It does not place test content in the public `workspace/`.

