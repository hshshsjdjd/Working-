# Cloud List

A serverless to-do app built with [Puter.js](https://developer.puter.com). Tasks are stored in the signed-in user's Puter key-value store (`puter.kv.get` / `puter.kv.set`). There is no backend and no API key.

## Features

- Sign in / sign out with a Puter account (popup must be opened from a click)
- Local drafts in this browser until you sign in; then tasks sync to Puter KV
- Add, complete, edit, and delete tasks
- Optional due dates, with overdue highlighting
- All / Active / Done filters
- Clear completed tasks
- Data isolated per user and per app in Puter KV

## Run locally

Puter.js must be served over HTTP, not a `file://` URL.

```bash
python3 -m http.server 4173
```

Then open `http://localhost:4173`.

## How storage works

1. The app checks `puter.auth.isSignedIn()`.
2. After you click **Sign in with Puter**, `puter.auth.signIn()` completes and `puter.auth.getUser()` loads the username.
3. The list is read from `puter.kv.get('cloud-list:todos')`.
4. Every change is written with `puter.kv.set('cloud-list:todos', todos)`.

## Tests

```bash
node --test js/todos.test.js
```
