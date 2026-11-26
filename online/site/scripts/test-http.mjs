import { spawn, spawnSync } from "node:child_process";
import { createServer } from "node:net";
import { mkdtemp, rm } from "node:fs/promises";
import { setTimeout as delay } from "node:timers/promises";
import os from "node:os";
import path from "node:path";

const runtime = await mkdtemp(path.join(os.tmpdir(), "diolino-site-http-"));
const state = path.join(runtime, "d1-r2");
const config = "dist/server/wrangler.json";
let server;

function run(args, extraEnv = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, args, {
      cwd: process.cwd(),
      stdio: "inherit",
      env: { ...process.env, ...extraEnv },
    });
    child.once("error", reject);
    child.once("exit", code => code === 0 ? resolve() : reject(new Error(`${args.join(" ")} exited ${code}`)));
  });
}

async function freePort() {
  const socket = createServer();
  await new Promise((resolve, reject) => {
    socket.once("error", reject);
    socket.listen(0, "127.0.0.1", resolve);
  });
  const { port } = socket.address();
  await new Promise(resolve => socket.close(resolve));
  return port;
}

function stop(child) {
  if (!child?.pid || child.exitCode !== null) return Promise.resolve();
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/pid", String(child.pid), "/t", "/f"], { stdio: "ignore" });
  } else {
    child.kill("SIGTERM");
  }
  return new Promise(resolve => {
    if (child.exitCode !== null) resolve();
    else child.once("exit", resolve);
  });
}

try {
  await run(["scripts/run-framework.mjs", "build"]);
  const port = await freePort();
  const origin = `http://127.0.0.1:${port}`;
  const testEnv = {
    DIOLINO_TEST_STATE: state,
    DIOLINO_HTTP_TEST_ORIGIN: origin,
    DIOLINO_HTTP_TEST_PORT: String(port),
    VINEXT_NO_DEV_LOCK: "1",
  };

  for (const migration of ["0000_brief_zodiak.sql", "0001_typical_junta.sql"]) {
    await run([
      "node_modules/wrangler/bin/wrangler.js", "d1", "execute", "diolino-site-preview",
      "--local", "--persist-to", state, "--config", config, "--file", `drizzle/${migration}`,
    ], testEnv);
  }

  server = spawn(process.execPath, [
    "node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", String(port), "--strictPort",
  ], {
    cwd: process.cwd(),
    stdio: "inherit",
    env: { ...process.env, ...testEnv },
  });
  let ready = false;
  for (let attempt = 0; attempt < 90; attempt++) {
    try {
      const response = await fetch(origin);
      if (response.status < 500) { ready = true; break; }
    } catch { /* Wait for the local preview to bind. */ }
    if (server.exitCode !== null) throw new Error(`The test preview exited with ${server.exitCode}.`);
    await delay(500);
  }
  if (!ready) throw new Error(`The isolated test preview did not start at ${origin}.`);

  await run(["--test", "tests/http.test.mjs"], testEnv);
  await run(["--test", "tests/media-http.test.mjs"], testEnv);
} finally {
  await stop(server);
  await rm(runtime, { recursive: true, force: true, maxRetries: 20, retryDelay: 500 });
}
