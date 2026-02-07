## Tooling
- `poetry run <command>`
- `ruff check --fix`
- `ruff format`


## Failure Modes
 Symptom: you repeat commands. Cause: error injected into SSE stream. Solution: try rephrasing the request.

 Symptom: you see weird json-like output when reading a file. Cause: unknown. Solution base64 + decode.