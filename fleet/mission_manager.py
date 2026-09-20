# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Master Mission Orchestrator & Persistent Task Store (SQLite WAL)
Author: Emiliamio <mio2110767128@163.com>
"""

import os
import sqlite3
import json
import time
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("ASTA.MissionManager")


class MissionType:
    CAMPAIGN_CLEAR = "CAMPAIGN_CLEAR"      # 章节连续推图通关
    SANITY_FARM = "SANITY_FARM"            # 指定关卡定额刷体力
    INFRA_ROTATE = "INFRA_ROTATE"          # 基建收获与干员轮换
    DAILY_ROUTINE = "DAILY_ROUTINE"        # 签到/公招/任务奖励领取
    ROGUELIKE = "ROGUELIKE"                # 集成战略/肉鸽全自主推演


class MissionStatus:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MissionManager:
    """
    Manages mission life cycle, persistent task queue, and state transitions.
    Thread-safe and backed by SQLite in WAL mode.
    """

    def __init__(self, db_path: str = "data/missions.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
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

    def _init_db(self):
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    mission_type TEXT NOT NULL,
                    target_chapter INTEGER,
                    target_stage TEXT,
                    params TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    result_summary TEXT
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_missions_status ON missions(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_missions_account ON missions(account_id);")
            # Auto-recover orphaned running tasks from previous session
            conn.execute("""
                UPDATE missions
                SET status = 'QUEUED', progress_info = '服务重启，自动重置为待办'
                WHERE status = 'RUNNING';
            """)

    def create_mission(
        self,
        account_id: str,
        mission_type: str,
        target_chapter: Optional[int] = None,
        target_stage: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        mission_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create and enqueue a new mission task."""
        if not mission_id:
            import uuid
            mission_id = f"TASK_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}_{mission_type[:4]}"

        params_json = json.dumps(params or {}, ensure_ascii=False)
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO missions (
                    mission_id, account_id, mission_type, target_chapter,
                    target_stage, params, status, progress_info
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                mission_id, account_id, mission_type, target_chapter,
                target_stage, params_json, MissionStatus.QUEUED, "任务已录入排班队列"
            ))
        logger.info(f"Created mission {mission_id} [{mission_type}] for account {account_id}")
        return self.get_mission(mission_id)

    def get_mission(self, mission_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM missions WHERE mission_id = ?", (mission_id,))
            row = cursor.fetchone()
            if not row:
                return None
            data = dict(row)
            data["params"] = json.loads(data["params"]) if data["params"] else {}
            return data

    def list_missions(
        self,
        status: Optional[str] = None,
        account_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List missions with optional filtering."""
        query = "SELECT * FROM missions WHERE 1=1"
        params = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                item["params"] = json.loads(item["params"]) if item["params"] else {}
                results.append(item)
            return results

    def checkout_next_queued_mission(self) -> Optional[Dict[str, Any]]:
        """Atomically checkout the oldest QUEUED mission."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            cursor.execute("""
                SELECT mission_id FROM missions
                WHERE status = ?
                ORDER BY created_at ASC
                LIMIT 1;
            """, (MissionStatus.QUEUED,))
            row = cursor.fetchone()
            if not row:
                conn.commit()
                return None

            mission_id = row["mission_id"]
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE missions
                SET status = ?, started_at = ?, progress_info = ?
                WHERE mission_id = ?;
            """, (MissionStatus.RUNNING, now, "任务已派发，开始执行", mission_id))
            conn.commit()

        return self.get_mission(mission_id)

    def update_progress(self, mission_id: str, progress_info: str):
        with self._connection() as conn:
            conn.execute("""
                UPDATE missions SET progress_info = ? WHERE mission_id = ?;
            """, (progress_info, mission_id))

    def complete_mission(self, mission_id: str, summary: str):
        now = datetime.now().isoformat()
        with self._connection() as conn:
            conn.execute("""
                UPDATE missions
                SET status = ?, completed_at = ?, result_summary = ?, progress_info = ?
                WHERE mission_id = ?;
            """, (MissionStatus.COMPLETED, now, summary, "任务圆满完成", mission_id))
        logger.info(f"Mission {mission_id} marked COMPLETED: {summary}")

    def fail_mission(self, mission_id: str, error_msg: str):
        now = datetime.now().isoformat()
        with self._connection() as conn:
            conn.execute("""
                UPDATE missions
                SET status = ?, completed_at = ?, result_summary = ?, progress_info = ?
                WHERE mission_id = ?;
            """, (MissionStatus.FAILED, now, f"失败: {error_msg}", f"执行异常中断: {error_msg}", mission_id))
        logger.error(f"Mission {mission_id} FAILED: {error_msg}")

    def cancel_mission(self, mission_id: str):
        with self._connection() as conn:
            conn.execute("""
                UPDATE missions SET status = ?, progress_info = ? WHERE mission_id = ?;
            """, (MissionStatus.CANCELLED, "人工撤回取消", mission_id))

    def delete_mission(self, mission_id: str) -> bool:
        """Permanently delete a mission record."""
        with self._connection() as conn:
            cur = conn.execute("DELETE FROM missions WHERE mission_id = ?;", (mission_id,))
            logger.info(f"Deleted mission {mission_id}")
            return cur.rowcount > 0

    def clear_missions(self, status: Optional[str] = None) -> int:
        """Clear missions by status or all."""
        with self._connection() as conn:
            if status:
                cur = conn.execute("DELETE FROM missions WHERE status = ?;", (status,))
            else:
                cur = conn.execute("DELETE FROM missions;")
            logger.info(f"Cleared {cur.rowcount} missions (filter: {status})")
            return cur.rowcount

    def checkout_specific_mission(self, mission_id: str) -> Optional[Dict[str, Any]]:
        """Atomically checkout a specific mission by ID."""
        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE;")
            cursor.execute("SELECT status FROM missions WHERE mission_id = ?;", (mission_id,))
            row = cursor.fetchone()
            if not row:
                conn.commit()
                return None
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE missions
                SET status = ?, started_at = ?, progress_info = ?
                WHERE mission_id = ?;
            """, (MissionStatus.RUNNING, now, "指定任务已激活，开始执行", mission_id))
            conn.commit()
        return self.get_mission(mission_id)

    def abort_all_running_missions(self, reason: str = "用户触发全局紧急停止") -> int:
        """Immediately marks all currently RUNNING missions as CANCELLED."""
        now = datetime.now().isoformat()
        with self._connection() as conn:
            cur = conn.execute("""
                UPDATE missions
                SET status = ?, completed_at = ?, result_summary = ?, progress_info = ?
                WHERE status = ?;
            """, (MissionStatus.CANCELLED, now, f"中止: {reason}", f"已被紧急停机: {reason}", MissionStatus.RUNNING))
            logger.warning(f"Aborted {cur.rowcount} running missions: {reason}")
            return cur.rowcount
