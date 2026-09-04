const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "todos.js"), "utf8");
const sandbox = { window: {} };
vm.runInNewContext(source, sandbox);
const store = sandbox.window.TodoStore;

test("normalizeTodos drops empty and wraps objects", () => {
  const todos = store.normalizeTodos([
    { id: "1", text: " Buy milk ", completed: true, due: "2026-09-04" },
    { text: "" },
    null,
  ]);
  assert.equal(todos.length, 1);
  assert.equal(todos[0].text, "Buy milk");
  assert.equal(todos[0].completed, true);
  assert.equal(todos[0].due, "2026-09-04");
});

test("add, toggle, update, remove, and clear completed", () => {
  let todos = store.addTodo([], { text: "Write docs", due: "2026-09-10" });
  assert.equal(todos.length, 1);
  const id = todos[0].id;
  todos = store.toggleTodo(todos, id);
  assert.equal(todos[0].completed, true);
  todos = store.updateTodo(todos, id, { text: " Write README " });
  assert.equal(todos[0].text, "Write README");
  todos = store.addTodo(todos, { text: "Ship it" });
  assert.equal(store.remainingCount(todos), 1);
  todos = store.clearCompleted(todos);
  assert.equal(todos.length, 1);
  todos = store.removeTodo(todos, todos[0].id);
  assert.equal(todos.length, 0);
});

test("filters split active and completed", () => {
  const todos = [
    { id: "a", text: "A", completed: false },
    { id: "b", text: "B", completed: true },
  ];
  assert.equal(store.filterTodos(todos, "all").length, 2);
  assert.equal(store.filterTodos(todos, "active")[0].id, "a");
  assert.equal(store.filterTodos(todos, "completed")[0].id, "b");
});
