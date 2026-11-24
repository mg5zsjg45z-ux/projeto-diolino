import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from energy import energy_estimate
from storage import Store
from project_sync import write_snapshot


class EnergyTests(unittest.TestCase):
    def test_known_arithmetic_both_coefficients(self):
        result = energy_estimate(80, 180, 30, 'Masculino (+5)', 1.5, 20)
        self.assertEqual(result['resting_kcal'], 1780)
        self.assertEqual(result['total_kcal'], 2670)
        self.assertEqual(result['deficit_kcal'], 534)
        self.assertEqual(result['intake_kcal'], 2136)
        female = energy_estimate('80', '180', '30', 'Feminino (−161)', '1,5', 0)
        self.assertEqual(female['resting_kcal'], 1614)
        self.assertEqual(female['intake_kcal'], female['total_kcal'])

    def test_missing_invalid_and_extreme_inputs(self):
        args = [80, 180, 30, 'Masculino (+5)', 1.5, 20]
        for index, value in [(0, 'NaN'), (0, ''), (1, 1.8), (2, 17), (2, 30.5), (3, ''), (4, 0), (5, -10), (5, 90)]:
            invalid = args.copy()
            invalid[index] = value
            with self.assertRaises(ValueError):
                energy_estimate(*invalid)
        with self.assertRaises(ValueError):
            energy_estimate(50, 155, 65, 'Feminino (−161)', 1.2, 50)


class AgendaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def agenda(self, **kwargs):
        return {'date': '2026-10-16', 'time': '21:00', 'title': 'Estudar', 'category': 'Tarefa', 'state': 'Pendente', 'reminder': 'Sim'} | kwargs

    def test_due_once_reopen_reschedule_and_complete(self):
        rid = self.store.save('agenda', self.agenda())
        self.assertEqual(self.store.due_reminders(datetime(2026, 10, 16, 20, 59)), [])
        due = self.store.due_reminders(datetime(2026, 10, 16, 21, 0))
        self.assertEqual(len(due), 1)
        self.store.mark_notified(due[0], datetime(2026, 10, 16, 21, 0))
        self.store.close()
        self.store = Store(self.temp.name)
        self.assertEqual(self.store.due_reminders(datetime(2026, 10, 17)), [])
        self.store.save('agenda', self.agenda(time='22:00'), rid)
        self.assertEqual(len(self.store.due_reminders(datetime(2026, 10, 17))), 1)
        self.store.save('agenda', self.agenda(state='Concluído'), rid)
        self.assertEqual(self.store.due_reminders(datetime(2026, 10, 17)), [])

    def test_notes_no_time_and_cancelled_deleted_not_notified(self):
        with self.assertRaises(ValueError):
            self.store.save('agenda', self.agenda(time=''))
        self.store.save('agenda', self.agenda(time='', reminder='Não', category='Nota'))
        self.store.save('agenda', self.agenda(state='Cancelado'))
        rid = self.store.save('agenda', self.agenda())
        self.store.delete('agenda', rid)
        self.assertEqual(self.store.due_reminders(datetime(2026, 10, 17)), [])

    def test_pillars_manual_and_record_evidence(self):
        day = '2026-10-16'
        self.store.save('study', {'date': day, 'topic': 'Teste', 'duration_min': 60, 'format': 'Leitura'})
        self.assertTrue(self.store.pillar_states(day)['medicine_status']['done'])
        self.store.set_pillar(day, 'medicine_status', False)
        self.assertFalse(self.store.pillar_states(day)['medicine_status']['done'])
        self.store.set_pillar(day, 'bible_status', True)
        self.assertTrue(self.store.pillar_states(day)['bible_status']['done'])
        self.assertEqual(self.store.rows('study')[0]['duration_min'], 60)

    def test_snapshot_omits_private_details(self):
        self.store.save('profile', {'name': 'Teste', 'conditions': 'DIAGNOSTICO_PRIVADO'})
        self.store.save('agenda', self.agenda(description='NOTA_PRIVADA'))
        with tempfile.TemporaryDirectory() as folder:
            with patch('project_sync.default_directory', return_value=Path(self.temp.name)), patch('project_sync.project_directory', return_value=Path(folder)):
                path = write_snapshot(self.store)
                content = path.read_text(encoding='utf-8')
                self.assertNotIn('DIAGNOSTICO_PRIVADO', content)
                self.assertNotIn('NOTA_PRIVADA', content)
                self.assertIn('Snapshot de 7 dias', content)

    def test_v2_upgrade_preserves_checklist_and_legacy_restore(self):
        self.store.set_check('2026-10-16', 'med_1', True)
        with self.store.conn:
            for table in ('agenda', 'agenda_notices', 'energy'):
                self.store.conn.execute(f'DROP TABLE {table}')
            self.store.conn.execute('PRAGMA user_version=2')
        backup = self.store.backup()
        self.store.close()
        self.store = Store(self.temp.name)
        self.assertEqual(self.store.checklist('2026-10-16')['counts']['Checagem da medicação'], 1)
        self.store.save('agenda', self.agenda())
        self.store.restore(backup)
        self.assertEqual(self.store.rows('agenda'), [])
        self.assertEqual(self.store.checklist('2026-10-16')['counts']['Checagem da medicação'], 1)


if __name__ == '__main__':
    unittest.main()
