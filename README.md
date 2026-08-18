# Working-

A minimal Express REST API that serves as the development baseline for this repository.

## Requirements

- Node.js >= 20 (the Cloud Agent environment ships Node 22)

## Setup

```bash
npm ci        # install dependencies from the lockfile
```

## Running

```bash
npm start     # start the server on http://localhost:3000
npm run dev   # start with auto-reload (node --watch)
```

The server exposes a small task API:

| Method | Path          | Description            |
| ------ | ------------- | ---------------------- |
| GET    | `/health`     | Health check           |
| GET    | `/tasks`      | List all tasks         |
| GET    | `/tasks/:id`  | Get a single task      |
| POST   | `/tasks`      | Create a task          |
| PATCH  | `/tasks/:id`  | Update a task          |
| DELETE | `/tasks/:id`  | Delete a task          |

Example:

```bash
curl -s http://localhost:3000/health
curl -s -X POST http://localhost:3000/tasks \
  -H 'content-type: application/json' \
  -d '{"title":"write docs"}'
curl -s http://localhost:3000/tasks
```

## Checks

```bash
npm test      # run the test suite (node:test + supertest)
npm run lint  # run eslint
```

## Cloud Agent environment

Environment setup lives in [`.cursor/environment.json`](.cursor/environment.json):

- `install`: `npm ci` restores dependencies from `package-lock.json`.
- `terminals`: a `dev-server` terminal runs `npm run dev` so the API is available while working.
