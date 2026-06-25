"""
CropSurvey GT Mobile Application
Entry point — sets up KivyMD theme and ScreenManager.

Run:  python main.py
Build for Android:  buildozer android debug deploy run
"""
import os
import sys
import logging

# ── Kivy config (must be before any kivy imports) ─────────────────────────────
os.environ.setdefault('KIVY_NO_CONSOLELOG', '0')
from kivy.config import Config
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '800')
Config.set('graphics', 'resizable', True)

from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.clock import Clock
from kivy.lang import Builder

# ── App screens ───────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from screens.main_screen        import MainScreen
from screens.collect_data_screen import CollectDataScreen
from screens.view_data_screen   import ViewDataScreen
from screens.sync_screen        import SyncDataScreen

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)s %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class CropSurveyApp(MDApp):
    def build(self):
        # ── Theme ─────────────────────────────────────────────────────────────
        self.theme_cls.theme_style  = "Light"
        self.theme_cls.primary_palette = "Green"
        self.theme_cls.accent_palette  = "Teal"
        self.title = "CropSurvey GT"

        # ── Screen manager ────────────────────────────────────────────────────
        sm = ScreenManager(transition=FadeTransition(duration=0.15))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(CollectDataScreen(name='collect'))
        sm.add_widget(ViewDataScreen(name='view'))
        sm.add_widget(SyncDataScreen(name='sync'))
        return sm

    def on_start(self):
        logger.info("CropSurvey app started")

    def on_stop(self):
        from utils.gps_utils import stop_gps
        stop_gps()
        logger.info("CropSurvey app stopped")


if __name__ == '__main__':
    CropSurveyApp().run()
