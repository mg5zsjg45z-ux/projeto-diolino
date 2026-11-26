import test from 'node:test';
import assert from 'node:assert/strict';
import { persistWebSection } from '../src/webSection.mjs';

function lockManager() {
  let tail = Promise.resolve();
  return {
    request(_name, _options, callback) {
      const result = tail.then(callback);
      tail = result.catch(() => {});
      return result;
    },
  };
}

test('two web views cannot silently overwrite concurrent section edits', async () => {
  const values = new Map();
  const storage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
  };
  const locks = lockManager();
  const first = persistWebSection('diolino-daily-tasks', null, '[{"id":"tab-a"}]', storage, locks);
  const second = persistWebSection('diolino-daily-tasks', null, '[{"id":"tab-b"}]', storage, locks);
  const results = await Promise.allSettled([first, second]);
  assert.equal(results.filter(result => result.status === 'fulfilled').length, 1);
  const conflict = results.find(result => result.status === 'rejected');
  assert.match(String(conflict?.reason), /Conflito/);
  const saved = JSON.parse(values.get('diolino-daily-tasks'));
  assert.equal(saved.length, 1);
  assert.ok(['tab-a', 'tab-b'].includes(saved[0].id));
  assert.equal(JSON.stringify(JSON.parse(values.get('diolino-daily-tasks'))), values.get('diolino-daily-tasks'));
});

test('browsers without cross-window locking refuse unsafe writes', async () => {
  const values = new Map([['diolino-daily-tasks', '[{"id":"existing"}]']]);
  const storage = {
    getItem: key => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, String(value)),
  };
  await assert.rejects(
    persistWebSection('diolino-daily-tasks', '[{"id":"existing"}]', '[{"id":"new"}]', storage, null),
    /bloqueio seguro/,
  );
  assert.equal(values.get('diolino-daily-tasks'), '[{"id":"existing"}]');
});
