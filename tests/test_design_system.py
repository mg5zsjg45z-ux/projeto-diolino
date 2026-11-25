import unittest
import tempfile
from design_system import grid_columns, navigation_width
from storage import Store

class LayoutTests(unittest.TestCase):
    def test_breakpoints(self):
        self.assertEqual([navigation_width(w) for w in (1050,1199,1200,1920)], [168,168,232,232])
        self.assertEqual([grid_columns(w) for w in (1,439,440,660,2000)], [1,1,2,3,3])

    def test_shell_and_home(self):
        from app import App
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            try:
                app = App(store)
                try:
                    app.withdraw()
                    app.update_idletasks()
                    app.toggle_navigation()
                    self.assertTrue(app.sidebar_hidden)
                    self.assertFalse(app.sidebar.winfo_manager())
                    app.toggle_navigation()
                    self.assertEqual(app.sidebar.winfo_manager(), 'pack')
                    app.navigate('studies')
                    app.navigate('home')
                    app.update_idletasks()
                    self.assertEqual(app.page, 'home')
                    self.assertEqual(store.rows('study'), [])
                    self.assertEqual(store.rows('workout'), [])
                finally:
                    app.shutdown()
            finally:
                # App.shutdown normally closes the store.
                pass
