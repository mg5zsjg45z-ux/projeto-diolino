"""Exercise the real form-to-database flow with isolated temporary data."""
import tempfile
import unittest
from unittest.mock import patch
from app import App, Editor
from storage import Store
from inputs import DateTimeInput


class FormTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(self.tmp.name)
        self.app = App(self.store)
        self.app.withdraw()
        self.app.day.set('2026-10-16')

    def tearDown(self):
        self.app.shutdown()
        self.tmp.cleanup()

    def test_week_calendar_selection_and_year_transition_preserve_records(self):
        self.app.day.set('2026-12-31')
        self.assertEqual(self.app.week_strip.buttons[6].cget('text'), 'DOM\n3')
        self.app.week_strip.buttons[6].invoke()
        self.assertEqual(self.app.day.get(), '2027-01-03')
        self.assertEqual(self.app.week_strip.buttons[6].cget('style'), 'WeekSelected.TButton')
        self.app.week_strip.move_week(1)
        self.assertEqual(self.app.day.get(), '2027-01-10')
        self.assertIn('Janeiro de 2027', self.app.week_strip.month_label.cget('text'))
        self.assertEqual(self.store.rows('daily'), [])
        self.app.navigate('food')
        self.assertEqual(self.app.week_strip.winfo_manager(), '')
        self.app.navigate('agenda')
        self.assertEqual(self.app.week_strip.winfo_manager(), '')

    def test_save_edit_and_persistence(self):
        self.app.navigate('study')
        editor = Editor(self.app, 'study')
        editor.withdraw()
        for key, value in {'topic': 'Cardiologia — revisão', 'duration_min': '60', 'format': 'Leitura'}.items():
            editor.vars[key].set(value)
        editor.save()
        records = self.store.rows('study')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['topic'], 'Cardiologia — revisão')
        editor = Editor(self.app, 'study', records[0])
        editor.withdraw()
        editor.vars['duration_min'].set('75')
        editor.save()
        self.assertEqual(self.store.summary('2026-10-16')['study_min'], 75)
        second = Store(self.tmp.name)
        try:
            self.assertEqual(second.rows('study')[0]['duration_min'], 75)
        finally:
            second.close()

    def test_invalid_form_remains_open_without_write(self):
        editor = Editor(self.app, 'study')
        editor.withdraw()
        with patch('app.messagebox.showerror') as error:
            editor.save()
            error.assert_called_once()
        self.assertEqual(self.store.rows('study'), [])
        self.assertTrue(editor.winfo_exists())
        editor.destroy()

    def test_series_duplicate_keeps_workout_increments_number(self):
        wid = self.store.save('workout', {'date': '2026-10-16', 'name': 'Teste', 'modality': 'Musculação', 'duration_min': 40})
        sid = self.store.save('sets', {'workout_id': wid, 'exercise': 'Supino', 'set_number': 1, 'reps': 10, 'load_kg': 20, 'load_basis': 'Total'})
        editor = Editor(self.app, 'sets', self.store.get('sets', sid), True)
        editor.withdraw()
        editor.save()
        records = self.store.rows('sets')
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]['set_number'], 2)
        self.assertEqual(records[0]['workout_id'], wid)

    def test_daily_checkbox_click_saves_and_unchecks(self):
        self.app.navigate('checklist')
        self.assertEqual(len(self.app.check_buttons), 7)
        self.app.check_buttons['brush_1'][0].invoke()
        self.assertEqual(self.store.checklist('2026-10-16')['counts']['Higiene bucal'], 1)
        self.app.check_buttons['med_2'][0].invoke()
        self.app.check_buttons['brush_1'][0].invoke()
        self.assertEqual(self.store.checklist('2026-10-16')['counts']['Higiene bucal'], 0)
        self.app.change_day(1)
        self.assertFalse(self.app.check_buttons['med_2'][1].get())
        self.app.change_day(-1)
        self.assertTrue(self.app.check_buttons['med_2'][1].get())

    def test_structured_dates_and_times_round_trip(self):
        for kind, value in [('date', '2026-10-16'), ('time', '08:05'), ('datetime', '2026-10-16 08:05')]:
            widget = DateTimeInput(self.app, kind, value)
            self.assertEqual(widget.get(), value)
            widget.set('')
            self.assertEqual(widget.get(), '')
            widget.set(value)
            self.assertEqual(widget.get(), value)
            widget.destroy()

    def test_agenda_form_and_calculator_saved_scenario(self):
        self.app.navigate('agenda')
        editor = Editor(self.app, 'agenda')
        editor.withdraw()
        editor.vars['title'].set('Consulta de teste')
        editor.vars['time'].set('09:30')
        editor.save()
        self.assertEqual(self.store.rows('agenda')[0]['time'], '09:30')
        self.app.navigate('calculator')
        for key, value in {'weight_kg':'80', 'height_cm':'180', 'age_years':'30', 'coefficient':'Masculino (+5)', 'activity_factor':'1,5', 'deficit_pct':'20'}.items():
            self.app.calc_vars[key].set(value)
        result = self.app.calculate_energy(True)
        self.assertEqual(result['intake_kcal'], 2136)
        self.assertEqual(len(self.store.rows('energy')), 1)
        self.app.calc_vars['deficit_pct'].set('0')
        self.app.load_energy()
        self.assertEqual(float(self.app.calc_vars['deficit_pct'].get()), 20)

    def test_chart_data_missing_days_and_partial_calories(self):
        from datetime import date
        self.store.save('food', {'date':'2026-10-16', 'meal':'Almoço', 'food_name':'Teste', 'quantity':1, 'unit':'porção', 'source':'Não informado'})
        self.assertEqual(self.app.metric_points('calories', date(2026,10,15), date(2026,10,17)), [])
        for day, weight, time in [('2026-10-15',80,'08:00'), ('2026-10-15',81,'09:00'), ('2026-10-17',82,'08:00')]:
            self.store.save('body', {'date':day, 'weight_kg':weight, 'time':time})
        self.assertEqual(self.store.body_series('weight_kg','2026-10-15','2026-10-17'), [('2026-10-15',81),('2026-10-17',82)])


if __name__ == '__main__':
    unittest.main()
