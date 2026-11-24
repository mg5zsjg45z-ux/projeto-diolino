import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import App
from storage import Store
from models import MODELS
from bible_library import passage, reading_plan, BOOKS, VERSIONS
from print_documents import build_report, build_template, TEMPLATES


class PrintLibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='test-output')
        self.store = Store(self.tmp.name)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_all_versions_passage_and_chapter_validation(self):
        self.assertEqual(len(BOOKS), 66)
        for version in VERSIONS:
            for name, _, count, _ in BOOKS:
                selected = passage(version, name, count)
                self.assertTrue(selected['url'].startswith('https://'))
                self.assertIn(version, selected['reference'])
        for args in [('NAA','João',22), ('unknown','João',1), ('NVI','invalid',1), ('ACF','Jó',0)]:
            with self.assertRaises(ValueError): passage(*args)
        self.assertEqual(passage('NVI','João',3)['url'], 'https://www.bible.com/pt/bible/129/JHN.3.NVI')

    def test_reading_plan_is_unchecked_and_does_not_confirm_bible(self):
        rid = reading_plan(self.store, 'João', 'NAA', '2026-12-20')
        steps = self.store.rows('plan_steps')
        self.assertEqual(len(steps), 21)
        self.assertTrue(all(r['state'] == 'A fazer' and r['plan_id'] == rid for r in steps))
        self.assertEqual(max(r['due_date'] for r in steps), '2027-01-09')
        self.assertFalse(self.store.pillar_states('2026-12-20')['bible_status']['done'])

    def test_all_areas_filter_escape_and_no_database_changes(self):
        self.store.save('study', {'date':'2026-10-16','topic':'<script>bad()</script>', 'duration_min':60,'format':'Leitura','notes':'PRIVATE-NOTE'})
        self.store.save('study', {'date':'2026-10-17','topic':'OUTSIDE', 'duration_min':10,'format':'Vídeo'})
        self.store.save('body', {'date':'2026-10-16','weight_kg':80})
        before = self.store.conn.total_changes
        html = build_report(self.store, '2026-10-16', '2026-10-16', list(MODELS), False, include_empty=True)
        self.assertIn('&lt;script&gt;bad()', html)
        self.assertNotIn('<script>bad()', html)
        self.assertNotIn('OUTSIDE', html)
        self.assertNotIn('PRIVATE-NOTE', html)
        for label, _ in MODELS.values(): self.assertIn(label, html)
        self.assertEqual(self.store.conn.total_changes, before)
        with self.assertRaises(ValueError): build_report(self.store,'2026-10-17','2026-10-16',[])

    def test_absent_days_are_not_reported_as_zero_or_failed(self):
        html = build_report(self.store, '2026-10-16','2026-10-16', [], include_summary=True)
        self.assertIn('<td>–</td>', html)
        self.assertNotIn('<td>0</td>', html)
        self.assertNotIn('<td>Não realizado</td>', html)

    def test_templates_month_edges_and_combined_booklet(self):
        before = self.store.conn.total_changes
        for kind in TEMPLATES:
            html = build_template(self.store, kind, '2026-08-31')
            self.assertIn('@page{size:A4', html)
            self.assertIn('window.print()', html)
        month = build_template(self.store,'monthly','2024-02-29')
        self.assertIn('<strong>29</strong>', month)
        self.assertNotIn('<strong>30</strong>', month)
        bundle = build_template(self.store,'bundle','2026-12-31')
        self.assertEqual(bundle.count('<section class="sheet">'), 12)
        self.assertIn('03/01/2027', bundle)
        self.assertEqual(self.store.conn.total_changes, before)

    def test_native_library_and_print_actions_do_not_write_until_save(self):
        app = App(self.store)
        app.withdraw()
        try:
            app.navigate('bible_online')
            with patch('library_ui.webbrowser.open', return_value=True) as browser:
                app.open_bible()
                browser.assert_called_once()
            app.record_bible()
            self.assertEqual(self.store.rows('bible'), [])
            editor = next(w for w in app.winfo_children() if w.winfo_class() == 'Toplevel')
            self.assertIn('NAA', editor.vars['passage'].get())
            editor.destroy()
            app.navigate('printing')
            self.assertEqual(set(app.report_kinds), set(MODELS))
            with patch('library_ui.webbrowser.open', return_value=True):
                path = app.generate_template()
            self.assertTrue(path.is_file())
            self.assertEqual(self.store.rows('daily'), [])
            app.update_idletasks()
        finally:
            # The test owns Store; App.shutdown would close it twice.
            app.destroy()


if __name__ == '__main__': unittest.main()
