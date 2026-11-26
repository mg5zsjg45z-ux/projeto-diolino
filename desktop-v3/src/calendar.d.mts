export type CalendarView = 'Mês' | 'Semana' | 'Dia' | 'Ano';
export function shiftCalendarDate(value: string, amount: number, view: CalendarView): string;
