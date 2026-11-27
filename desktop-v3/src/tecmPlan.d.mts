import type { Task } from './data';
export const TECM_PLAN: string;
export const TECM_AREAS: readonly string[];
export function buildTecmTasks(tasks: Task[], floor?: number, now?: number): Task[];
