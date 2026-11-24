import {test} from 'node:test';
import assert from 'node:assert/strict';
import {plannerPeriod,shiftPlannerDate} from '../public/mobile/planner-model.mjs';
test('planner periods use Monday weeks and correct leap months',()=>{
 assert.deepEqual(plannerPeriod('2026-11-04','day'),['2026-11-04']);
 assert.deepEqual(plannerPeriod('2026-11-04','week'),['2026-11-02','2026-11-03','2026-11-04','2026-11-05','2026-11-06','2026-11-07','2026-11-08']);
 assert.equal(plannerPeriod('2028-02-15','month').length,29);assert.equal(plannerPeriod('2026-02-15','month').length,28);
 assert.throws(()=>plannerPeriod('2026-02-30','month'));
});
test('planner month navigation avoids skipping months from the 31st',()=>{
 assert.equal(shiftPlannerDate('2026-01-31','month',1),'2026-02-28');
 assert.equal(shiftPlannerDate('2026-12-31','week',1),'2027-01-07');
 assert.equal(shiftPlannerDate('2026-11-01','day',-1),'2026-10-31');
});

import {plannerHour,visiblePlannerHours} from '../public/mobile/planner-model.mjs';
test('hour lanes preserve midnight, late tasks and separate unplanned times',()=>{assert.equal(plannerHour('00:15'),0);assert.equal(plannerHour('23:59'),23);for(const value of ['',null,'24:00','12:60','x'])assert.equal(plannerHour(value),null);assert.deepEqual(visiblePlannerHours([{time:'00:15'},{time:'23:00'}]),[0,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]);assert.equal(visiblePlannerHours([],true).length,24);});
