"""
View Collected Data Screen
- Table of all locally stored survey records
- Tap any record to see full details
- "Show on Map" button opens Google Maps with all points
"""
import threading
import webbrowser
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder

KV = """
<ViewDataScreen>:
    name: 'view'

    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: app.theme_cls.backgroundColor

        MDTopAppBar:
            title: "Collected Data"
            left_action_items: [["arrow-left", lambda x: root.go_back()]]
            right_action_items: [["map-marker-multiple", lambda x: root.show_all_on_map()]]
            md_bg_color: app.theme_cls.primaryColor
            specific_text_color: 1, 1, 1, 1

        MDBoxLayout:
            padding: "8dp"
            size_hint_y: None
            height: "48dp"
            MDLabel:
                id: lbl_count
                text: "Loading records…"
                theme_text_color: "Secondary"
                font_style: "Caption"

        MDScrollView:
            MDList:
                id: list_view

        MDBoxLayout:
            size_hint_y: None
            height: "56dp"
            padding: "16dp", "8dp"
            spacing: "16dp"

            MDRaisedButton:
                text: "Refresh"
                icon: "refresh"
                on_release: root.load_records()

            MDRaisedButton:
                text: "View All on Map"
                icon: "map"
                md_bg_color: 0.2, 0.6, 0.85, 1
                on_release: root.show_all_on_map()
"""

Builder.load_string(KV)


class ViewDataScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._records = []

    def on_enter(self):
        self.load_records()

    def load_records(self):
        def _work():
            from utils.local_db import get_all_surveys
            records = get_all_surveys()
            Clock.schedule_once(lambda dt: self._render_records(records), 0)
        threading.Thread(target=_work, daemon=True).start()

    def _render_records(self, records):
        from kivymd.uix.list import TwoLineAvatarIconListItem, IconLeftWidget
        from kivymd.uix.label import MDLabel

        self._records = records
        lst = self.ids.list_view
        lst.clear_widgets()

        if not records:
            lbl = MDLabel(
                text="No records found. Collect some data first.",
                halign='center',
                theme_text_color='Secondary',
            )
            lst.add_widget(lbl)
            self.ids.lbl_count.text = "0 records"
            return

        self.ids.lbl_count.text = (
            f"{len(records)} records  |  "
            f"Synced: {sum(1 for r in records if r.get('synced'))}  |  "
            f"Pending: {sum(1 for r in records if not r.get('synced'))}"
        )

        for rec in records:
            icon = 'cloud-check' if rec.get('synced') else 'cloud-upload'
            icon_color = (0.1, 0.6, 0.1, 1) if rec.get('synced') else (0.9, 0.5, 0, 1)

            item = TwoLineAvatarIconListItem(
                text=f"[{rec['sno']}] {rec.get('crop_name','?')} — {rec.get('crop_stage','')}",
                secondary_text=(
                    f"{rec.get('date_time','?')} | "
                    f"{rec.get('latitude',0):.5f}, {rec.get('longitude',0):.5f}"
                ),
            )
            av = IconLeftWidget(icon=icon)
            av.theme_text_color = 'Custom'
            av.text_color = icon_color
            item.add_widget(av)
            item.bind(on_release=lambda x, r=rec: self.show_detail(r))
            lst.add_widget(item)

    def show_detail(self, record: dict):
        """Show a dialog with the full record details."""
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        fields = [
            ('Sno',          record.get('sno')),
            ('Crop',         record.get('crop_name')),
            ('Stage',        record.get('crop_stage')),
            ('Season',       record.get('season')),
            ('Water Source', record.get('water_source')),
            ('Lat / Lon',    f"{record.get('latitude',0):.6f}, {record.get('longitude',0):.6f}"),
            ('Date & Time',  record.get('date_time')),
            ('Remarks',      record.get('description_rem')),
            ('Synced',       'Yes' if record.get('synced') else 'No'),
        ]
        detail_text = '\n'.join(f"• {k}: {v}" for k, v in fields if v)

        buttons = [
            MDFlatButton(
                text="CLOSE",
                on_release=lambda x: dlg.dismiss()
            ),
            MDFlatButton(
                text="ON MAP",
                on_release=lambda x, r=record: (dlg.dismiss(), self.show_single_on_map(r))
            ),
        ]
        dlg = MDDialog(
            title=f"Record #{record.get('sno')}",
            text=detail_text,
            buttons=buttons,
        )
        dlg.open()

    def show_single_on_map(self, record: dict):
        lat = record.get('latitude', 0)
        lon = record.get('longitude', 0)
        crop = record.get('crop_name', '')
        url = (
            f"https://www.google.com/maps/search/?api=1"
            f"&query={lat},{lon}&query_place_id={crop}"
        )
        webbrowser.open(url)

    def show_all_on_map(self):
        """Open Google Maps My Maps URL with all survey points."""
        if not self._records:
            return
        # Google Maps directions with up to 8 waypoints; for full display use KML
        # Build a simple multi-marker URL
        coords = '|'.join(
            f"{r['latitude']},{r['longitude']}"
            for r in self._records[:20]  # browser limit
        )
        # Opens first point with all others listed
        first = self._records[0]
        url = (
            f"https://www.google.com/maps/dir/"
            + '/'.join(
                f"{r['latitude']},{r['longitude']}"
                for r in self._records[:10]
            )
        )
        webbrowser.open(url)

    def go_back(self):
        self.manager.current = 'main'
