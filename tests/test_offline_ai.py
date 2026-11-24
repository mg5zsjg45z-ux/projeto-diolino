import tempfile
import unittest
from unittest.mock import patch
from app import App
from assistant_ui import AssistantWindow
from storage import Store
from offline_ai import normalize_drafts, draft_error, Recorder, grounded_values, quick_drafts


class OfflineDraftTests(unittest.TestCase):
    def test_hallucinated_measurements_time_and_notes_are_removed(self):
        result = grounded_values('body', {'weight_kg': 82.4, 'waist_cm': 90, 'time': '00:00', 'notes': 'Normal'},
                                 {'weight_kg': 'pesei 82,4 kg', 'waist_cm': 'pesei 82,4 kg', 'time': 'hoje'},
                                 'Hoje pesei 82,4 kg.', '2026-10-16')
        self.assertEqual(result, {'weight_kg': 82.4, 'date': '2026-10-16'})

    def test_negation_and_date_evidence_preserved(self):
        result = grounded_values('medication', {'status': 'Tomado', 'taken_dose': 30},
                                 {'status': 'não tomei', 'taken_dose': 'não tomei'},
                                 'Hoje não tomei o medicamento.', '2026-10-16')
        self.assertNotIn('status', result)
        self.assertNotIn('taken_dose', result)
        self.assertIsNone(quick_drafts('Não bebi 500 ml de água', '2026-10-16'))
        self.assertIsNone(quick_drafts('Ontem pesei 82 kg e hoje bebi 500 ml de água', '2026-10-16'))

    def test_exact_measurements_convert_liters_without_extra_fields(self):
        drafts, _ = quick_drafts('Hoje pesei 82,4 kg e bebi 1,5 litros de água.', '2026-10-16')
        self.assertEqual(drafts[0]['values'], {'date': '2026-10-16', 'weight_kg': 82.4})
        self.assertEqual(drafts[1]['values']['volume_ml'], 1500)

    def test_rejects_unknown_types_and_nested_values(self):
        for payload in ({'records': [{'kind': 'sql', 'values': {}}]},
                        {'records': [{'kind': 'body', 'values': {'weight_kg': {'command': 'delete'}}}]}):
            with self.assertRaises(ValueError):
                normalize_drafts(payload, '2026-10-16')

    def test_missing_fields_remain_pending_and_no_taco_provenance_forged(self):
        drafts, _ = normalize_drafts({'records': [
            {'kind': 'medication', 'values': {'name': 'Medicamento', 'status': 'Não tomado'}},
            {'kind': 'food', 'values': {'source': 'TACO (NEPA/UNICAMP)', 'kcal': 123, 'food_name': 'Arroz'}}]}, '2026-10-16')
        self.assertNotIn('taken_dose', drafts[0]['values'])
        self.assertTrue(draft_error(drafts[0]))
        self.assertEqual(drafts[1]['values']['source'], 'Não informado')
        self.assertNotIn('kcal', drafts[1]['values'])
        self.assertEqual(drafts[0]['values']['date'], '2026-10-16')

    def test_recording_stop_writes_local_wav_without_microphone(self):
        import wave
        from pathlib import Path
        with tempfile.TemporaryDirectory(dir='test-output') as folder:
            recorder = Recorder()
            recorder.data.extend(b'\0\0' * 16000)
            path = Path(folder) / 'audio.wav'
            recorder.stop(path)
            with wave.open(str(path)) as audio:
                self.assertEqual(audio.getnframes(), 16000)
                self.assertEqual(audio.getframerate(), 16000)
            self.assertEqual(recorder.data, b'')


class OfflineAssistantUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='test-output')
        self.store = Store(self.temp.name)
        self.app = App(self.store)
        self.app.withdraw()
        self.window = AssistantWindow(self.app)
        self.window.withdraw()

    def tearDown(self):
        self.window.drafts = []
        self.window.close()
        self.app.shutdown()
        self.temp.cleanup()

    def test_drafts_do_not_write_until_save_and_retry_does_not_duplicate(self):
        self.window.queue.put(('drafts', ([{'kind': 'body', 'values': {'date': '2026-10-16', 'weight_kg': 82.4}},
                                            {'kind': 'hydration', 'values': {'date': '2026-10-16', 'drink': 'Água', 'is_water': 'Sim', 'volume_ml': 500}}], [])))
        self.window.poll()
        self.assertEqual(self.store.rows('body'), [])
        self.window.save()
        self.window.save()
        self.assertEqual(len(self.store.rows('body')), 1)
        self.assertEqual(self.store.rows('hydration')[0]['volume_ml'], 500)

    def test_incomplete_draft_blocks_batch_and_edit_can_complete_it(self):
        self.window.drafts = [{'kind': 'study', 'values': {'date': '2026-10-16', 'topic': 'Medicina', 'duration_min': 60}}]
        self.window.refresh()
        self.window.save()
        self.assertEqual(self.store.rows('study'), [])
        self.window.tree.selection_set('0')
        self.window.select()
        self.window.fields['format'].set('Leitura')
        self.window.save()
        self.assertEqual(len(self.store.rows('study')), 1)

    def test_recording_never_starts_on_window_open(self):
        with patch('offline_ai.Recorder.start') as start:
            from navigation import AREAS
            self.assertNotIn('assistant', [key for key, _, _ in AREAS])
            self.assertFalse(hasattr(self.app, 'open_assistant'))
            start.assert_not_called()
