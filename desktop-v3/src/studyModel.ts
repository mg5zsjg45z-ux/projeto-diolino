import type { StudyRecord } from './data';

export type StudyFields = Omit<StudyRecord,'id'>;

export function upsertStudy(studies:StudyRecord[],existingId:number|null,fields:StudyFields):StudyRecord[] {
  const id=existingId??Math.max(0,...studies.map(record=>record.id))+1;
  const record:StudyRecord={...fields,id};
  return [...studies.filter(item=>item.id!==id),record]
    .sort((a,b)=>b.date.localeCompare(a.date)||(b.time??'').localeCompare(a.time??''));
}
