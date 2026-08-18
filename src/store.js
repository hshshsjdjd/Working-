// Simple in-memory task store. Not persistent; intended as a development baseline.
export class TaskStore {
  constructor() {
    this.tasks = new Map();
    this.nextId = 1;
  }

  list() {
    return [...this.tasks.values()];
  }

  get(id) {
    return this.tasks.get(Number(id));
  }

  create({ title, done = false }) {
    const id = this.nextId++;
    const task = { id, title, done: Boolean(done) };
    this.tasks.set(id, task);
    return task;
  }

  update(id, changes) {
    const task = this.tasks.get(Number(id));
    if (!task) return undefined;
    if (typeof changes.title === "string") task.title = changes.title;
    if (typeof changes.done === "boolean") task.done = changes.done;
    return task;
  }

  remove(id) {
    return this.tasks.delete(Number(id));
  }
}
