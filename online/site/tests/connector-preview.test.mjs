import test from "node:test";
import assert from "node:assert/strict";
import { driverMessageSchema, invocationSchema } from "../scripts/connector-preview/protocol.mjs";

test("connector preview protocol accepts nonempty string-keyed argument and result records", () => {
  assert.deepEqual(
    invocationSchema.parse({ connectorId: "records", actionName: "get", arguments: { id: 42, include: ["notes"] } }),
    { connectorId: "records", actionName: "get", arguments: { id: 42, include: ["notes"] } },
  );
  assert.deepEqual(
    driverMessageSchema.parse({ jsonrpc: "2.0", id: "00000000-0000-4000-8000-000000000001", result: { content: [{ type: "text", text: "ok" }] } }).result,
    { content: [{ type: "text", text: "ok" }] },
  );
});
