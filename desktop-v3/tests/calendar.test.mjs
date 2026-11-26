import test from 'node:test';
import assert from 'node:assert/strict';
import { shiftCalendarDate } from '../src/calendar.mjs';

test('month navigation clamps January 31 to February end in common and leap years', () => {
  assert.equal(shiftCalendarDate('2026-01-31', 1, 'Mês'), '2026-02-28');
  assert.equal(shiftCalendarDate('2024-01-31', 1, 'Mês'), '2024-02-29');
});

test('month navigation works backwards and across year boundaries', () => {
  assert.equal(shiftCalendarDate('2024-03-31', -1, 'Mês'), '2024-02-29');
  assert.equal(shiftCalendarDate('2026-01-31', -1, 'Mês'), '2025-12-31');
  assert.equal(shiftCalendarDate('2026-12-31', 1, 'Mês'), '2027-01-31');
});

test('day and week navigation retain their own calendar arithmetic', () => {
  assert.equal(shiftCalendarDate('2026-02-28', 1, 'Dia'), '2026-03-01');
  assert.equal(shiftCalendarDate('2024-02-28', 1, 'Dia'), '2024-02-29');
  assert.equal(shiftCalendarDate('2026-11-26', -1, 'Semana'), '2026-11-19');
});

test('annual navigation changes year and clamps leap day when needed', () => {
  assert.equal(shiftCalendarDate('2026-06-15', 1, 'Ano'), '2027-06-15');
  assert.equal(shiftCalendarDate('2026-06-15', -1, 'Ano'), '2025-06-15');
  assert.equal(shiftCalendarDate('2024-02-29', 1, 'Ano'), '2025-02-28');
  assert.equal(shiftCalendarDate('2025-02-28', -1, 'Ano'), '2024-02-28');
});
