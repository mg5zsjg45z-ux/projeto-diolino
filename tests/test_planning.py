import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from storage import Store, SCHEMA_VERSION
from planning import create_plan, list_plans, check_step, duplicate_plan, upcoming_steps, TEMPLATES


def plan(**values):
    return dict(title='Plano de estudo', area='Medicina', status='Ativo', priority='Normal', **values)


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='test-output')
        self.store = Store(self.temp.name)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_check_progress_reopen_and_pillars_remain_independent(self):
        rid = create_plan(self.store, plan(), ['Ler capítulo', 'Fazer revisão'])
        row = list_plans(self.store, '2026-10-16')[0]
        self.assertEqual(row['progress'], 0)
        check_step(self.store, row['steps'][0]['id'], True)
        self.assertEqual(list_plans(self.store)[0]['progress'], 50)
        self.assertEqual(self.store.rows('study'), [])
        self.assertFalse(self.store.pillar_states('2026-10-16')['medicine_status']['done'])
        check_step(self.store, row['steps'][0]['id'], False)
        self.assertEqual(list_plans(self.store)[0]['progress'], 0)
        self.assertEqual(self.store.get('plans', rid)['status'], 'Ativo')

    def test_invalid_child_never_creates_half_plan(self):
        with self.assertRaises(ValueError):
            create_plan(self.store, plan(), ['Válida', {'title': ''}])
        self.assertEqual(self.store.rows('plans'), [])
        original = self.store.audit
        def fail(kind, *args):
            if kind == 'plan_steps':
                raise RuntimeError('Simulated write failure')
            return original(kind, *args)
        with patch.object(self.store, 'audit', side_effect=fail):
            with self.assertRaises(RuntimeError):
                create_plan(self.store, plan(), ['Etapa'])
        self.assertEqual(self.store.rows('plans'), [])
        self.assertEqual(self.store.conn.execute('SELECT COUNT(*) FROM audit').fetchone()[0], 0)

    def test_duplicate_resets_checks_deadlines_archive_and_audit_preserved(self):
        rid = create_plan(self.store, plan(end_date='2026-10-30'), [{'title': 'Rever', 'due_date': '2026-10-15'}])
        step = list_plans(self.store)[0]['steps'][0]
        check_step(self.store, step['id'], True)
        copied = duplicate_plan(self.store, rid)
        row = next(p for p in list_plans(self.store) if p['id'] == copied)
        self.assertEqual(row['done'], 0)
        self.assertIsNone(row['end_date'])
        self.assertIsNone(row['steps'][0]['due_date'])
        with self.assertRaises(ValueError):
            self.store.delete('plans', rid)
        self.assertEqual(len(self.store.history('plan_steps', step['id'])), 2)

    def test_due_steps_exclude_paused_archived_completed_and_missing_dates(self):
        rid = create_plan(self.store, plan(), [{'title': 'Ontem', 'due_date': '2026-10-15'}, {'title': 'Sem prazo'}, {'title': 'Depois', 'due_date': '2026-11-01'}])
        self.assertEqual([s['title'] for s in upcoming_steps(self.store, '2026-10-16')], ['Ontem'])
        row = self.store.get('plans', rid)
        self.store.save('plans', dict(row, status='Pausado'), rid)
        self.assertEqual(upcoming_steps(self.store, '2026-10-16'), [])

    def test_v6_migration_backup_and_restore_preserve_existing_records(self):
        self.store.save('body', {'date': '2026-10-16', 'weight_kg': 82})
        with self.store.conn:
            self.store.conn.execute('DROP TABLE plan_steps')
            self.store.conn.execute('DROP TABLE plans')
            self.store.conn.execute('PRAGMA user_version=6')
        legacy = self.store.backup()
        self.store.close()
        self.store = Store(self.temp.name)
        self.assertEqual(self.store.conn.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
        self.assertEqual(self.store.rows('body')[0]['weight_kg'], 82)
        create_plan(self.store, plan(), ['Primeiro'])
        self.store.restore(legacy)
        self.assertEqual(self.store.rows('body')[0]['weight_kg'], 82)
        self.assertEqual(self.store.rows('plans'), [])
        self.assertGreaterEqual(len(list((Path(self.temp.name)/'backups').glob('*.sqlite3'))), 3)

    def test_native_view_and_parent_selection(self):
        from app import App, Editor
        create_plan(self.store, plan(), ['Revisar'])
        app = App(self.store)
        app.withdraw()
        try:
            app.navigate('planning')
            app.update_idletasks()
            editor = Editor(app, 'plan_steps')
            self.assertTrue(editor.links['plan_id'])
            editor.destroy()
        finally:
            app.shutdown()
        self.store = Store(self.temp.name)

    def test_backup_export_and_restore_include_checked_plan_steps(self):
        import zipfile
        rid = create_plan(self.store, plan(), ['Etapa preservada'])
        step = list_plans(self.store)[0]['steps'][0]
        check_step(self.store, step['id'], True)
        backup = self.store.backup()
        bundle = Path(self.temp.name) / 'export.zip'
        self.store.export(bundle)
        with zipfile.ZipFile(bundle) as export:
            self.assertIn('Etapa preservada', export.read('plan_steps.csv').decode('utf-8-sig'))
            self.assertIn('plans.csv', export.namelist())
        check_step(self.store, step['id'], False)
        self.store.restore(backup)
        self.assertEqual(list_plans(self.store)[0]['progress'], 100)

    def test_native_overview_uses_symbols_and_dash_instead_of_empty_record_text(self):
        import tkinter as tk
        from app import App
        self.store.set_pillar('2026-10-16', 'medicine_status', True)
        self.store.set_pillar('2026-10-16', 'exercise_status', False)
        app = App(self.store)
        app.withdraw()
        app.day.set('2026-10-16')
        try:
            app.navigate('home')
            def descendants(widget):
                yield widget
                for child in widget.winfo_children():
                    yield from descendants(child)
            widgets = list(descendants(app.content))
            texts=[]
            symbols=[]
            for widget in widgets:
                try:
                    texts.append(str(widget.cget('text')))
                except tk.TclError:
                    pass
                if isinstance(widget, tk.Canvas):
                    symbols += [widget.itemcget(item, 'text') for item in widget.find_all() if widget.type(item)=='text']
            self.assertIn('✓', symbols)
            self.assertIn('×', symbols)
            self.assertIn('–', symbols)
            self.assertNotIn('Sem registro', texts)
            self.assertFalse(any('/ 3' in text for text in texts))
        finally:
            app.shutdown()
        self.store = Store(self.temp.name)
