import test from "node:test";
import assert from "node:assert/strict";
import request from "supertest";
import { createApp } from "../src/app.js";

test("health endpoint reports ok", async () => {
  const res = await request(createApp()).get("/health");
  assert.equal(res.status, 200);
  assert.equal(res.body.status, "ok");
});

test("creates and retrieves a task", async () => {
  const app = createApp();
  const created = await request(app).post("/tasks").send({ title: "write docs" });
  assert.equal(created.status, 201);
  assert.equal(created.body.title, "write docs");
  assert.equal(created.body.done, false);

  const fetched = await request(app).get(`/tasks/${created.body.id}`);
  assert.equal(fetched.status, 200);
  assert.equal(fetched.body.id, created.body.id);
});

test("rejects a task without a title", async () => {
  const res = await request(createApp()).post("/tasks").send({});
  assert.equal(res.status, 400);
  assert.equal(res.body.error, "title is required");
});

test("updates and deletes a task", async () => {
  const app = createApp();
  const created = await request(app).post("/tasks").send({ title: "temp" });
  const id = created.body.id;

  const updated = await request(app).patch(`/tasks/${id}`).send({ done: true });
  assert.equal(updated.status, 200);
  assert.equal(updated.body.done, true);

  const removed = await request(app).delete(`/tasks/${id}`);
  assert.equal(removed.status, 204);

  const missing = await request(app).get(`/tasks/${id}`);
  assert.equal(missing.status, 404);
});
