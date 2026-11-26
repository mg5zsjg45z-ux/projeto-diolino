export function shiftCalendarDate(value, amount, view) {
  const [year, month, day] = value.split('-').map(Number);
  if (view === 'Dia' || view === 'Semana') {
    const date = new Date(value + 'T12:00:00');
    date.setDate(date.getDate() + amount * (view === 'Semana' ? 7 : 1));
    return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
  }
  const targetMonth = month - 1 + amount;
  const targetYear = year + Math.floor(targetMonth / 12);
  const normalizedMonth = ((targetMonth % 12) + 12) % 12;
  const lastDay = new Date(targetYear, normalizedMonth + 1, 0, 12).getDate();
  const date = new Date(targetYear, normalizedMonth, Math.min(day, lastDay), 12);
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'), String(date.getDate()).padStart(2, '0')].join('-');
}
