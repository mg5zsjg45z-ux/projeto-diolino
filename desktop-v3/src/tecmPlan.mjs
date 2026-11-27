// Modelo de preparação opcional; não representa calendário oficial da SBCM.
export const TECM_PLAN = 'TECM 2027 — Clínica Médica';
export const TECM_AREAS = [
  'Cardiologia', 'Pneumologia', 'Gastroenterologia e Hepatologia', 'Nefrologia',
  'Endocrinologia', 'Infectologia', 'Hematologia', 'Oncologia', 'Reumatologia',
  'Neurologia', 'Geriatria', 'Dermatologia', 'Psiquiatria', 'Emergência e Medicina Intensiva',
  'Clínica Geral e Medicina Preventiva', 'Ginecologia e Obstetrícia', 'Oftalmologia',
  'Otorrinolaringologia', 'Epidemiologia, SUS e Ética Médica',
];
const blocks = [
  ['Fundamentação teórica I', 90], ['Fundamentação teórica II', 90],
  ['Questões comentadas', 120], ['Casos clínicos', 60],
  ['Revisão espaçada', 60], ['Treinamento prático', 60],
];
const dayAt = offset => new Date(Date.UTC(2026, 11, 1 + offset)).toISOString().slice(0,10);
const phase = date => date < '2027-01-01' ? 'Diagnóstico e início'
  : date < '2027-05-01' ? 'Cobertura'
  : date < '2027-07-01' ? 'Consolidação'
  : date < '2027-08-01' ? 'Simulados' : 'Revisão intensiva';
export function buildTecmTasks(tasks, floor = 0, now = Date.now()) {
  // Também considera tarefas arquivadas; não restaura etapas excluídas ao reimportar.
  if (tasks.some(task => task.plan === TECM_PLAN)) return tasks;
  let id = tasks.reduce((max, task) => Math.max(max, task.id), floor) + 1;
  const created = [];
  for (let week = 0; week < 39; week++) {
    const area = week === 0 ? 'Avaliação diagnóstica global' : TECM_AREAS[(week - 1) % TECM_AREAS.length];
    for (let slot = 0; slot < blocks.length; slot++) {
      const [activity, minutes] = blocks[slot];
      const due = dayAt(week * 7 + slot);
      created.push({id:id++, title:`S${String(week+1).padStart(2,'0')} · ${area} · ${activity} (${phase(due)})`,
        plan:TECM_PLAN, state:'A fazer', priority:'Alta', due,
        estimated_minutes:minutes, created_at:now, updated_at:now, completed_at:null});
    }
  }
  return [...tasks, ...created];
}
