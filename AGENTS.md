## Tooling
- `poetry run <command>`
- `poetry show <package>`
- `poetry run ruff check --fix`
- `poetry run ruff format`


## Failure Modes
 Symptom: you repeat commands. Cause: error injected into SSE stream. Solution: try rephrasing the request.

 Symptom: you see weird json-like output when reading a file. Cause: unknown. Solution bash`base64 <filename>` then decode. not: `cat <file> | base64`

 ## Architecture
 Current architecture is described at `docs/architecture/current_architecture.md`