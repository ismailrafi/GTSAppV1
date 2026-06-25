"""
Sync Data Screen
Uploads all unsynced local records to the Django backend.
Shows progress, success count, and error details.
"""
import threading
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.lang import Builder

KV = """
<SyncDataScreen>:
    name: 'sync'

    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: app.theme_cls.backgroundColor

        MDTopAppBar:
            title: "Sync Data"
            left_action_items: [["arrow-left", lambda x: root.go_back()]]
            md_bg_color: app.theme_cls.primaryColor
            specific_text_color: 1, 1, 1, 1

        MDBoxLayout:
            orientation: 'vertical'
            padding: "24dp"
            spacing: "20dp"

            MDCard:
                padding: "20dp"
                radius: [8]
                adaptive_height: True
                orientation: 'vertical'
                MDBoxLayout:
                    orientation: 'vertical'
                    spacing: "12dp"
                    adaptive_height: True

                    MDLabel:
                        text: "Server Configuration"
                        font_style: "H6"
                        size_hint_y: None
                        height: "36dp"

                    MDTextField:
                        id: txt_server_url
                        hint_text: "Backend URL"
                        text: "http://192.168.1.100:8000/api"
                        size_hint_y: None
                        height: "48dp"

                    MDTextField:
                        id: txt_user_id
                        hint_text: "User ID"
                        text: "surveyor_001"
                        size_hint_y: None
                        height: "48dp"

            MDCard:
                padding: "20dp"
                radius: [8]
                size_hint_y: None
                height: "180dp"
                MDBoxLayout:
                    orientation: 'vertical'
                    spacing: "8dp"

                    MDLabel:
                        id: lbl_pending
                        text: "…"
                        font_style: "H5"
                        halign: "center"

                    MDLabel:
                        id: lbl_sync_status
                        text: "Tap 'Sync Now' to upload pending records"
                        halign: "center"
                        theme_text_color: "Secondary"

                    MDProgressBar:
                        id: progress_bar
                        value: 0
                        max: 100
                        size_hint_y: None
                        height: "12dp"

            MDRaisedButton:
                text: "  Sync Now"
                icon: "cloud-upload"
                size_hint_x: 1
                height: "64dp"
                font_size: "18sp"
                md_bg_color: 0.13, 0.62, 0.44, 1
                on_release: root.start_sync()

            MDScrollView:
                MDList:
                    id: sync_log

        Widget:
            size_hint_y: 1
"""

Builder.load_string(KV)


class SyncDataScreen(Screen):
    def on_enter(self):
        self._refresh_pending()

    def _refresh_pending(self):
        def _work():
            from utils.local_db import get_survey_count
            counts = get_survey_count()
            Clock.schedule_once(lambda dt: self._set_pending(counts), 0)
        threading.Thread(target=_work, daemon=True).start()

    def _set_pending(self, counts):
        total   = counts.get('total', 0)
        unsynced= counts.get('unsynced', 0)
        self.ids.lbl_pending.text = (
            f"{unsynced} pending  /  {total} total"
        )

    def start_sync(self):
        import os
        server_url = self.ids.txt_server_url.text.strip()
        os.environ['BACKEND_URL'] = server_url

        self.ids.lbl_sync_status.text = "Starting sync…"
        self.ids.progress_bar.value = 0
        self.ids.sync_log.clear_widgets()

        def _work():
            from utils.local_db import get_unsynced_surveys, mark_synced
            from utils.api_client import sync_records

            records = get_unsynced_surveys()
            if not records:
                Clock.schedule_once(
                    lambda dt: setattr(self.ids.lbl_sync_status, 'text',
                                       'Nothing to sync!'), 0
                )
                return

            total = len(records)
            Clock.schedule_once(
                lambda dt: setattr(self.ids.lbl_sync_status, 'text',
                                   f"Uploading {total} records…"), 0
            )

            # Upload in batches of 10
            BATCH = 10
            synced_count = 0
            error_count  = 0

            for i in range(0, total, BATCH):
                batch = records[i:i + BATCH]
                result = sync_records(batch)

                if result.get('ok'):
                    data = result['data']
                    # Mark records as synced
                    for rec, srv_id in zip(batch, data.get('created_ids', [])):
                        mark_synced(rec['sno'])
                        synced_count += 1
                    error_count += len(data.get('errors', []))
                else:
                    error_count += len(batch)
                    self._log(f"Batch error: {result.get('error')}")

                progress = int((i + len(batch)) / total * 100)
                Clock.schedule_once(
                    lambda dt, p=progress, s=synced_count: (
                        setattr(self.ids.progress_bar, 'value', p),
                        setattr(self.ids.lbl_sync_status, 'text',
                                f"Uploaded {s}/{total}…")
                    ), 0
                )

            Clock.schedule_once(
                lambda dt: self._on_sync_complete(synced_count, error_count), 0
            )

        threading.Thread(target=_work, daemon=True).start()

    def _on_sync_complete(self, synced: int, errors: int):
        self.ids.progress_bar.value = 100
        self.ids.lbl_sync_status.text = (
            f"✅ Sync complete: {synced} uploaded, {errors} errors"
        )
        self._refresh_pending()
        self._log(f"Done. Synced: {synced}, Errors: {errors}")

    def _log(self, msg: str):
        from kivymd.uix.list import OneLineListItem
        item = OneLineListItem(text=msg)
        Clock.schedule_once(lambda dt: self.ids.sync_log.add_widget(item), 0)

    def go_back(self):
        self.manager.current = 'main'
