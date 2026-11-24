"""Appearance settings remain local and never change personal records."""
import json
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch
from datetime import date
from pathlib import Path
from tkinter import font as tkfont, ttk

from appearance import DEFAULTS, AppearanceController, load_preferences, save_preferences
from app import App, Editor
from charts import chart
from storage import Store
from surface_ui import RoundedSurface
from visual_icons import OutlineIcon, ICONS, DIRECTORY


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='test-output')
        self.directory = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_round_trip_and_invalid_save_preserves_existing_preferences(self):
        self.assertEqual(load_preferences(self.directory), DEFAULTS)
        prefs = dict(DEFAULTS, theme='dark', text_size='large', density='compact',
                     title_style='modern', shadows='none')
        save_preferences(self.directory, prefs)
        self.assertEqual(load_preferences(self.directory), prefs)
        before = (self.directory / 'appearance.json').read_bytes()
        with self.assertRaises(ValueError):
            save_preferences(self.directory, dict(prefs, theme='invalid'))
        self.assertEqual((self.directory / 'appearance.json').read_bytes(), before)

    def test_corrupt_or_partially_invalid_preferences_recover_to_valid_defaults(self):
        target = self.directory / 'appearance.json'
        target.write_text('{truncated', encoding='utf-8')
        self.assertEqual(load_preferences(self.directory), DEFAULTS)
        target.write_text(json.dumps({'theme': 'dark', 'text_size': 'invalid', 'unknown': 'ignore'}), encoding='utf-8')
        self.assertEqual(load_preferences(self.directory), dict(DEFAULTS, theme='dark'))
        target.write_text('[]', encoding='utf-8')
        self.assertEqual(load_preferences(self.directory), DEFAULTS)


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir='test-output')
        self.directory = Path(self.temp.name)
        self.store = Store(self.directory)
        self.app = App(self.store)
        self.app.withdraw()
        self.app.day.set('2026-10-16')

    def tearDown(self):
        self.app.update_idletasks()
        self.app.shutdown()
        self.temp.cleanup()

    def color(self, widget, option):
        return widget.winfo_rgb(widget.cget(option))

    def test_rounded_cards_follow_theme_and_button_artwork_is_reused(self):
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        self.app.update_idletasks()
        cards = [w for w in descendants(self.app) if isinstance(w, RoundedSurface)]
        self.assertGreaterEqual(len(cards), 4)
        self.app.appearance.activate(dict(DEFAULTS, theme='dark'))
        self.app.update_idletasks()
        for card in cards:
            self.assertEqual(card.body.cget('background'), '#222326')
            self.assertEqual(card._surface_key[-2], '#222326')
        count = len(self.app.appearance._button_artwork)
        for _ in range(3):
            self.app.appearance.configure_styles()
        self.assertEqual(len(self.app.appearance._button_artwork), count)
        self.app.appearance.activate(DEFAULTS)
        self.app.update_idletasks()
        for card in cards:
            self.assertEqual(card.body.cget('background'), '#ffffff')

    def test_compact_padding_and_ornaments_update_without_reopening(self):
        self.app.update_idletasks()
        def find(widget):
            for child in widget.winfo_children():
                if isinstance(child, RoundedSurface):
                    return child
                result = find(child)
                if result is not None:
                    return result
        card = find(self.app)
        before = card.coords(card.window_item)[0]
        self.app.appearance.activate(dict(DEFAULTS, density='compact', ornaments='plain'))
        self.assertLess(card.coords(card.window_item)[0], before)
        self.assertFalse(card._surface_key[4])
        self.app.appearance.activate(DEFAULTS)
        self.assertEqual(card.coords(card.window_item)[0], before)
        self.assertTrue(card._surface_key[4])

    def test_local_outline_icons_follow_selected_navigation_color(self):
        for key, name in ICONS.items():
            self.assertTrue((DIRECTORY / (name+'.png')).is_file())
            icon = self.app.nav_buttons[key][1]
            self.assertIsInstance(icon, OutlineIcon)
        self.app.navigate('data')
        icon = self.app.nav_buttons['data'][1]
        self.assertEqual(icon.icon_signature[-1], icon.cget('foreground'))
        image = icon.icon_image
        icon.refresh_icon()
        self.assertIs(icon.icon_image, image)

    def test_appearance_preview_respects_high_contrast_override(self):
        self.app.navigate('appearance')
        palette = dict(bg='#000000', surface='#000000', ink='#ffff00', muted='#ffff00',
                       line='#ffff00', soft='#000000', nav='#ffff00', nav_text='#000000',
                       accent='#ffff00', shadow='#000000')
        with patch('appearance.high_contrast_palette', return_value=palette):
            self.app.appearance.refresh_accessibility()
            self.assertEqual(self.app.appearance_preview.cget('background'), '#000000')
            for item in self.app.appearance_preview.find_all():
                if self.app.appearance_preview.type(item) == 'text':
                    self.assertEqual(self.app.appearance_preview.itemcget(item, 'fill'), '#ffff00')

    def test_high_contrast_overrides_theme_and_restores_without_saving(self):
        controller = self.app.appearance
        controller.activate(dict(DEFAULTS, theme='dark'))
        palette = dict(bg='#000000', surface='#000000', ink='#ffff00', muted='#ffff00',
                       line='#ffff00', soft='#000000', nav='#ffff00', nav_text='#000000',
                       accent='#ffff00', shadow='#000000')
        with patch('appearance.high_contrast_palette', return_value=palette):
            controller.refresh_accessibility()
            self.assertEqual(self.app.cget('background'), '#000000')
            style = ttk.Style(self.app)
            self.assertEqual(style.lookup('TLabel', 'foreground'), '#ffff00')
            self.assertEqual(style.lookup('TEntry', 'fieldbackground'), '#000000')
            self.assertNotEqual(style.lookup('Accent.TButton', 'background'),
                                style.lookup('Accent.TButton', 'foreground'))
            self.assertEqual(controller.preferences['theme'], 'dark')
        with patch('appearance.high_contrast_palette', return_value=None):
            controller.refresh_accessibility()
        self.assertEqual(self.app.cget('background'), '#17181a')
        self.assertFalse((self.directory / 'appearance.json').exists())

    def test_table_rows_follow_font_metrics_at_multiple_dpi_scales(self):
        original = self.app.tk.call('tk', 'scaling')
        try:
            for scale in (1, 1.25, 1.5, 2):
                self.app.tk.call('tk', 'scaling', scale * 96 / 72)
                self.app.appearance.activate(dict(DEFAULTS, text_size='large', density='compact'))
                style = ttk.Style(self.app)
                height = int(style.lookup('Treeview', 'rowheight'))
                font = tkfont.Font(root=self.app, font=style.lookup('Treeview', 'font'))
                self.assertGreater(height, font.metrics('linespace'))
                self.app.appearance.configure_styles()
                self.assertEqual(height, int(style.lookup('Treeview', 'rowheight')))
        finally:
            self.app.tk.call('tk', 'scaling', original)

    def test_large_text_is_idempotent_and_icon_font_family_is_preserved(self):
        sample = tk.Label(self.app, text='Leitura', font=('Segoe UI', 10))
        icon = tk.Label(self.app, text='\ue787', font=('Segoe MDL2 Assets', 16))
        self.app.appearance.activate(dict(DEFAULTS, text_size='large'))
        self.app.appearance.apply_tree(self.app)
        first = tkfont.Font(root=self.app, font=sample.cget('font')).actual()
        icon_font = tkfont.Font(root=self.app, font=icon.cget('font')).actual()
        self.assertGreater(first['size'], 10)
        self.assertEqual(icon_font['family'], 'Segoe MDL2 Assets')
        for _ in range(3):
            self.app.appearance.apply_tree(self.app)
        self.assertEqual(tkfont.Font(root=self.app, font=sample.cget('font')).actual(), first)
        self.app.appearance.activate(DEFAULTS)
        self.assertEqual(tkfont.Font(root=self.app, font=sample.cget('font')).actual()['size'], 10)

    def test_new_editor_dark_text_and_caret_have_contrast(self):
        self.app.appearance.activate(dict(DEFAULTS, theme='dark'))
        self.app.navigate('study')
        editor = Editor(self.app, 'study')
        editor.withdraw()
        try:
            self.app.update_idletasks()
            text = next(widget for widget in editor.field_widgets.values() if isinstance(widget, tk.Text))
            self.assertLess(sum(self.color(text, 'background')), 3 * 32768)
            self.assertGreater(sum(self.color(text, 'foreground')), 3 * 32768)
            self.assertNotEqual(self.color(text, 'insertbackground'), self.color(text, 'background'))
            style = ttk.Style(self.app)
            self.assertNotEqual(style.lookup('TEntry', 'fieldbackground'), '#ffffff')
        finally:
            editor.destroy()

    def test_saved_preferences_are_applied_when_the_app_reopens(self):
        self.app.update_idletasks()
        self.app.shutdown()
        prefs = dict(DEFAULTS, theme='dark', text_size='large', density='compact', shadows='none')
        save_preferences(self.directory, prefs)
        self.store = Store(self.directory)
        self.app = App(self.store)
        self.app.withdraw()
        self.assertEqual(self.app.appearance.preferences, prefs)
        self.assertLess(sum(self.color(self.app, 'background')), 3 * 32768)
        self.app.navigate('checklist')
        self.assertEqual(self.app.appearance.preferences, prefs)

    def test_selected_calendar_day_remains_readable_on_dark_hover_and_restores_light(self):
        style = ttk.Style(self.app)
        self.app.appearance.activate(dict(DEFAULTS, theme='dark'))
        background = self.app.winfo_rgb(style.lookup('WeekSelected.TButton', 'background', ('active',)))
        foreground = self.app.winfo_rgb(style.lookup('WeekSelected.TButton', 'foreground', ('active',)))
        self.assertGreater(sum(background), 3 * 32768)
        self.assertLess(sum(foreground), 3 * 32768)
        self.app.appearance.activate(DEFAULTS)
        self.assertEqual(style.lookup('WeekSelected.TButton', 'background', ('active',)), '#333333')

    def test_opening_combobox_dropdown_handles_tcl_only_map_widgets(self):
        self.app.navigate('appearance')
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        combo = next(widget for widget in descendants(self.app.content) if isinstance(widget, ttk.Combobox))
        errors = []
        original_handler = self.app.report_callback_exception
        self.app.report_callback_exception = lambda *args: errors.append(args)
        try:
            self.app.deiconify()
            self.app.update_idletasks()
            self.app.tk.call('ttk::combobox::Post', str(combo))
            self.app.update()
            popdown = self.app.tk.call('ttk::combobox::PopdownWindow', str(combo))
            self.assertTrue(self.app.tk.getboolean(self.app.tk.call('winfo', 'ismapped', popdown)))
            self.assertEqual(errors, [])
        finally:
            self.app.tk.call('ttk::combobox::Unpost', str(combo))
            self.app.withdraw()
            self.app.report_callback_exception = original_handler

    def test_shadow_toggle_keeps_title_and_status_symbol_colors(self):
        self.store.set_pillar('2026-10-16', 'medicine_status', True)
        self.store.set_pillar('2026-10-16', 'exercise_status', False)
        self.app.navigate('home')
        self.app.appearance.activate(dict(DEFAULTS, theme='dark', shadows='none'))
        def descendants(widget):
            yield widget
            for child in widget.winfo_children():
                yield from descendants(child)
        canvases = [widget for widget in descendants(self.app.content) if isinstance(widget, tk.Canvas)]
        headings = [widget for widget in canvases if widget.find_withtag('shadow')]
        self.assertTrue(headings)
        for heading in headings:
            self.assertEqual(heading.itemcget('shadow', 'state'), 'hidden')
            self.assertNotEqual(heading.itemcget('title', 'state'), 'hidden')
        indicators = {}
        for canvas in canvases:
            if not any(canvas.type(item) == 'oval' for item in canvas.find_all()):
                continue
            for item in canvas.find_all():
                if canvas.type(item) == 'text':
                    indicators[canvas.itemcget(item, 'text')] = canvas.winfo_rgb(canvas.itemcget(item, 'fill'))
        self.assertEqual(set(indicators), {'✓', '×', '–'})
        green, red = indicators['✓'], indicators['×']
        self.assertGreater(green[1], green[0])
        self.assertGreater(green[1], green[2])
        self.assertGreater(red[0], red[1])
        self.assertGreater(red[0], red[2])
        self.app.appearance.activate(DEFAULTS)
        for heading in headings:
            self.assertEqual(heading.itemcget('shadow', 'state'), 'normal')

    def test_draft_preview_discard_reset_and_save_preserve_records_and_context(self):
        self.store.save('study', {'date': '2026-10-16', 'topic': 'Revisão', 'duration_min': 60, 'format': 'Leitura'})
        records = self.store.rows('study')
        save_preferences(self.directory, DEFAULTS)
        before = (self.directory / 'appearance.json').read_bytes()
        self.app.navigate('appearance')
        self.app.appearance_vars['theme'].set('dark')
        self.app.appearance_vars['text_size'].set('large')
        self.app.update_idletasks()
        self.assertEqual(self.app.appearance.preferences, DEFAULTS)
        self.assertEqual((self.directory / 'appearance.json').read_bytes(), before)
        self.assertEqual(self.store.rows('study'), records)
        self.app.discard_appearance()
        self.assertEqual(self.app.appearance_vars['theme'].get(), 'light')
        self.app.appearance_vars['theme'].set('dark')
        self.app.save_appearance()
        self.assertEqual(load_preferences(self.directory)['theme'], 'dark')
        self.assertEqual(self.app.day.get(), '2026-10-16')
        self.assertEqual(self.app.page, 'appearance')
        self.assertEqual(self.store.rows('study'), records)
        self.app.reset_appearance()
        self.assertEqual({key: var.get() for key, var in self.app.appearance_vars.items()}, DEFAULTS)
        self.assertEqual(load_preferences(self.directory)['theme'], 'dark')
        self.app.discard_appearance()
        self.assertEqual(self.app.appearance_vars['theme'].get(), 'dark')

    def test_dark_chart_keeps_palette_after_resize_and_hover_tip(self):
        self.app.appearance.activate(dict(DEFAULTS, theme='dark'))
        canvas = chart(self.app, 'Peso', [('2026-10-16', 80)], date(2026, 10, 15), date(2026, 10, 17), 'kg')
        canvas.pack()
        def invoke_binding(binding, width, event_type):
            callback = binding.split('[', 1)[1].split(' ', 1)[0]
            self.app.tk.call(callback, 0, 0, 0, 240, 0, 0, 0, width, 100, 100,
                             '', 0, '', 0, str(canvas), event_type, 100, 100, 0)
        # A withdrawn test window does not receive real Configure events.
        configure = canvas.bind('<Configure>')
        invoke_binding(configure, 640, 22)
        self.app.appearance.apply_tree(canvas)
        self.app.update_idletasks()
        invoke_binding(configure, 700, 22)
        self.assertLess(sum(self.color(canvas, 'background')), 3 * 32768)
        texts = [item for item in canvas.find_all() if canvas.type(item) == 'text']
        self.assertTrue(texts)
        for item in texts:
            self.assertGreater(sum(canvas.winfo_rgb(canvas.itemcget(item, 'fill'))), 3 * 32768)
        points = [item for item in canvas.find_all() if canvas.type(item) == 'oval']
        self.assertTrue(points)
        binding = canvas.tag_bind(points[0], '<Enter>')
        self.assertTrue(binding)
        # Invoke the registered item callback without moving the real mouse.
        invoke_binding(binding, 700, 7)
        tips = canvas.find_withtag('tip')
        self.assertTrue(tips)
        backgrounds = [canvas.itemcget(item, 'fill') for item in tips if canvas.type(item) == 'rectangle']
        self.assertTrue(backgrounds)
        self.assertLess(sum(canvas.winfo_rgb(backgrounds[0])), 3 * 32768)


if __name__ == '__main__':
    unittest.main()
