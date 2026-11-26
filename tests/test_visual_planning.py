import tempfile
import unittest
from datetime import date
from storage import Store
from planning import create_plan, list_plans, move_step
from week_planner_ui import week_dates

class VisualPlanningTests(unittest.TestCase):
    def test_week_boundary(self):
        days = week_dates(date(2027,1,1))
        self.assertEqual(days[0],date(2026,12,28))
        self.assertEqual(days[-1],date(2027,1,3))

    def test_move_keeps_fields(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            try:
                create_plan(store,dict(title='Estudo',area='Medicina',status='Ativo',priority='Normal'),
                            [dict(title='Revisar',priority='Alta',due_date='2026-11-25')])
                step = list_plans(store)[0]['steps'][0]
                move_step(store,step['id'],'Em andamento')
                moved = store.get('plan_steps',step['id'])
                self.assertEqual(moved['state'],'Em andamento')
                self.assertEqual(moved['due_date'],step['due_date'])
                self.assertEqual(moved['priority'],step['priority'])
                with self.assertRaises(ValueError):
                    move_step(store,step['id'],'inválido')
                self.assertEqual(store.get('plan_steps',step['id'])['state'],'Em andamento')
                move_step(store,step['id'],'Concluído')
                self.assertEqual(list_plans(store)[0]['done'],1)
            finally:
                store.close()
