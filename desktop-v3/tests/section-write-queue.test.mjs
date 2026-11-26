import test from 'node:test';
import assert from 'node:assert/strict';
import { queueSectionWrite, sectionWrites } from '../src/sectionWriteQueue.mjs';

const tick = () => new Promise(resolve => setImmediate(resolve));

test('a reversion made during an outstanding write is committed after it', async () => {
  const key = `queue-revert-${Math.random()}`;
  let confirmed = ['base'];
  let releaseFirst;
  const firstGate = new Promise(resolve => { releaseFirst = resolve; });
  const written = [];
  let calls = 0;
  const handlers = {
    getConfirmed: () => confirmed,
    getRevision: () => 1,
    write: async (_key, _revision, value) => {
      calls += 1;
      written.push(value);
      if (calls === 1) await firstGate;
    },
    readLatest: async () => confirmed,
    isConflict: () => false,
    onCommit: (_serialized, value) => { confirmed = value; },
    onNoop() {}, onConflict() {}, onError() {},
  };

  const pending = queueSectionWrite(key, JSON.stringify(['middle']), handlers);
  await tick();
  queueSectionWrite(key, JSON.stringify(['base']), handlers);
  releaseFirst();
  await pending;

  assert.deepEqual(written, [['middle'], ['base']]);
  assert.deepEqual(confirmed, ['base']);
  assert.equal(sectionWrites.has(key), false);
});

test('conflicts are reported to the caller after refreshing the revision baseline', async () => {
  const key = `queue-conflict-${Math.random()}`;
  let revision = 2;
  let confirmed = ['old'];
  let conflictFound = false;
  const handlers = {
    getConfirmed: () => confirmed,
    getRevision: () => revision,
    write: async (_key, expected) => {
      assert.equal(expected, 2);
      throw new Error('outra janela alterou estes dados');
    },
    readLatest: async () => ({ value: ['latest'], revision: 3 }),
    isConflict: error => String(error).includes('outra janela'),
    onCommit() {},
    onNoop() {},
    onConflict: latest => { revision = latest.revision; confirmed = latest.value; conflictFound = true; },
    onError() {},
  };

  await assert.rejects(queueSectionWrite(key, JSON.stringify(['mine']), handlers), /outra janela/);
  assert.equal(conflictFound, true);
  assert.equal(revision, 3);
  assert.deepEqual(confirmed, ['latest']);
});
