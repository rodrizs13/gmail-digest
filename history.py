"""Histórico local. Use um banco separado por conta Gmail."""
import sqlite3
from pathlib import Path


class History:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute('PRAGMA foreign_keys = ON')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY, sender TEXT NOT NULL, subject TEXT NOT NULL,
                received_at TEXT, processed_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY, started_at TEXT NOT NULL,
                finished_at TEXT, status TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                cutoff INTEGER NOT NULL, checkpoint INTEGER, error TEXT);
        ''')

    def checkpoint(self):
        successful = self.db.execute("SELECT MAX(checkpoint) FROM runs WHERE status = 'success'").fetchone()[0]
        if successful is not None:
            return successful
        return self.db.execute("SELECT MIN(cutoff) FROM runs WHERE status = 'failed'").fetchone()[0]

    def start(self, started, cutoff):
        # One writer per database; prevents two workers producing the same digest.
        self.db.execute('BEGIN IMMEDIATE')
        return self.db.execute(
            "INSERT INTO runs(started_at,status,cutoff) VALUES (?, 'running', ?)",
            (started, cutoff)).lastrowid

    def unseen(self, messages):
        seen = {row[0] for row in self.db.execute('SELECT id FROM messages')}
        result = []
        for message in messages:
            if message['id'] not in seen:
                result.append(message)
                seen.add(message['id'])
        return result

    def finish(self, run_id, messages, finished, checkpoint, truncated):
        self.db.executemany(
            'INSERT INTO messages VALUES (?, ?, ?, ?, ?)',
            [(m['id'], m['sender'], m['subject'], m.get('received_at'), finished) for m in messages])
        self.db.execute('UPDATE runs SET finished_at=?, status=?, message_count=?, checkpoint=? WHERE id=?',
                        (finished, 'partial' if truncated else 'success', len(messages),
                         None if truncated else checkpoint, run_id))
        self.db.execute('COMMIT')

    def fail(self, run_id, finished, error):
        self.db.execute('ROLLBACK')
        # Do not persist API errors: they can contain private data or tokens.
        self.db.execute("INSERT INTO runs(started_at,finished_at,status,cutoff,error) VALUES (?,?,'failed',?,?)",
                        (run_id[0], finished, run_id[1], type(error).__name__))

    def close(self):
        self.db.close()
