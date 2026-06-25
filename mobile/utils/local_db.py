"""
Local SQLite Database (Offline Storage)
All survey data is saved locally first, then synced to the server.
"""
import sqlite3
import os
import json
import base64
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── Database path ────────────────────────────────────────────────────────────
DB_DIR  = Path(os.path.expanduser('~')) / '.cropsurvey'
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / 'local_survey.db'


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the local GTSurvey table if it does not exist."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS GTSurvey (
            sno                        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id                    TEXT NOT NULL DEFAULT 'default_user',
            latitude                   REAL,
            longitude                  REAL,
            bearing_distance           REAL,
            bearing_angle              REAL,
            date_time                  TEXT,
            crop_name                  TEXT,
            crop_stage                 TEXT,
            water_source               TEXT,
            season                     TEXT,
            indices_b64                TEXT,
            unsupervised_b64           TEXT,
            supervised_b64             TEXT,
            photo1_path                TEXT,
            photo2_path                TEXT,
            photo3_path                TEXT,
            description_rem            TEXT,
            synced                     INTEGER DEFAULT 0,
            created_at                 TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()
    logger.info(f"Local DB initialised at {DB_PATH}")


def save_survey(record: dict) -> int:
    """Insert a survey record and return its local sno."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO GTSurvey (
            user_id, latitude, longitude,
            bearing_distance, bearing_angle,
            date_time, crop_name, crop_stage, water_source, season,
            indices_b64, unsupervised_b64, supervised_b64,
            photo1_path, photo2_path, photo3_path,
            description_rem, synced
        ) VALUES (
            :user_id, :latitude, :longitude,
            :bearing_distance, :bearing_angle,
            :date_time, :crop_name, :crop_stage, :water_source, :season,
            :indices_b64, :unsupervised_b64, :supervised_b64,
            :photo1_path, :photo2_path, :photo3_path,
            :description_rem, 0
        )
    """, record)
    sno = cur.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Survey saved locally with sno={sno}")
    return sno


def get_all_surveys() -> list:
    """Return all survey records as a list of dicts."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM GTSurvey ORDER BY sno DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def get_unsynced_surveys() -> list:
    """Return records not yet uploaded to the server."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM GTSurvey WHERE synced = 0")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def mark_synced(sno: int):
    """Mark a record as successfully synced."""
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("UPDATE GTSurvey SET synced = 1 WHERE sno = ?", (sno,))
    conn.commit()
    conn.close()


def delete_survey(sno: int):
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("DELETE FROM GTSurvey WHERE sno = ?", (sno,))
    conn.commit()
    conn.close()


def get_survey_count() -> dict:
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) as total, SUM(CASE WHEN synced=0 THEN 1 ELSE 0 END) as unsynced FROM GTSurvey")
    row = dict(cur.fetchone())
    conn.close()
    return row


# Initialise on import
init_db()
