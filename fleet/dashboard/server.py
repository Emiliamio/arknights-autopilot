# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
PRTS Local Web Tactical Command Dashboard Server (HTTP + SSE + REST)
Author: Emiliamio <mio2110767128@163.com>
"""

from fleet.fleet_orchestrator import FleetOrchestrator

import os
import sys
import json
import time
import math
import random
import logging
import threading
from urllib.parse import urlparse, parse_qs
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Any, Optional, List

from fleet.account_manager import AccountManager
from fleet.mission_manager import MissionManager, MissionStatus
from fleet.multi_instance_runner import MultiInstanceRunner

logger = logging.getLogger("ASTA.DashboardServer")


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP Server for handling concurrent SSE and REST requests."""
    daemon_threads = True
    allow_reuse_address = True


class TelemetryStore:
    """Thread-safe state store for real-time tactical battlefield telemetry."""

    def __init__(self):
        self._lock = threading.Lock()
        self.last_updated = time.time()

        # Battlefield Telemetry
        self.dp = 0
        self.max_dp = 99
        self.dp_history: List[int] = []
        self.kill_count = [0, 0]
        self.battle_state = "IDLE"  # PRE_BATTLE, IN_BATTLE, VICTORY, DEFEAT, IDLE
        self.speed_2x = True
        self.threat_level = "SAFE"  # SAFE, MONITORING, ALERT, PANIC_LEAK
        self.leak_info: Optional[Dict[str, Any]] = None

        # Tactical Map & Operators
        self.stage_id = "1-7"
        self.stage_title = "固源岩圣地 · 空间战术推演"
        self.active_blockers: List[List[int]] = [[3, 4]]
        self.primary_choke = [3, 4]
        self.deployed_operators: List[Dict[str, Any]] = [
            {"id": "op_01", "name": "德克萨斯", "role": "VANGUARD", "tile": [3, 4], "orientation": "RIGHT", "hp_percent": 92, "sp_ready": True},
            {"id": "op_02", "name": "克洛丝", "role": "SNIPER", "tile": [3, 3], "orientation": "DOWN", "hp_percent": 100, "sp_ready": False},
            {"id": "op_03", "name": "安塞尔", "role": "MEDIC", "tile": [2, 4], "orientation": "RIGHT", "hp_percent": 100, "sp_ready": False}
        ]

        # Copilot Plan & Execution Status
        self.copilot_name = "1-7_xiaoran_duo"
        self.current_step_idx = 2
        self.copilot_steps: List[Dict[str, Any]] = [
            {"step": 1, "name": "德克萨斯", "action": "DEPLOY", "tile": [3, 4], "orientation": "RIGHT", "cost": 10, "status": "DEPLOYED"},
            {"step": 2, "name": "克洛丝", "action": "DEPLOY", "tile": [3, 3], "orientation": "DOWN", "cost": 9, "status": "DEPLOYED"},
            {"step": 3, "name": "安塞尔", "action": "DEPLOY", "tile": [2, 4], "orientation": "RIGHT", "cost": 14, "status": "CURRENT"},
            {"step": 4, "name": "德克萨斯", "action": "SKILL", "tile": [3, 4], "orientation": "NONE", "cost": 0, "status": "PENDING"}
        ]

        # Emergency Reserve Operators (Panic Daemon)
        self.emergency_reserves: List[Dict[str, Any]] = [
            {"name": "红", "role": "SPECIALIST", "cost": 7, "ready": True, "cooldown_sec": 0},
            {"name": "傀影", "role": "SPECIALIST", "cost": 9, "ready": True, "cooldown_sec": 0},
            {"name": "砾", "role": "SPECIALIST", "cost": 5, "ready": False, "cooldown_sec": 8}
        ]

        # Anti-Cheat & Physical Telemetry
        self.touch_scatter: List[List[float]] = [
            [0.5, -0.8], [-1.2, 1.4], [0.3, 0.9], [-0.7, -1.1], [1.5, -0.3],
            [-0.2, 0.4], [1.1, 1.0], [-1.4, -0.6], [0.8, -1.3], [-0.5, 0.7]
        ]
        self.bezier_motion_ms = 338
        self.adb_latency_ms = 170
        self.anti_cheat_score = 99.8

        # Real-time Event Logs
        self.logs: List[Dict[str, Any]] = [
            {"time": time.strftime("%H:%M:%S"), "level": "INFO", "msg": "ASTA PRTS 战术中枢已就绪，等待下发作战工单"}
        ]

    def update_from_combat(self, **kwargs):
        """Update telemetry from live combat engine."""
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self, k):
                    setattr(self, k, v)
            self.last_updated = time.time()

    def add_log(self, level: str, msg: str):
        """Append an event log entry."""
        with self._lock:
            entry = {"time": time.strftime("%H:%M:%S"), "level": level, "msg": msg}
            self.logs.append(entry)
            if len(self.logs) > 50:
                self.logs.pop(0)

    def get_snapshot(self) -> Dict[str, Any]:
        """Return full JSON-serializable telemetry state."""
        with self._lock:
            now = time.time()

            return {
                "timestamp": now,
                "stage": {
                    "id": self.stage_id,
                    "title": self.stage_title,
                    "primary_choke": self.primary_choke,
                    "active_blockers": self.active_blockers
                },
                "telemetry": {
                    "dp": self.dp,
                    "max_dp": self.max_dp,
                    "dp_history": self.dp_history,
                    "kill_count": self.kill_count,
                    "battle_state": self.battle_state,
                    "speed_2x": self.speed_2x,
                    "threat_level": self.threat_level,
                    "leak_info": self.leak_info
                },
                "operators": self.deployed_operators,
                "copilot": {
                    "name": self.copilot_name,
                    "current_step": self.current_step_idx,
                    "total_steps": len(self.copilot_steps),
                    "steps": self.copilot_steps,
                    "emergency_reserves": self.emergency_reserves
                },
                "anti_cheat": {
                    "touch_scatter": self.touch_scatter,
                    "bezier_motion_ms": self.bezier_motion_ms,
                    "adb_latency_ms": self.adb_latency_ms,
                    "anti_cheat_score": self.anti_cheat_score
                },
                "logs": self.logs
            }


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP Request Handler for REST API, SSE streaming, and PRTS UI assets."""

    server_version = "ASTA-PRTS/1.0"

    def __init__(self, *args, **kwargs):
        self.static_dir = os.path.join(os.path.dirname(__file__), "static")
        super().__init__(*args, directory=self.static_dir, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            return self._serve_index()
        elif path == "/api/status":
            return self._handle_api_status()
        elif path == "/api/telemetry":
            return self._handle_api_telemetry()
        elif path == "/api/accounts":
            return self._handle_api_accounts()
        elif path == "/api/fleet":
            return self._handle_api_fleet()
        elif path == "/api/missions":
            return self._handle_api_missions()
        elif path == "/api/roster":
            return self._handle_api_roster()
        elif path == "/api/stream":
            return self._handle_sse_stream()
        else:
            # Fallback to serving static files
            return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/override":
            return self._handle_api_override()
        elif path == "/api/missions":
            return self._handle_api_create_mission()
        elif path == "/api/missions/run":
            return self._handle_api_run_missions()
        elif path == "/api/missions/run_single":
            return self._handle_api_run_single_mission()
        elif path == "/api/missions/delete":
            return self._handle_api_delete_mission()
        elif path == "/api/missions/clear":
            return self._handle_api_clear_missions()
        elif path == "/api/squad/synthesize":
            return self._handle_api_synthesize_squad()
        elif path == "/api/accounts/create":
            return self._handle_api_create_account()
        elif path == "/api/accounts/delete":
            return self._handle_api_delete_account()
        elif path in ("/api/stop", "/api/missions/stop"):
            return self._handle_api_stop()
        else:
            self.send_error(404, "Endpoint not found")

    def _serve_index(self):
        index_file = os.path.join(self.static_dir, "index.html")
        if not os.path.isfile(index_file):
            self.send_error(404, "index.html not found")
            return
        with open(index_file, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _handle_api_status(self):
        port = self.server.server_address[1]
        self._send_json({
            "system": "ASTA - Arknights Sovereign Tactical Autopilot",
            "dashboard": "PRTS Tactical Command Center",
            "author": "Emiliamio <mio2110767128@163.com>",
            "host": "AKIYAMA-MIO",
            "port": port,
            "status": "ONLINE",
            "timestamp": time.time()
        })

    def _handle_api_telemetry(self):
        store: TelemetryStore = getattr(self.server, "telemetry_store", None)
        if store:
            self._send_json(store.get_snapshot())
        else:
            self._send_json({"error": "Telemetry store uninitialized"}, 500)

    def _handle_api_roster(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        account_id = qs.get("account_id", ["EMILIAMIO_MAIN"])[0]
        try:
            from tactical.roster_inspector import RosterInspector
            inspector = RosterInspector()
            roster = inspector.load_roster(account_id)
            self._send_json({"account_id": account_id, "operators": roster, "total": len(roster)})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_api_synthesize_squad(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req = json.loads(post_body)
            account_id = req.get("account_id", "EMILIAMIO_MAIN")
            stage_id = req.get("stage_id", "1-7")
            from tactical.squad_synthesizer import SquadSynthesizer
            synthesizer = SquadSynthesizer()
            res = synthesizer.synthesize_squad(account_id, stage_id)
            store = getattr(self.server, "telemetry_store", None)
            if store:
                store.add_log("INFO", f"🧠 [阵容自构] 为 {account_id} 在关卡 {stage_id} 自适应合成 12 人黄金战队")
            self._send_json(res)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_api_accounts(self):
        try:
            mgr = AccountManager()
            accounts = mgr.list_accounts()
            self._send_json({"accounts": accounts, "total": len(accounts)})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_api_missions(self):
        try:
            mgr = MissionManager()
            missions = mgr.list_missions()
            self._send_json({"missions": missions, "total": len(missions)})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _dispatch_mission_in_background(self, mission_id: str):
        store = getattr(self.server, "telemetry_store", None)
        orchestrator = FleetOrchestrator(telemetry_store=store)
        dispatched = orchestrator.dispatch_pending_missions(force_reset_abort=True)
        logger.info(f"[+] FleetOrchestrator parallel dispatch result: {dispatched} missions dispatched.")

    def _handle_api_delete_mission(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req = json.loads(post_body)
            mission_id = req.get("mission_id")
            mgr = MissionManager()
            success = mgr.delete_mission(mission_id)
            store = getattr(self.server, "telemetry_store", None)
            if store:
                store.add_log("INFO", f"🗑️ [工单管理] 已删除任务工单: {mission_id}")
            self._send_json({"status": "SUCCESS", "deleted": success})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_api_run_single_mission(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req = json.loads(post_body)
            mission_id = req.get("mission_id")
            store = getattr(self.server, "telemetry_store", None)
            if store:
                store.add_log("INFO", f"▶️ [工单管理] 单选立即启动任务: {mission_id}")
            orchestrator = FleetOrchestrator(telemetry_store=store)
            success = orchestrator.dispatch_specific_mission(mission_id)
            self._send_json({"status": "SUCCESS", "mission_id": mission_id, "dispatched": success})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_api_stop(self):
        store = getattr(self.server, "telemetry_store", None)
        orchestrator = FleetOrchestrator(telemetry_store=store)
        orchestrator.stop_all("指挥官通过控制大屏触发全局紧急停机")
        mgr = MissionManager()
        count = mgr.abort_all_running_missions("指挥官通过控制大屏触发全局紧急停机")
        store = getattr(self.server, "telemetry_store", None)
        if store:
            store.threat_level = "SAFE"
            store.add_log("ALERT", f"🛑 [全局紧急停机] 所有正在执行的作战与推图任务已立即截停！(已中止 {count} 个运行中工单)")
        self._send_json({"status": "ABORTED", "stopped_count": count})

    def _handle_api_clear_missions(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req = json.loads(post_body)
            status_filter = req.get("status", "QUEUED")
            mgr = MissionManager()
            if status_filter == "ALL":
                count = mgr.clear_missions()
            elif status_filter == "FINISHED":
                with mgr._get_connection() as conn:
                    cur = conn.execute("DELETE FROM missions WHERE status IN ('COMPLETED', 'FAILED', 'CANCELLED');")
                    count = cur.rowcount
            else:
                count = mgr.clear_missions(status=status_filter)

            store = getattr(self.server, "telemetry_store", None)
            if store:
                store.add_log("INFO", f"🧹 [工单管理] 已批量清理 {count} 条工单 (类型: {status_filter})")
            self._send_json({"status": "SUCCESS", "count": count})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_api_run_missions(self):
        mgr = MissionManager()
        queued = mgr.list_missions(status="QUEUED")
        if not queued:
            self._send_json({"status": "EMPTY", "message": "No queued missions"})
            return

        store = getattr(self.server, "telemetry_store", None)
        if store:
            store.add_log("INFO", f"▶️ [多开并发] 指挥官手动触发多开并行执行待办队列 ({len(queued)} 项)...")

        orchestrator = FleetOrchestrator(telemetry_store=store)
        dispatched = orchestrator.dispatch_pending_missions(force_reset_abort=True)
        self._send_json({"status": "SUCCESS", "dispatched_count": dispatched, "remaining": len(queued) - dispatched})

    def _handle_api_create_account(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req = json.loads(post_body)
            mgr = AccountManager()
            acc = mgr.add_or_update_account(
                account_id=req.get("account_id"),
                client_name=req.get("client_name"),
                service_tier=req.get("service_tier", "MONTHLY"),
                platform=req.get("platform", "BILIBILI"),
                assigned_instance=int(req.get("assigned_instance", 0)),
                login_account=req.get("login_account"),
                login_password=req.get("login_password")
            )
            store = getattr(self.server, "telemetry_store", None)
            if store:
                store.add_log("INFO", f"👤 [账户管理] 新录入客户账户档案: {acc['account_id']} ({acc['client_name']}, {acc['platform']}服)")
            self._send_json({"status": "SUCCESS", "account": acc})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_api_delete_account(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req = json.loads(post_body)
            acc_id = req.get("account_id")
            mgr = AccountManager()
            success = mgr.delete_account(acc_id)
            store = getattr(self.server, "telemetry_store", None)
            if store:
                store.add_log("INFO", f"🗑️ [账户管理] 已注销客户账户档案: {acc_id}")
            self._send_json({"status": "SUCCESS", "deleted": success})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_api_create_mission(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req = json.loads(post_body)
            mgr = MissionManager()
            m = mgr.create_mission(
                account_id=req.get("account_id", "EMILIAMIO_MAIN"),
                mission_type=req.get("mission_type", "CAMPAIGN_CLEAR"),
                target_chapter=req.get("target_chapter"),
                target_stage=req.get("target_stage"),
                params=req.get("params", {})
            )
            store = getattr(self.server, "telemetry_store", None)
            if store:
                store.add_log("INFO", f"📋 [总控工单] 新工单已录入待办队列: {m['mission_id']} [{m['mission_type']}] (状态: QUEUED，等待点击执行)")
            self._send_json({"status": "SUCCESS", "mission": m})
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_api_fleet(self):
        try:
            store = getattr(self.server, "telemetry_store", None)
            orchestrator = FleetOrchestrator(telemetry_store=store)
            data = orchestrator.get_fleet_telemetry()
            data["instances"] = {str(s["instance_index"]): s for s in data.get("slots", [])}
            self._send_json(data)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def _handle_sse_stream(self):
        """Server-Sent Events real-time event pipeline."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        store: TelemetryStore = getattr(self.server, "telemetry_store", None)
        if not store:
            return

        try:
            while getattr(self.server, "_keep_running", True):
                snapshot = store.get_snapshot()
                payload = f"event: telemetry\ndata: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
                self.wfile.write(payload.encode("utf-8"))
                self.wfile.flush()
                time.sleep(0.3)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Client closed tab or refreshed page
            pass

    def _handle_api_override(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        try:
            req = json.loads(post_body)
        except Exception:
            req = {}

        action = req.get("action", "UNKNOWN")
        store: TelemetryStore = getattr(self.server, "telemetry_store", None)

        if store:
            if action == "PANIC_INTERCEPT":
                store.threat_level = "PANIC_LEAK"
                store.add_log("WARN", "🚨 [指挥官指令] 人工下发强制应急空投截停！PanicDaemon 启动！")
            elif action == "FORCE_SKILL":
                store.add_log("INFO", "⚡ [指挥官指令] 人工下发全局干员决战技爆发释放！")
            elif action == "RETREAT":
                store.add_log("INFO", "🔄 [指挥官指令] 人工下发低血量与完成回费干员战术撤退！")
            elif action == "TOGGLE_2X":
                store.speed_2x = not store.speed_2x
                state_str = "已开启" if store.speed_2x else "已关闭"
                store.add_log("INFO", f"⏩ [指挥官指令] 战斗速度切换: 2x 模式 {state_str}")
            elif action == "CLEAR_PANIC":
                store.threat_level = "SAFE"
                store.add_log("INFO", "🟢 [指挥官指令] 威胁状态已人工复位为 SAFE 正常。")
            else:
                store.add_log("INFO", f"⚡ [指挥官指令] 接收到未知战术指令: {action}")

            self._send_json({"status": "SUCCESS", "action": action, "timestamp": time.time()})
        else:
            self._send_json({"status": "FAILED", "error": "No store"}, 500)

    def log_message(self, format, *args):
        """Mute repetitive access logs to keep console output clean."""
        if "GET /api/stream" in args[0] or "GET /api/telemetry" in args[0]:
            return
        logger.debug("%s - - [%s] %s" % (self.address_string(), self.log_date_time_string(), format % args))


class DashboardServer:
    """Manager lifecycle for the PRTS Tactical Web Dashboard."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8848):
        self.host = host
        self.port = port
        self.telemetry_store = TelemetryStore()
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._keep_running = False

    def start(self, block: bool = False):
        """Start the dashboard server."""
        self._keep_running = True
        self._server = ThreadingHTTPServer((self.host, self.port), DashboardHandler)
        self._server.telemetry_store = self.telemetry_store  # Attach store
        self._server._keep_running = True
        logger.info(f"PRTS Dashboard Server listening on http://{self.host}:{self.port}")

        if block:
            try:
                self._server.serve_forever()
            except KeyboardInterrupt:
                self.stop()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop the dashboard server gracefully."""
        self._keep_running = False
        if self._server:
            self._server._keep_running = False
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("PRTS Dashboard Server stopped.")

    @property
    def is_running(self) -> bool:
        return self._server is not None and self._keep_running


def run_dashboard(host: str = "127.0.0.1", port: int = 8848):
    """Entry point helper to launch dashboard interactively."""
    server = DashboardServer(host=host, port=port)
    print(f"[+] ASTA PRTS Tactical Dashboard launching at: http://{host}:{port}")
    print("[*] Press Ctrl+C to terminate.")
    server.start(block=True)
