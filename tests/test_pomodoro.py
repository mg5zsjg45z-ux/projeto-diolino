import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from pomodoro import Pomodoro
from storage import Store


class PomodoroTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir='test-output')
        self.store = Store(self.directory.name)
        self.now = 0
        self.timer = Pomodoro(self.store, lambda: self.now)
        self.timer.configure(1, 1, 2)

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def advance(self, seconds):
        for _ in range(seconds):
            self.now += 1
            self.timer.tick()

    def test_pause_resume_and_explicit_save(self):
        self.timer.start(topic='Cardiologia', now=datetime(2026, 11, 4, 23, 59), study_format='Vídeo')
        self.advance(20)
        self.timer.pause()
        self.advance(80)
        self.timer.start()
        self.advance(40)
        self.assertTrue(self.timer.state['pending'])
        self.assertEqual(self.store.rows('study'), [])
        rid = self.timer.resolve(True)
        record = self.store.get('study', rid)
        self.assertEqual((record['duration_min'], record['date'], record['format']), (1, '2026-11-04', 'Vídeo'))
        self.assertEqual(self.timer.state['phase'], 'short')
        self.assertIsNone(self.timer.resolve(True))
        self.timer.start()
        self.advance(60)
        self.assertEqual(self.timer.state['phase'], 'focus')
        self.assertFalse(self.timer.state['running'])
        self.assertEqual(len(self.store.rows('study')), 1)

    def test_restore_paused_and_ignore_sleep(self):
        self.timer.start(topic='Revisão')
        self.advance(12)
        self.timer.persist()
        self.now += 3600
        self.assertEqual(self.timer.tick(), 'interrupted')
        self.assertEqual(self.timer.state['elapsed'], 12)
        restored = Pomodoro(self.store, lambda: self.now)
        self.assertFalse(restored.state['running'])
        self.assertEqual(restored.state['elapsed'], 12)
        self.assertEqual(restored.state['session']['topic'], 'Revisão')

    def test_four_cycles_long_break_and_discard(self):
        for cycle in range(4):
            self.timer.start(topic='Tema')
            self.advance(60)
            self.timer.resolve(False)
            self.assertEqual(self.timer.state['phase'], 'long' if cycle == 3 else 'short')
            self.timer.skip_break()
        self.assertEqual(self.store.rows('study'), [])

    def test_partial_bible_and_save_failure_keeps_pending(self):
        self.timer.start('bible', 'João 1')
        self.advance(17)
        self.timer.finish_early()
        with patch.object(self.store, 'save', side_effect=OSError('Disco indisponível')):
            with self.assertRaises(OSError):
                self.timer.resolve(True)
        self.assertTrue(self.timer.state['pending'])
        rid = self.timer.resolve(True)
        self.assertEqual(self.store.get('bible', rid)['passage'], 'João 1')
        self.assertIn('0.2 min', self.store.get('bible', rid)['reflection'])
        self.assertEqual(self.timer.state['cycles'], 0)
        self.assertEqual(self.store.rows('study'), [])

    def test_crash_after_record_commit_does_not_duplicate(self):
        self.timer.start(topic='Tema')
        self.advance(60)
        with patch.object(self.timer, 'persist', side_effect=OSError('Disco indisponível')):
            with self.assertRaises(OSError):
                self.timer.resolve(True)
        restored = Pomodoro(self.store, lambda: self.now)
        self.assertTrue(restored.state['pending'])
        restored.resolve(True)
        self.assertEqual(len(self.store.rows('study')), 1)

    def test_invalid_settings_and_missing_topic(self):
        for value in ('0', '181', 'abc'):
            with self.assertRaises(ValueError):
                self.timer.configure(value, 5, 15)
        with self.assertRaises(ValueError):
            self.timer.start(topic='  ')
        self.timer.start(topic='Tema')
        with self.assertRaises(ValueError):
            self.timer.configure(30, 5, 15)

    def test_ui_navigation_keeps_timer_and_save_refreshes_study(self):
        from app import App
        app = App(self.store)
        app.withdraw()
        try:
            app.show_pomodoro()
            app.pomo_topic.set('Tema de teste')
            app.pomo_action('start')
            self.assertTrue(app.pomodoro.state['running'])
            app.navigate('studies')
            app.update_idletasks()
            self.assertTrue(app.pomodoro.state['running'])
            app.pomodoro_window.withdraw()
            app.pomodoro.state['elapsed'] = 61
            app.pomo_action('finish')
            app.pomo_action('save')
            self.assertEqual(len(self.store.rows('study')), 1)
            app.show_pomodoro()
            app.update_idletasks()
            self.assertEqual(app.pomo_topic.get(), 'Tema de teste')
        finally:
            app.stop_pomodoro()
            app.destroy()




    def test_flowtime_passes_focus_duration_until_finished(self):
        self.timer.configure(1, 1, 2, flowtime=True)
        self.timer.start(topic='Anatomia')
        self.advance(75)
        self.timer.pause()
        self.advance(20)
        self.timer.start()
        self.advance(15)
        self.timer.finish_early()
        record = self.store.get('study', self.timer.resolve(True))
        self.assertEqual((record['duration_min'], record['source']), (1.5, 'Flowtime'))
        self.assertEqual(self.timer.state['phase'], 'focus')


if __name__ == '__main__':
    unittest.main()
