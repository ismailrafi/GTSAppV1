"""
Collect Data Screen
Full survey data collection workflow:
  1. GPS location (accuracy ≤ 3 m, wait ≤ 30 s)
  2. Bearing/distance slider offset
  3. Manual Google Maps location picker
  4. Crop name (editable dropdown by category)
  5. Date & Time (auto)
  6. Spectral Indices via GEE
  7. Unsupervised classification via GEE
  8. Supervised classification via GEE
  9. 3 geotagged landscape photos
 10. Water source, crop stage, season dropdowns
 11. Description / remarks
 12. Save to local SQLite → back to main
"""
import os
import sys
import threading
import base64
import io
import logging
from datetime import datetime

from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder

logger = logging.getLogger(__name__)

# ── Lazy imports (avoid crash on desktop dev machines) ────────────────────────
try:
    from kivymd.uix.dialog import MDDialog
    from kivymd.uix.button import MDFlatButton, MDRaisedButton
    from kivymd.uix.snackbar import Snackbar
except ImportError:
    pass

KV = """
<CollectDataScreen>:
    name: 'collect'

    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: app.theme_cls.backgroundColor

        # ── App bar ──────────────────────────────────────────────────────────
        MDTopAppBar:
            title: "Collect Data"
            left_action_items: [["arrow-left", lambda x: root.go_back()]]
            md_bg_color: app.theme_cls.primaryColor
            specific_text_color: 1, 1, 1, 1

        MDScrollView:
            MDBoxLayout:
                orientation: 'vertical'
                padding: "16dp"
                spacing: "14dp"
                adaptive_height: True

                # ════════════════════════════════════════
                # 1. LOCATION SECTION
                # ════════════════════════════════════════
                MDCard:
                    padding: "12dp"
                    radius: [8]
                    adaptive_height: True
                    MDBoxLayout:
                        orientation: 'vertical'
                        spacing: "8dp"
                        adaptive_height: True

                        MDLabel:
                            text: "  📍 Location"
                            font_style: "H6"
                            size_hint_y: None
                            height: "36dp"

                        MDLabel:
                            id: lbl_gps_status
                            text: "Press 'Get GPS' to acquire location"
                            theme_text_color: "Secondary"
                            size_hint_y: None
                            height: "28dp"

                        MDBoxLayout:
                            spacing: "8dp"
                            size_hint_y: None
                            height: "48dp"
                            MDTextField:
                                id: txt_lat
                                hint_text: "Latitude"
                                readonly: True
                                size_hint_x: 0.5
                            MDTextField:
                                id: txt_lon
                                hint_text: "Longitude"
                                readonly: True
                                size_hint_x: 0.5

                        MDTextField:
                            id: txt_accuracy
                            hint_text: "Accuracy (m)"
                            readonly: True
                            size_hint_y: None
                            height: "48dp"

                        MDBoxLayout:
                            spacing: "8dp"
                            size_hint_y: None
                            height: "48dp"
                            MDRaisedButton:
                                text: "Get GPS"
                                icon: "crosshairs-gps"
                                on_release: root.acquire_gps()
                            MDFlatButton:
                                text: "Clear"
                                on_release: root.clear_location()
                            MDFlatButton:
                                text: "Manual (Maps)"
                                on_release: root.open_maps_picker()

                        # ── Bearing / distance slider ─────────────────────
                        MDLabel:
                            text: "Offset Location (bearing & distance)"
                            font_style: "Caption"
                            size_hint_y: None
                            height: "24dp"

                        MDBoxLayout:
                            spacing: "8dp"
                            size_hint_y: None
                            height: "48dp"
                            MDTextField:
                                id: txt_bearing
                                hint_text: "Bearing (°)"
                                input_filter: 'float'
                                text: "0"
                                size_hint_x: 0.4
                            MDTextField:
                                id: txt_distance
                                hint_text: "Distance (m)"
                                input_filter: 'float'
                                text: "0"
                                size_hint_x: 0.4
                            MDFlatButton:
                                text: "Apply"
                                size_hint_x: 0.2
                                on_release: root.apply_offset()

                # ════════════════════════════════════════
                # 2. CROP NAME
                # ════════════════════════════════════════
                MDCard:
                    padding: "12dp"
                    radius: [8]
                    adaptive_height: True
                    MDBoxLayout:
                        orientation: 'vertical'
                        spacing: "8dp"
                        adaptive_height: True

                        MDLabel:
                            text: "  🌾 Crop Name"
                            font_style: "H6"
                            size_hint_y: None
                            height: "36dp"

                        MDTextField:
                            id: txt_crop_name
                            hint_text: "Select or type crop name"
                            size_hint_y: None
                            height: "48dp"
                            on_text: root.filter_crops(self.text)

                        MDBoxLayout:
                            id: crop_suggestions
                            orientation: 'vertical'
                            adaptive_height: True

                # ════════════════════════════════════════
                # 3. DATE & TIME
                # ════════════════════════════════════════
                MDCard:
                    padding: "12dp"
                    radius: [8]
                    size_hint_y: None
                    height: "80dp"
                    MDBoxLayout:
                        orientation: 'vertical'
                        MDLabel:
                            text: "  🕐 Current Date & Time"
                            font_style: "H6"
                            size_hint_y: None
                            height: "32dp"
                        MDTextField:
                            id: txt_datetime
                            hint_text: "Date & Time"
                            readonly: True

                # ════════════════════════════════════════
                # 4. SPECTRAL INDICES
                # ════════════════════════════════════════
                MDCard:
                    padding: "12dp"
                    radius: [8]
                    adaptive_height: True
                    MDBoxLayout:
                        orientation: 'vertical'
                        spacing: "8dp"
                        adaptive_height: True

                        MDLabel:
                            text: "  🛰 Sentinel Analysis"
                            font_style: "H6"
                            size_hint_y: None
                            height: "36dp"

                        MDLabel:
                            id: lbl_gee_status
                            text: "Requires server connection and GEE setup"
                            theme_text_color: "Secondary"
                            font_style: "Caption"
                            size_hint_y: None
                            height: "24dp"

                        MDBoxLayout:
                            spacing: "8dp"
                            size_hint_y: None
                            height: "48dp"
                            MDRaisedButton:
                                text: "Indices"
                                icon: "layers"
                                md_bg_color: 0.1, 0.5, 0.8, 1
                                on_release: root.run_indices()
                            MDRaisedButton:
                                text: "Unsupervised"
                                icon: "scatter-plot"
                                md_bg_color: 0.5, 0.1, 0.8, 1
                                on_release: root.run_unsupervised()
                            MDRaisedButton:
                                text: "Supervised"
                                icon: "robot"
                                md_bg_color: 0.8, 0.4, 0.0, 1
                                on_release: root.run_supervised()

                        # Image result placeholders
                        MDBoxLayout:
                            id: box_indices_imgs
                            spacing: "4dp"
                            size_hint_y: None
                            height: "0dp"

                # ════════════════════════════════════════
                # 5. PHOTOS
                # ════════════════════════════════════════
                MDCard:
                    padding: "12dp"
                    radius: [8]
                    adaptive_height: True
                    MDBoxLayout:
                        orientation: 'vertical'
                        spacing: "8dp"
                        adaptive_height: True

                        MDLabel:
                            text: "  📷 Geotagged Photos (Landscape)"
                            font_style: "H6"
                            size_hint_y: None
                            height: "36dp"

                        MDBoxLayout:
                            spacing: "8dp"
                            size_hint_y: None
                            height: "48dp"
                            MDRaisedButton:
                                text: "Photo 1"
                                icon: "camera"
                                on_release: root.take_photo(1)
                            MDRaisedButton:
                                text: "Photo 2"
                                icon: "camera"
                                on_release: root.take_photo(2)
                            MDRaisedButton:
                                text: "Photo 3"
                                icon: "camera"
                                on_release: root.take_photo(3)

                        MDLabel:
                            id: lbl_photo_status
                            text: "No photos taken yet"
                            theme_text_color: "Secondary"
                            font_style: "Caption"
                            size_hint_y: None
                            height: "24dp"

                # ════════════════════════════════════════
                # 6. DROPDOWNS
                # ════════════════════════════════════════
                MDCard:
                    padding: "12dp"
                    radius: [8]
                    adaptive_height: True
                    MDBoxLayout:
                        orientation: 'vertical'
                        spacing: "10dp"
                        adaptive_height: True

                        MDLabel:
                            text: "  📋 Field Information"
                            font_style: "H6"
                            size_hint_y: None
                            height: "36dp"

                        MDTextField:
                            id: txt_water_source
                            hint_text: "Water Source"
                            readonly: True
                            on_focus: if self.focus: root.show_dropdown('water_source')

                        MDTextField:
                            id: txt_crop_stage
                            hint_text: "Crop Stage"
                            readonly: True
                            on_focus: if self.focus: root.show_dropdown('crop_stage')

                        MDTextField:
                            id: txt_season
                            hint_text: "Season"
                            readonly: True
                            on_focus: if self.focus: root.show_dropdown('season')

                # ════════════════════════════════════════
                # 7. REMARKS
                # ════════════════════════════════════════
                MDCard:
                    padding: "12dp"
                    radius: [8]
                    adaptive_height: True
                    MDTextField:
                        id: txt_remarks
                        hint_text: "Description / Remarks"
                        multiline: True
                        size_hint_y: None
                        height: "96dp"

                # ════════════════════════════════════════
                # SAVE / CANCEL
                # ════════════════════════════════════════
                MDBoxLayout:
                    spacing: "16dp"
                    size_hint_y: None
                    height: "56dp"
                    padding: "0dp", "4dp"

                    MDRaisedButton:
                        text: "  SAVE"
                        icon: "content-save"
                        md_bg_color: 0.1, 0.6, 0.1, 1
                        size_hint_x: 0.5
                        on_release: root.save_record()

                    MDFlatButton:
                        text: "CANCEL"
                        theme_text_color: "Custom"
                        text_color: 0.7, 0.1, 0.1, 1
                        size_hint_x: 0.5
                        on_release: root.cancel()

                Widget:
                    size_hint_y: None
                    height: "16dp"
"""

Builder.load_string(KV)


class CollectDataScreen(Screen):
    """Main data collection screen."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._lat: float = 0.0
        self._lon: float = 0.0
        self._accuracy: float = 0.0
        self._bearing: float = 0.0
        self._distance: float = 0.0
        self._photos = {1: None, 2: None, 3: None}
        self._indices_b64: str = ''
        self._unsupervised_b64: str = ''
        self._supervised_b64: str = ''
        self._dialog = None

    def on_enter(self):
        self._refresh_datetime()
        Clock.schedule_interval(self._refresh_datetime, 1)
        self._populate_crop_suggestions('')

    def on_leave(self):
        Clock.unschedule(self._refresh_datetime)

    def _refresh_datetime(self, *args):
        self.ids.txt_datetime.text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ── GPS ──────────────────────────────────────────────────────────────────

    def acquire_gps(self):
        self.ids.lbl_gps_status.text = "Acquiring GPS… (up to 30 s)"
        def _work():
            from utils.gps_utils import get_location_blocking
            def _progress(msg):
                Clock.schedule_once(lambda dt: setattr(self.ids.lbl_gps_status, 'text', msg), 0)
            loc = get_location_blocking(timeout=30, target_accuracy=3.0, on_progress=_progress)
            Clock.schedule_once(lambda dt: self._on_gps_result(loc), 0)
        threading.Thread(target=_work, daemon=True).start()

    def _on_gps_result(self, loc):
        if loc and loc.is_valid:
            self._lat = loc.latitude
            self._lon = loc.longitude
            self._accuracy = loc.accuracy or 0
            self.ids.txt_lat.text = f"{self._lat:.7f}"
            self.ids.txt_lon.text = f"{self._lon:.7f}"
            self.ids.txt_accuracy.text = f"{self._accuracy:.1f} m"
            acc_ok = self._accuracy <= 3.0
            self.ids.lbl_gps_status.text = (
                f"✅ GPS acquired (accuracy: {self._accuracy:.1f} m)"
                if acc_ok else
                f"⚠ GPS acquired but accuracy {self._accuracy:.1f} m > 3 m"
            )
        else:
            self.ids.lbl_gps_status.text = "❌ Could not acquire GPS"

    def clear_location(self):
        self._lat = self._lon = self._accuracy = 0.0
        self.ids.txt_lat.text = ''
        self.ids.txt_lon.text = ''
        self.ids.txt_accuracy.text = ''
        self.ids.lbl_gps_status.text = "Location cleared. Press 'Get GPS'."

    def apply_offset(self):
        """Offset the GPS coordinate by bearing and distance."""
        try:
            bearing  = float(self.ids.txt_bearing.text or 0)
            distance = float(self.ids.txt_distance.text or 0)
            if distance == 0:
                return
            from utils.gps_utils import offset_location
            new_lat, new_lon = offset_location(self._lat, self._lon, distance, bearing)
            self._lat, self._lon = new_lat, new_lon
            self._bearing  = bearing
            self._distance = distance
            self.ids.txt_lat.text = f"{new_lat:.7f}"
            self.ids.txt_lon.text = f"{new_lon:.7f}"
            self.ids.lbl_gps_status.text = (
                f"Offset applied: {distance:.1f} m @ {bearing:.1f}°"
            )
        except ValueError:
            self._snack("Enter valid bearing (°) and distance (m)")

    def open_maps_picker(self):
        """Open Google Maps in browser for manual coordinate selection."""
        import webbrowser
        url = f"https://www.google.com/maps/search/?api=1&query={self._lat},{self._lon}"
        webbrowser.open(url)
        self._snack("Copy the coordinates from Google Maps and enter below")

    # ── Crop name ─────────────────────────────────────────────────────────────

    def _populate_crop_suggestions(self, query: str):
        from kivymd.uix.button import MDFlatButton
        box = self.ids.crop_suggestions
        box.clear_widgets()
        if not query:
            return
        from data.crop_data import ALL_CROPS, CROP_CATEGORIES
        q = query.lower()
        matches = [c for c in ALL_CROPS if q in c.lower()][:8]
        for name in matches:
            btn = MDFlatButton(text=name, size_hint_y=None, height='36dp')
            btn.bind(on_release=lambda b, n=name: self._select_crop(n))
            box.add_widget(btn)

    def filter_crops(self, text: str):
        Clock.schedule_once(lambda dt: self._populate_crop_suggestions(text), 0.1)

    def _select_crop(self, name: str):
        self.ids.txt_crop_name.text = name
        self.ids.crop_suggestions.clear_widgets()

    # ── GEE Analysis ──────────────────────────────────────────────────────────

    def _check_location(self) -> bool:
        if not self._lat and not self._lon:
            self._snack("Please acquire GPS location first")
            return False
        return True

    def run_indices(self):
        if not self._check_location():
            return
        self.ids.lbl_gee_status.text = "Computing indices… (may take 1–2 min)"
        def _work():
            from utils.api_client import compute_indices
            result = compute_indices(self._lat, self._lon)
            Clock.schedule_once(lambda dt: self._on_indices_done(result), 0)
        threading.Thread(target=_work, daemon=True).start()

    def _on_indices_done(self, result):
        if result.get('ok'):
            data = result['data']
            self._indices_b64 = data.get('ndvi_b64', '')
            self.ids.lbl_gee_status.text = (
                f"Indices ready. {data.get('s2_scenes_used',0)} S2 scenes used."
            )
            self._show_image_result(self._indices_b64, "NDVI")
        else:
            self.ids.lbl_gee_status.text = f"Error: {result.get('error')}"

    def run_unsupervised(self):
        if not self._check_location():
            return
        self.ids.lbl_gee_status.text = "Running unsupervised classification…"
        def _work():
            from utils.api_client import run_unsupervised
            result = run_unsupervised(self._lat, self._lon, n_classes=10)
            Clock.schedule_once(lambda dt: self._on_unsupervised_done(result), 0)
        threading.Thread(target=_work, daemon=True).start()

    def _on_unsupervised_done(self, result):
        if result.get('ok'):
            data = result['data']
            self._unsupervised_b64 = data.get('classification_b64', '')
            self.ids.lbl_gee_status.text = (
                f"Unsupervised ready. {data.get('n_classes')} classes."
            )
            self._show_image_result(self._unsupervised_b64, "Unsupervised")
        else:
            self.ids.lbl_gee_status.text = f"Error: {result.get('error')}"

    def run_supervised(self):
        if not self._check_location():
            return
        crop_name = self.ids.txt_crop_name.text.strip() or 'Unknown'
        self.ids.lbl_gee_status.text = "Running supervised classification…"
        def _work():
            from utils.api_client import run_supervised
            result = run_supervised(self._lat, self._lon, crop_name=crop_name)
            Clock.schedule_once(lambda dt: self._on_supervised_done(result), 0)
        threading.Thread(target=_work, daemon=True).start()

    def _on_supervised_done(self, result):
        if result.get('ok'):
            data = result['data']
            self._supervised_b64 = data.get('classification_b64', '')
            self.ids.lbl_gee_status.text = (
                f"Supervised ready. Crop: {data.get('primary_crop')}."
            )
            self._show_image_result(self._supervised_b64, "Supervised")
        else:
            self.ids.lbl_gee_status.text = f"Error: {result.get('error')}"

    def _show_image_result(self, b64: str, label: str):
        """Display a base64 PNG thumbnail in the UI."""
        try:
            from kivy.uix.image import Image as KvImage
            from kivy.core.image import Image as CoreImage
            from kivymd.uix.label import MDLabel

            box = self.ids.box_indices_imgs
            box.height = '160dp'

            img_data = base64.b64decode(b64)
            buf = io.BytesIO(img_data)
            core_img = CoreImage(buf, ext='png')

            kv_img = KvImage(texture=core_img.texture,
                             size_hint=(None, None), size=('140dp', '140dp'))
            lbl = MDLabel(text=label, font_style='Caption',
                          size_hint_y=None, height='20dp')

            from kivy.uix.boxlayout import BoxLayout
            col = BoxLayout(orientation='vertical', size_hint=(None, None),
                            size=('140dp', '160dp'))
            col.add_widget(lbl)
            col.add_widget(kv_img)
            box.add_widget(col)
        except Exception as e:
            logger.warning(f"Could not display image: {e}")

    # ── Photos ────────────────────────────────────────────────────────────────

    def take_photo(self, index: int):
        def _work():
            from utils.camera_utils import take_photo, add_geotag_overlay
            path = take_photo(index)
            if path:
                crop_name = self.ids.txt_crop_name.text.strip() or 'Unknown'
                dt_str = self.ids.txt_datetime.text
                labelled = add_geotag_overlay(
                    path, self._lat, self._lon, dt_str, crop_name
                )
                self._photos[index] = labelled
                Clock.schedule_once(lambda dt: self._update_photo_status(), 0)
        threading.Thread(target=_work, daemon=True).start()

    def _update_photo_status(self):
        taken = [i for i, p in self._photos.items() if p]
        self.ids.lbl_photo_status.text = (
            f"Photos taken: {', '.join(map(str,taken))}" if taken else "No photos taken"
        )

    # ── Dropdowns ─────────────────────────────────────────────────────────────

    def show_dropdown(self, field: str):
        from data.crop_data import WATER_SOURCES, CROP_STAGES, SEASONS
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        options_map = {
            'water_source': (WATER_SOURCES, self.ids.txt_water_source),
            'crop_stage':   (CROP_STAGES,   self.ids.txt_crop_stage),
            'season':       (SEASONS,        self.ids.txt_season),
        }
        options, target_field = options_map[field]

        buttons = []
        for opt in options:
            def _cb(widget, o=opt, tf=target_field):
                tf.text = o
                if self._dialog:
                    self._dialog.dismiss()
            buttons.append(MDFlatButton(text=opt, on_release=_cb))

        self._dialog = MDDialog(
            title=field.replace('_', ' ').title(),
            type='simple',
            buttons=buttons,
        )
        self._dialog.open()

    # ── Save ─────────────────────────────────────────────────────────────────

    def save_record(self):
        crop = self.ids.txt_crop_name.text.strip()
        if not crop:
            self._snack("Please enter a crop name")
            return
        if not self._lat and not self._lon:
            self._snack("Please acquire location first")
            return

        record = {
            'user_id':          'surveyor_001',
            'latitude':         self._lat,
            'longitude':        self._lon,
            'bearing_distance': self._distance,
            'bearing_angle':    self._bearing,
            'date_time':        self.ids.txt_datetime.text,
            'crop_name':        crop,
            'crop_stage':       self.ids.txt_crop_stage.text,
            'water_source':     self.ids.txt_water_source.text,
            'season':           self.ids.txt_season.text,
            'indices_b64':      self._indices_b64,
            'unsupervised_b64': self._unsupervised_b64,
            'supervised_b64':   self._supervised_b64,
            'photo1_path':      self._photos.get(1) or '',
            'photo2_path':      self._photos.get(2) or '',
            'photo3_path':      self._photos.get(3) or '',
            'description_rem':  self.ids.txt_remarks.text,
        }

        def _work():
            from utils.local_db import save_survey
            sno = save_survey(record)
            Clock.schedule_once(lambda dt: self._on_saved(sno), 0)
        threading.Thread(target=_work, daemon=True).start()

    def _on_saved(self, sno: int):
        self._snack(f"Record saved locally (sno={sno}). Use Sync to upload.")
        self._reset_form()
        Clock.schedule_once(lambda dt: self.go_back(), 1.2)

    def _reset_form(self):
        self._lat = self._lon = self._accuracy = 0.0
        self._indices_b64 = self._unsupervised_b64 = self._supervised_b64 = ''
        self._photos = {1: None, 2: None, 3: None}
        self.ids.txt_lat.text = ''
        self.ids.txt_lon.text = ''
        self.ids.txt_accuracy.text = ''
        self.ids.txt_crop_name.text = ''
        self.ids.txt_water_source.text = ''
        self.ids.txt_crop_stage.text = ''
        self.ids.txt_season.text = ''
        self.ids.txt_remarks.text = ''
        self.ids.txt_bearing.text = '0'
        self.ids.txt_distance.text = '0'
        self.ids.lbl_gps_status.text = "Location cleared"
        self.ids.lbl_gee_status.text = "Ready"
        self.ids.lbl_photo_status.text = "No photos taken"
        self.ids.box_indices_imgs.clear_widgets()
        self.ids.box_indices_imgs.height = '0dp'

    def cancel(self):
        self._reset_form()
        self.go_back()

    def go_back(self):
        self.manager.current = 'main'

    def _snack(self, msg: str):
        try:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text=msg, duration=2.5).open()
        except Exception:
            print(msg)
