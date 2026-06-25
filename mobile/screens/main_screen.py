"""
Main Screen
Buttons: Collect Data | View Collected Data | Sync Data | Exit
"""
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder
from kivy.clock import Clock
import threading

from utils.local_db import get_survey_count

KV = """
<MainScreen>:
    name: 'main'

    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: app.theme_cls.backgroundColor

        # ── App Bar ──────────────────────────────────────────────────────────
        MDTopAppBar:
            title: "CropSurvey GT"
            md_bg_color: app.theme_cls.primaryColor
            specific_text_color: 1, 1, 1, 1
            elevation: 4

        # ── Status strip ─────────────────────────────────────────────────────
        MDCard:
            size_hint_y: None
            height: "56dp"
            padding: "16dp", "8dp"
            md_bg_color: 0.2, 0.6, 0.2, 0.15
            MDBoxLayout:
                orientation: 'horizontal'
                spacing: "8dp"
                MDIcon:
                    icon: "database"
                    theme_text_color: "Custom"
                    text_color: 0.1, 0.6, 0.1, 1
                MDLabel:
                    id: lbl_status
                    text: "Loading…"
                    theme_text_color: "Custom"
                    text_color: 0.1, 0.5, 0.1, 1
                    font_style: "Body2"

        # ── Main menu buttons ─────────────────────────────────────────────────
        MDBoxLayout:
            orientation: 'vertical'
            padding: "32dp"
            spacing: "24dp"

            Widget:
                size_hint_y: 0.05

            # Collect Data
            MDRaisedButton:
                text: "  Collect Data"
                icon: "map-marker-plus"
                size_hint: 1, None
                height: "72dp"
                font_size: "18sp"
                md_bg_color: app.theme_cls.primaryColor
                on_release: root.go_collect()

            # View Collected Data
            MDRaisedButton:
                text: "  View Collected Data"
                icon: "table-eye"
                size_hint: 1, None
                height: "72dp"
                font_size: "18sp"
                md_bg_color: 0.18, 0.52, 0.78, 1
                on_release: root.go_view()

            # Sync Data
            MDRaisedButton:
                text: "  Sync Data"
                icon: "cloud-upload"
                size_hint: 1, None
                height: "72dp"
                font_size: "18sp"
                md_bg_color: 0.13, 0.62, 0.44, 1
                on_release: root.go_sync()

            Widget:
                size_hint_y: 1

            # Exit
            MDFlatButton:
                text: "Exit"
                theme_text_color: "Custom"
                text_color: 0.7, 0.1, 0.1, 1
                size_hint: None, None
                size: "120dp", "48dp"
                pos_hint: {"center_x": .5}
                on_release: app.stop()

            Widget:
                size_hint_y: 0.05
"""

Builder.load_string(KV)


class MainScreen(Screen):
    def on_enter(self):
        """Refresh record count every time this screen is shown."""
        Clock.schedule_once(lambda dt: self._refresh_status(), 0.2)

    def _refresh_status(self):
        def _work():
            counts = get_survey_count()
            msg = (
                f"Total: {counts.get('total', 0)} records  |  "
                f"Pending sync: {counts.get('unsynced', 0)}"
            )
            Clock.schedule_once(lambda dt: self._set_status(msg), 0)
        threading.Thread(target=_work, daemon=True).start()

    def _set_status(self, msg: str):
        self.ids.lbl_status.text = msg

    def go_collect(self):
        self.manager.current = 'collect'

    def go_view(self):
        self.manager.current = 'view'

    def go_sync(self):
        self.manager.current = 'sync'
