(function (global) {
  const KV_KEY = "cloud-list:todos";

  function createId() {
    if (global.crypto && typeof global.crypto.randomUUID === "function") {
      return global.crypto.randomUUID();
    }
    return "todo-" + Date.now() + "-" + Math.random().toString(16).slice(2);
  }

  function normalizeTodos(value) {
    if (!Array.isArray(value)) return [];
    return value
      .filter((item) => item && typeof item === "object")
      .map((item) => ({
        id: String(item.id || createId()),
        text: String(item.text || "").trim(),
        completed: Boolean(item.completed),
        due: item.due ? String(item.due) : "",
        createdAt: Number(item.createdAt) || Date.now(),
      }))
      .filter((item) => item.text.length > 0);
  }

  function addTodo(todos, { text, due }) {
    const trimmed = String(text || "").trim();
    if (!trimmed) return todos.slice();
    return [
      {
        id: createId(),
        text: trimmed,
        completed: false,
        due: due || "",
        createdAt: Date.now(),
      },
      ...todos,
    ];
  }

  function toggleTodo(todos, id) {
    return todos.map((todo) =>
      todo.id === id ? { ...todo, completed: !todo.completed } : todo
    );
  }

  function updateTodo(todos, id, patch) {
    return todos.map((todo) => {
      if (todo.id !== id) return todo;
      const next = { ...todo, ...patch };
      if ("text" in patch) next.text = String(patch.text || "").trim();
      return next;
    });
  }

  function removeTodo(todos, id) {
    return todos.filter((todo) => todo.id !== id);
  }

  function clearCompleted(todos) {
    return todos.filter((todo) => !todo.completed);
  }

  function filterTodos(todos, filter) {
    if (filter === "active") return todos.filter((todo) => !todo.completed);
    if (filter === "completed") return todos.filter((todo) => todo.completed);
    return todos;
  }

  function remainingCount(todos) {
    return todos.filter((todo) => !todo.completed).length;
  }

  global.TodoStore = {
    KV_KEY,
    normalizeTodos,
    addTodo,
    toggleTodo,
    updateTodo,
    removeTodo,
    clearCompleted,
    filterTodos,
    remainingCount,
  };
})(typeof window !== "undefined" ? window : globalThis);
