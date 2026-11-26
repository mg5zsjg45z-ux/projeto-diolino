import test from 'node:test';
import assert from 'node:assert/strict';
import { isBackupDate, isBackupTime } from '../src/backupValidation.mjs';

test('backup validates ordinary dates and rejects malformed calendar dates', () => {
  assert.equal(isBackupDate('2026-11-26'), true);
  assert.equal(isBackupDate('2024-02-29'), true);
  assert.equal(isBackupDate('2026-02-29'), false);
  assert.equal(isBackupDate('2026-1-02'), false);
});

test('backup validates ordinary times and optional null values', () => {
  assert.equal(isBackupTime('08:30'), true);
  assert.equal(isBackupTime('23:59'), true);
  assert.equal(isBackupTime(null), true);
  assert.equal(isBackupTime('24:00'), false);
  assert.equal(isBackupTime('8:30'), false);
});
