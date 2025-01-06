import ctypes
import datetime
import sqlite3
from typing import Tuple
import csv

from rich.console import Console
from rich.table import Table

import flomo.errors as errors
import flomo.helpers as helpers

# TODO: Setup Dev & Prod Database Environments!


class Tracker:
    def __init__(self, initializing: bool = False):
        path = helpers.get_path("sessions.db", in_data=True)

        self.conn = sqlite3.connect(path)
        self.cursor = self.conn.cursor()

        if not initializing and not self._db_file_exists():
            raise errors.DBFileNotFoundError()

    def _db_file_exists(self):
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        return bool(self.cursor.fetchall())

    def create_table(self):
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS sessions (id FLOAT PRIMARY KEY, date_time TEXT, tag TEXT, name TEXT, total_time TEXT)"
        )
        self.conn.commit()

    def create_session(self, tag: str, name: str, start_time: datetime.datetime) -> str:
        lib = ctypes.CDLL(helpers.get_path("", lib=True))

        lib.encode_timestamp.argtypes = [ctypes.c_ulonglong]
        lib.encode_timestamp.restype = ctypes.c_char_p
        lib.decode_timestamp.argtypes = [ctypes.c_char_p]
        lib.decode_timestamp.restype = ctypes.c_ulonglong

        _session_id: bytes = lib.encode_timestamp(
            ctypes.c_ulonglong(int(start_time.timestamp()))
        )
        session_id = _session_id.decode("utf-8")
        self.cursor.execute(
            "INSERT INTO sessions (id, date_time, tag, name) VALUES (?, ?, ?, ?)",
            (session_id, start_time.strftime("%Y-%m-%d %H:%M:%S"), tag, name),
        )
        self.conn.commit()
        return session_id

    def end_session(self, session_id: str, end_time: datetime.datetime):
        date_time = self.get_session(session_id)[1]
        total_time = end_time - datetime.datetime.strptime(
            date_time, "%Y-%m-%d %H:%M:%S"
        )
        self.cursor.execute(
            "UPDATE sessions SET total_time = ? WHERE id = ?",
            (
                helpers.format_time(round(total_time.total_seconds())),
                session_id,
            ),
        )
        self.conn.commit()

    def get_sessions(self):
        self.cursor.execute("SELECT * FROM sessions")
        return self.cursor.fetchall()

    def get_session(self, session_id: str):
        self.cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        return self.cursor.fetchone()

    def delete_session(self, session_ids: Tuple[str] | Tuple):
        if len(session_ids) == 0:
            self.cursor.execute(
                "DELETE FROM sessions WHERE date_time = (SELECT MAX(date_time) FROM sessions)"
            )
            self.conn.commit()

        for session_id in session_ids:
            if not self.get_session(session_id):
                raise errors.NoSessionError(session_id)

        self.cursor.execute(
            "DELETE FROM sessions WHERE id IN ({seq})".format(
                seq=",".join(["?"] * len(session_ids))
            ),
            session_ids,
        )
        self.conn.commit()

    def update_session(self, session_id: str, tag: str | None, name: str | None):
        if not self.get_session(session_id):
            raise errors.NoSessionError(session_id)

        if tag:
            self.cursor.execute(
                "UPDATE sessions SET tag = ? WHERE id = ?", (tag.lower(), session_id)
            )
            print(f'Tag updated to "{tag.lower()}" for session {session_id}')
        if name:
            self.cursor.execute(
                "UPDATE sessions SET name = ? WHERE id = ?", (name, session_id)
            )
            print(f'Name updated to "{name}" for session {session_id}')
        self.conn.commit()
    
    def export(self, file_path: str):
        """
        Exports all sessions in the database to a CSV file.
        Args:
            file_path (str): The path to save the CSV file.
        """
        # Fetch all sessions from the database
        sessions = self.get_sessions()

        # Define the column headers
        headers = ["id", "date_time", "tag", "name", "total_time"]

        # Write to CSV
        with open(file_path, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(headers)  # Write headers
            writer.writerows(sessions)  # Write session rows

def end_session(session_id: str):
    db = Tracker()
    db.end_session(session_id, datetime.datetime.now())
    db.conn.close()


def show_sessions():
    db = Tracker()
    sessions = db.get_sessions()
    table = Table(title="You like this?")

    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Session Date & Time", style="magenta")
    table.add_column("Tag", style="green")
    table.add_column("Name", style="yellow")
    table.add_column("Duration", style="red", justify="right")
    for session in sessions:
        _id, datetime, tag, name, duration = session
        color = helpers.tag_color(tag)
        table.add_row(
            str(_id), str(datetime), f"[{color}]{tag}[/{color}]", name, str(duration)
        )

    console = Console()
    console.print(table)

    db.conn.close()



