import express from "express";
import { TaskStore } from "./store.js";

// Builds the Express application. A fresh store can be injected for tests.
export function createApp(store = new TaskStore()) {
  const app = express();
  app.use(express.json());

  app.get("/health", (_req, res) => {
    res.json({ status: "ok", uptime: process.uptime() });
  });

  app.get("/tasks", (_req, res) => {
    res.json(store.list());
  });

  app.get("/tasks/:id", (req, res) => {
    const task = store.get(req.params.id);
    if (!task) return res.status(404).json({ error: "task not found" });
    res.json(task);
  });

  app.post("/tasks", (req, res) => {
    const { title, done } = req.body ?? {};
    if (typeof title !== "string" || title.trim() === "") {
      return res.status(400).json({ error: "title is required" });
    }
    const task = store.create({ title: title.trim(), done });
    res.status(201).json(task);
  });

  app.patch("/tasks/:id", (req, res) => {
    const task = store.update(req.params.id, req.body ?? {});
    if (!task) return res.status(404).json({ error: "task not found" });
    res.json(task);
  });

  app.delete("/tasks/:id", (req, res) => {
    const removed = store.remove(req.params.id);
    if (!removed) return res.status(404).json({ error: "task not found" });
    res.status(204).end();
  });

  return app;
}
