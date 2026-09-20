# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Fleet Account Manager & SQLite State Machine (Thread-Safe with Atomic Checkout)
Author: Emiliamio <mio2110767128@163.com>
"""

import os
import sqlite3
import json
import logging
from contextlib import contextmanager
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("ASTA.FleetManager")


class AccountManager:
    """
    Industrial SQLite asset manager for commercial proxy-farming accounts.
    Features:
    - WAL journal mode for concurrent multi-instance access.
    - Atomic account checkout to prevent multi-instance double-dispatch race conditions.
    - Priority-based queue dispatching (SVIP > MONTHLY > DAILY).
    - Lifecycle status transitions (IDLE, QUEUED, RUNNING, SANITY_EMPTY, CAPTCHA_LOCKED).
    - Daily sanity reset scheduler for multi-day fleet automation.
    - Detailed task run auditing and drop history recording.
    """

    TIER_PRIORITY = {
        "SVIP": 3,
        "MONTHLY": 2,
        "DAILY": 1
    }

    def __init__(self, db_path: str = "data/accounts.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Creates a connection with row factory and WAL mode enabled."""
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
        return conn

    @contextmanager
    def _connection(self):
        """Context manager yielding connection, auto-committing, and strictly closing."""
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initializes schema for client accounts and task run auditing."""
        with self._connection() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS client_accounts (
                account_id TEXT PRIMARY KEY,
                client_name TEXT NOT NULL,
                platform TEXT DEFAULT 'OFFICIAL',
                service_tier TEXT NOT NULL,
                target_tasks TEXT NOT NULL,
                current_status TEXT DEFAULT 'IDLE',
                assigned_instance INTEGER DEFAULT 0,
                last_run_time DATETIME,
                daily_sanity_consumed INTEGER DEFAULT 0,
                expiry_date DATE,
                notify_webhook TEXT,
                login_account TEXT,
                login_password TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)

            conn.execute("""
            CREATE TABLE IF NOT EXISTS task_run_logs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                task_name TEXT NOT NULL,
                runs_completed INTEGER DEFAULT 0,
                drops_summary TEXT,
                sanity_spent INTEGER DEFAULT 0,
                start_time DATETIME,
                end_time DATETIME,
                status TEXT,
                FOREIGN KEY(account_id) REFERENCES client_accounts(account_id)
            );
            """)
            conn.commit()

    def add_or_update_account(
        self,
        account_id: str,
        client_name: str,
        service_tier: str = "MONTHLY",
        target_tasks: Optional[List[str]] = None,
        platform: str = "OFFICIAL",
        notify_webhook: str = "",
        expiry_date: str = "2026-12-31",
        force_status: Optional[str] = None,
        assigned_instance: int = 0,
        login_account: Optional[str] = None,
        login_password: Optional[str] = None
    ) -> Dict[str, Any]:
        """Adds or updates a client account in the fleet database."""
        tasks_json = json.dumps(target_tasks or ["1-7_farm", "daily_sanity"])
        tier = service_tier.upper()
        if tier not in self.TIER_PRIORITY:
            tier = "DAILY"

        with self._connection() as conn:
            if force_status:
                conn.execute("""
                INSERT INTO client_accounts (
                    account_id, client_name, platform, service_tier,
                    target_tasks, notify_webhook, expiry_date, current_status,
                    assigned_instance, login_account, login_password
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    client_name=excluded.client_name,
                    platform=excluded.platform,
                    service_tier=excluded.service_tier,
                    target_tasks=excluded.target_tasks,
                    notify_webhook=excluded.notify_webhook,
                    expiry_date=excluded.expiry_date,
                    current_status=excluded.current_status,
                    assigned_instance=excluded.assigned_instance,
                    login_account=excluded.login_account,
                    login_password=excluded.login_password;
                """, (account_id, client_name, platform, tier, tasks_json, notify_webhook, expiry_date, force_status, assigned_instance, login_account, login_password))
            else:
                conn.execute("""
                INSERT INTO client_accounts (
                    account_id, client_name, platform, service_tier,
                    target_tasks, notify_webhook, expiry_date,
                    assigned_instance, login_account, login_password
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    client_name=excluded.client_name,
                    platform=excluded.platform,
                    service_tier=excluded.service_tier,
                    target_tasks=excluded.target_tasks,
                    notify_webhook=excluded.notify_webhook,
                    expiry_date=excluded.expiry_date,
                    assigned_instance=excluded.assigned_instance,
                    login_account=excluded.login_account,
                    login_password=excluded.login_password;
                """, (account_id, client_name, platform, tier, tasks_json, notify_webhook, expiry_date, assigned_instance, login_account, login_password))
            conn.commit()

        return self.get_account(account_id)

    def reset_daily_status(self) -> int:
        """
        Resets accounts with status 'SANITY_EMPTY' or 'COMPLETED' back to 'IDLE' and zeroes daily sanity
        for the new scheduled day.
        """
        with self._connection() as conn:
            cur = conn.execute("""
            UPDATE client_accounts
            SET current_status = 'IDLE', daily_sanity_consumed = 0
            WHERE current_status IN ('SANITY_EMPTY', 'COMPLETED', 'RUNNING');
            """)
            conn.commit()
            return cur.rowcount

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single client account by ID."""
        with self._connection() as conn:
            cur = conn.execute("SELECT * FROM client_accounts WHERE account_id = ?", (account_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["target_tasks"] = json.loads(res["target_tasks"])
            return res

    def list_accounts(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists accounts, optionally filtered by current_status."""
        with self._connection() as conn:
            if status:
                cur = conn.execute("SELECT * FROM client_accounts WHERE current_status = ? ORDER BY created_at ASC", (status,))
            else:
                cur = conn.execute("SELECT * FROM client_accounts ORDER BY created_at ASC")
            rows = cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["target_tasks"] = json.loads(item["target_tasks"])
                results.append(item)
            return results

    def update_status(self, account_id: str, new_status: str, instance_idx: Optional[int] = None) -> None:
        """Transitions account lifecycle status."""
        valid_statuses = [
            "IDLE", "QUEUED", "RUNNING", "COMPLETED",
            "SANITY_EMPTY", "CAPTCHA_LOCKED", "ERROR"
        ]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status '{new_status}', must be one of {valid_statuses}")

        with self._connection() as conn:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if instance_idx is not None:
                conn.execute("""
                UPDATE client_accounts
                SET current_status = ?, assigned_instance = ?, last_run_time = ?
                WHERE account_id = ?;
                """, (new_status, instance_idx, now, account_id))
            else:
                conn.execute("""
                UPDATE client_accounts
                SET current_status = ?, last_run_time = ?
                WHERE account_id = ?;
                """, (new_status, now, account_id))
            conn.commit()

    def get_next_dispatchable_account(self, mark_as_running: bool = False) -> Optional[Dict[str, Any]]:
        """
        Picks the highest priority dispatchable account atomically.
        Filters accounts with status 'IDLE'.
        If mark_as_running=True, transitions status to 'RUNNING' inside the same transaction
        to guarantee race-condition immunity across concurrent worker threads.
        """
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            cur = conn.execute("""
            SELECT * FROM client_accounts
            WHERE current_status = 'IDLE'
            """)
            rows = cur.fetchall()
            if not rows:
                conn.commit()
                return None

            accounts = []
            for r in rows:
                item = dict(r)
                item["target_tasks"] = json.loads(item["target_tasks"])
                tier_weight = self.TIER_PRIORITY.get(item["service_tier"], 1)
                last_run = item["last_run_time"] or "1970-01-01 00:00:00"
                accounts.append((tier_weight, last_run, item))

            accounts.sort(key=lambda x: (-x[0], x[1]))
            selected = accounts[0][2]

            if mark_as_running:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn.execute("""
                UPDATE client_accounts
                SET current_status = 'RUNNING', last_run_time = ?
                WHERE account_id = ?;
                """, (now, selected["account_id"]))
                selected["current_status"] = "RUNNING"
                selected["last_run_time"] = now

            conn.commit()
            return selected

    def record_task_run(
        self,
        account_id: str,
        task_name: str,
        runs_completed: int,
        drops: Dict[str, int],
        sanity_spent: int,
        start_time: str,
        end_time: str,
        status: str = "SUCCESS"
    ) -> int:
        """Records a completed run in task_run_logs and updates daily sanity counter."""
        drops_json = json.dumps(drops, ensure_ascii=False)
        with self._connection() as conn:
            cur = conn.execute("""
            INSERT INTO task_run_logs (
                account_id, task_name, runs_completed, drops_summary,
                sanity_spent, start_time, end_time, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (account_id, task_name, runs_completed, drops_json, sanity_spent, start_time, end_time, status))
            run_id = cur.lastrowid

            conn.execute("""
            UPDATE client_accounts
            SET daily_sanity_consumed = daily_sanity_consumed + ?
            WHERE account_id = ?;
            """, (sanity_spent, account_id))
            conn.commit()
            return run_id

    def get_run_logs(self, account_id: str) -> List[Dict[str, Any]]:
        """Retrieves audit run history for an account."""
        with self._connection() as conn:
            cur = conn.execute("""
            SELECT * FROM task_run_logs
            WHERE account_id = ?
            ORDER BY start_time DESC;
            """, (account_id,))
            rows = cur.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["drops_summary"] = json.loads(item["drops_summary"])
                results.append(item)
            return results
    def delete_account(self, account_id: str) -> bool:
        """Deletes account and its logs from the database."""
        with self._connection() as conn:
            conn.execute("DELETE FROM task_run_logs WHERE account_id = ?;", (account_id,))
            cur = conn.execute("DELETE FROM client_accounts WHERE account_id = ?;", (account_id,))
            logger.info(f"Deleted account {account_id}")
            return cur.rowcount > 0
