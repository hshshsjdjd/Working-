(() => {
  const {
    KV_KEY,
    normalizeTodos,
    addTodo,
    toggleTodo,
    updateTodo,
    removeTodo,
    clearCompleted,
    filterTodos,
    remainingCount,
  } = window.TodoStore;

  const els = {
    authStatus: document.getElementById("auth-status"),
    signIn: document.getElementById("sign-in-btn"),
    signOut: document.getElementById("sign-out-btn"),
    banner: document.getElementById("banner"),
    composer: document.getElementById("composer"),
    text: document.getElementById("todo-text"),
    due: document.getElementById("todo-due"),
    list: document.getElementById("todo-list"),
    empty: document.getElementById("empty-state"),
    counts: document.getElementById("counts"),
    clearCompleted: document.getElementById("clear-completed"),
  };

  const LOCAL_KEY = "cloud-list:local-todos";

  const state = {
    todos: [],
    filter: "all",
    signedIn: false,
    username: "",
    busy: false,
  };

  function readLocal() {
    try {
      return normalizeTodos(JSON.parse(localStorage.getItem(LOCAL_KEY) || "[]"));
    } catch {
      return [];
    }
  }

  function writeLocal(todos) {
    localStorage.setItem(LOCAL_KEY, JSON.stringify(todos));
  }

  function showBanner(message) {
    els.banner.hidden = !message;
    els.banner.textContent = message || "";
  }

  function setBusy(busy) {
    state.busy = busy;
    els.composer.querySelector("button[type=submit]").disabled = busy;
    els.signIn.disabled = busy;
    els.signOut.disabled = busy;
  }

  function hasPuter() {
    return typeof window.puter !== "undefined" && window.puter.auth && window.puter.kv;
  }

  async function persist() {
    writeLocal(state.todos);
    if (!hasPuter() || !state.signedIn) return;
    await puter.kv.set(KV_KEY, state.todos);
  }

  async function loadFromCloud() {
    const raw = await puter.kv.get(KV_KEY);
    state.todos = normalizeTodos(raw);
  }

  function renderAuth() {
    if (!hasPuter()) {
      els.authStatus.textContent = "Puter.js did not load.";
      els.signIn.hidden = true;
      els.signOut.hidden = true;
      showBanner("Cloud sync needs Puter.js over HTTP. Serve this folder, then refresh.");
      return;
    }

    if (state.signedIn) {
      els.authStatus.textContent = state.username
        ? "Signed in as " + state.username
        : "Signed in with Puter";
      els.signIn.hidden = true;
      els.signOut.hidden = false;
      showBanner("");
      return;
    }

    els.authStatus.textContent = "Not signed in";
    els.signIn.hidden = false;
    els.signOut.hidden = true;
    showBanner(
      "Working from this browser for now. Sign in to sync the list to your Puter cloud KV store."
    );
  }

  function renderList() {
    const visible = filterTodos(state.todos, state.filter);
    els.list.replaceChildren();

    visible.forEach((todo) => {
      const li = document.createElement("li");
      li.className = "todo-item" + (todo.completed ? " done" : "");
      li.dataset.id = todo.id;

      const check = document.createElement("input");
      check.type = "checkbox";
      check.className = "check";
      check.checked = todo.completed;
      check.setAttribute("aria-label", "Mark complete");

      const body = document.createElement("div");
      const title = document.createElement("p");
      title.className = "title";
      title.textContent = todo.text;
      body.appendChild(title);

      if (todo.due) {
        const due = document.createElement("p");
        due.className = "due";
        const today = new Date().toISOString().slice(0, 10);
        if (!todo.completed && todo.due < today) due.classList.add("is-overdue");
        due.textContent = "Due " + todo.due;
        body.appendChild(due);
      }

      const actions = document.createElement("div");
      actions.className = "item-actions";

      const editBtn = document.createElement("button");
      editBtn.type = "button";
      editBtn.className = "icon-btn";
      editBtn.dataset.action = "edit";
      editBtn.textContent = "Edit";

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "icon-btn";
      deleteBtn.dataset.action = "delete";
      deleteBtn.textContent = "Delete";

      actions.append(editBtn, deleteBtn);
      li.append(check, body, actions);
      els.list.appendChild(li);
    });

    els.empty.hidden = visible.length > 0;
    const remaining = remainingCount(state.todos);
    els.counts.textContent =
      remaining + (remaining === 1 ? " remaining" : " remaining");
    els.clearCompleted.hidden = !state.todos.some((todo) => todo.completed);
  }

  function render() {
    renderAuth();
    renderList();
  }

  async function refreshSession() {
    if (!hasPuter()) {
      state.todos = readLocal();
      render();
      return;
    }

    state.signedIn = Boolean(puter.auth.isSignedIn());
    if (state.signedIn) {
      try {
        const user = await puter.auth.getUser();
        state.username = user && user.username ? user.username : "";
        await loadFromCloud();
        if (state.todos.length === 0) {
          const local = readLocal();
          if (local.length > 0) {
            state.todos = local;
            await persist();
          }
        } else {
          writeLocal(state.todos);
        }
      } catch (error) {
        showBanner(error.message || "Could not load Puter user or todos.");
      }
    } else {
      state.username = "";
      state.todos = readLocal();
    }
    render();
  }

  async function mutate(mutator) {
    if (state.busy) return;
    setBusy(true);
    try {
      state.todos = mutator(state.todos);
      renderList();
      await persist();
    } catch (error) {
      showBanner(error.message || "Could not save to Puter KV.");
      await refreshSession();
    } finally {
      setBusy(false);
    }
  }

  els.signIn.addEventListener("click", async () => {
    if (!hasPuter()) return;
    setBusy(true);
    try {
      await puter.auth.signIn();
      await refreshSession();
    } catch (error) {
      const message =
        error && error.error === "popup_blocked"
          ? "Sign-in popup was blocked. Use the Sign in button (a user click is required)."
          : error.message || "Sign in failed.";
      showBanner(message);
    } finally {
      setBusy(false);
      renderAuth();
    }
  });

  els.signOut.addEventListener("click", async () => {
    if (!hasPuter()) return;
    await puter.auth.signOut();
    state.signedIn = false;
    state.username = "";
    state.todos = readLocal();
    render();
  });

  els.composer.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = els.text.value;
    const due = els.due.value;
    if (!text.trim()) return;
    await mutate((todos) => addTodo(todos, { text, due }));
    els.composer.reset();
    els.text.focus();
  });

  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      state.filter = button.dataset.filter;
      document.querySelectorAll("[data-filter]").forEach((el) => {
        el.classList.toggle("is-active", el === button);
      });
      renderList();
    });
  });

  els.clearCompleted.addEventListener("click", () => {
    mutate(clearCompleted);
  });

  els.list.addEventListener("change", (event) => {
    const item = event.target.closest(".todo-item");
    if (!item || event.target.type !== "checkbox") return;
    mutate((todos) => toggleTodo(todos, item.dataset.id));
  });

  els.list.addEventListener("click", async (event) => {
    const item = event.target.closest(".todo-item");
    if (!item) return;
    const id = item.dataset.id;
    const action = event.target.dataset.action;
    if (action === "delete") {
      await mutate((todos) => removeTodo(todos, id));
      return;
    }
    if (action !== "edit") return;

    const current = state.todos.find((todo) => todo.id === id);
    if (!current) return;
    const next = window.prompt("Edit task", current.text);
    if (next == null) return;
    await mutate((todos) => updateTodo(todos, id, { text: next }));
  });

  refreshSession();
})();
