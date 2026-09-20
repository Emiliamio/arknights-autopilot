# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Multi-Instance Concurrent Fleet Orchestrator (Parallel VM ThreadPool)
Author: Emiliamio <mio2110767128@163.com>
"""

import time
import logging
import threading
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from fleet.mission_manager import MissionManager, MissionStatus
from fleet.account_manager import AccountManager
from fleet.multi_instance_runner import MultiInstanceRunner
from fleet.task_executor import TaskExecutor
from core.abort_controller import AbortController

logger = logging.getLogger("ASTA.FleetOrchestrator")


class FleetOrchestrator:
    """
    Manages concurrent multi-account execution across multiple MuMu 12 VM instances.
    Features:
    - Parallel thread pool dispatching for independent VMs (127.0.0.1:16384, 16416, 16448...).
    - Dynamic multi-slot topology with dedicated port binding (16384 + 32 * idx).
    - Account rotation & session detection on shared VM slots.
    - Sanity depletion auto-yield to sleep queue.
    - Real-time multi-VM telemetry aggregation for the PRTS Web Dashboard.
    - Global emergency stop coordination across all active worker threads.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(FleetOrchestrator, cls).__new__(cls)
            return cls._instance

    def __init__(
        self,
        mission_manager: Optional[MissionManager] = None,
        account_manager: Optional[AccountManager] = None,
        telemetry_store: Optional[Any] = None,
        max_workers: int = 4
    ):
        if hasattr(self, "_initialized") and self._initialized:
            return

        self.mission_mgr = mission_manager or MissionManager()
        self.account_mgr = account_manager or AccountManager()
        self.telemetry_store = telemetry_store
        self.max_workers = max_workers
        self.runner_helper = MultiInstanceRunner(account_manager=self.account_mgr)

        self._slots: Dict[int, Dict[str, Any]] = {}
        self._threads: Dict[int, threading.Thread] = {}
        self._state_lock = threading.Lock()
        self._refresh_vm_slots()
        self._initialized = True
        logger.info(f"[+] FleetOrchestrator initialized with {len(self._slots)} VM slots.")

    def _refresh_vm_slots(self):
        """Scans hardware pool and initializes VM slots with multi-worker support."""
        with self._state_lock:
            mumu_vms = {}
            try:
                mumu_vms = self.runner_helper.list_all_mumu_instances()
            except Exception as e:
                logger.warning(f"[!] Unable to query MuMuManager instances: {e}")

            # Populate slots: use detected VMs and guarantee slots up to max_workers
            total_slots_needed = max(len(mumu_vms), self.max_workers)
            for idx in range(total_slots_needed):
                info = mumu_vms.get(str(idx), {})
                if idx not in self._slots:
                    self._slots[idx] = {
                        "instance_index": idx,
                        "name": info.get("name", f"VM-{idx}"),
                        "port": 16384 + 32 * idx,
                        "status": "IDLE",  # IDLE, RUNNING, BOOTING, ERROR
                        "current_account": None,
                        "last_used_account": None,
                        "current_mission_id": None,
                        "current_mission_type": None,
                        "progress": "待命就绪"
                    }

    def get_fleet_telemetry(self) -> Dict[str, Any]:
        """Returns comprehensive multi-instance status for Web Dashboard."""
        self._refresh_vm_slots()
        with self._state_lock:
            slots_list = []
            for idx in sorted(self._slots.keys()):
                s = dict(self._slots[idx])
                slots_list.append(s)

            return {
                "max_concurrency": self.max_workers,
                "active_count": sum(1 for s in slots_list if s["status"] == "RUNNING"),
                "total_slots": len(slots_list),
                "slots": slots_list
            }

    def dispatch_pending_missions(self, force_reset_abort: bool = False) -> int:
        """
        Inspects QUEUED missions and dispatches them in parallel to available VM slots.
        Skips accounts with SANITY_EMPTY until sanity recovers.
        Returns the number of newly dispatched missions.
        """
        if force_reset_abort:
            AbortController.reset()

        if AbortController.is_aborted():
            logger.warning("[!] Abort signal active. Halting fleet dispatch.")
            return 0

        self._refresh_vm_slots()
        queued_missions = self.mission_mgr.list_missions(status=MissionStatus.QUEUED)
        if not queued_missions:
            return 0

        dispatched_count = 0

        for mission in queued_missions:
            acc_id = mission["account_id"]
            acc = self.account_mgr.get_account(acc_id)

            # Sanity depletion guard: skip accounts with no sanity
            if acc and acc.get("current_status") == "SANITY_EMPTY":
                logger.info(f"[*] Skipping mission {mission['mission_id']} for account {acc_id}: SANITY_EMPTY")
                continue

            target_vm = acc.get("assigned_instance", 0) if acc else 0

            assigned_slot = None
            with self._state_lock:
                # 1. First priority: Check preferred assigned instance
                if target_vm in self._slots and self._slots[target_vm]["status"] == "IDLE":
                    assigned_slot = target_vm
                else:
                    # 2. Dynamic fallback: Pick any free IDLE slot
                    for idx, slot in self._slots.items():
                        if slot["status"] == "IDLE":
                            assigned_slot = idx
                            break

                if assigned_slot is not None:
                    # Claim slot
                    self._slots[assigned_slot]["status"] = "RUNNING"
                    self._slots[assigned_slot]["current_account"] = acc_id
                    self._slots[assigned_slot]["current_mission_id"] = mission["mission_id"]
                    self._slots[assigned_slot]["current_mission_type"] = mission["mission_type"]
                    self._slots[assigned_slot]["progress"] = "正在启动多开实例..."

            if assigned_slot is not None:
                # Checkout mission atomically in database
                with self.mission_mgr._get_connection() as conn:
                    conn.execute("UPDATE missions SET status = 'RUNNING' WHERE mission_id = ?", (mission["mission_id"],))

                # Spawn worker thread for this VM slot
                t = threading.Thread(
                    target=self._run_slot_worker,
                    args=(assigned_slot, mission),
                    daemon=True,
                    name=f"VMWorker-{assigned_slot}"
                )
                self._threads[assigned_slot] = t
                t.start()
                dispatched_count += 1
                logger.info(f"[+] Dispatched mission {mission['mission_id']} ({acc_id}) to VM [{assigned_slot}] (Port: {16384 + 32 * assigned_slot})")

        return dispatched_count

    def dispatch_specific_mission(self, mission_id: str) -> bool:
        """Explicitly dispatches a specific target mission to a free VM slot."""
        AbortController.reset()
        self._refresh_vm_slots()
        mission = self.mission_mgr.get_mission(mission_id)
        if not mission or mission["status"] != MissionStatus.QUEUED:
            return False

        acc_id = mission["account_id"]
        acc = self.account_mgr.get_account(acc_id)
        if acc and acc.get("current_status") == "SANITY_EMPTY":
            logger.warning(f"[!] Cannot dispatch mission {mission_id}: Account {acc_id} is SANITY_EMPTY")
            return False

        target_vm = acc.get("assigned_instance", 0) if acc else 0

        assigned_slot = None
        with self._state_lock:
            if target_vm in self._slots and self._slots[target_vm]["status"] == "IDLE":
                assigned_slot = target_vm
            else:
                for idx, slot in self._slots.items():
                    if slot["status"] == "IDLE":
                        assigned_slot = idx
                        break

            if assigned_slot is not None:
                self._slots[assigned_slot]["status"] = "RUNNING"
                self._slots[assigned_slot]["current_account"] = acc_id
                self._slots[assigned_slot]["current_mission_id"] = mission["mission_id"]
                self._slots[assigned_slot]["current_mission_type"] = mission["mission_type"]
                self._slots[assigned_slot]["progress"] = "正在启动多开实例..."

        if assigned_slot is not None:
            with self.mission_mgr._get_connection() as conn:
                conn.execute("UPDATE missions SET status = 'RUNNING' WHERE mission_id = ?", (mission["mission_id"],))

            t = threading.Thread(
                target=self._run_slot_worker,
                args=(assigned_slot, mission),
                daemon=True,
                name=f"VMWorker-{assigned_slot}"
            )
            self._threads[assigned_slot] = t
            t.start()
            logger.info(f"[+] Specifically dispatched mission {mission_id} to VM [{assigned_slot}] (Port: {16384 + 32 * assigned_slot})")
            return True

        return False

    def _run_slot_worker(self, instance_index: int, mission: Dict[str, Any]):
        """Dedicated execution loop for an individual VM slot with account rotation detection."""
        m_id = mission["mission_id"]
        acc_id = mission["account_id"]
        port = 16384 + 32 * instance_index

        logger.info(f"[*] VM [{instance_index}] Worker thread started for {m_id} on port {port}")
        if self.telemetry_store:
            self.telemetry_store.add_log(
                "INFO",
                f"⚡ [多开并发] VM [{instance_index}] (端口 {port}) 接管工单 {m_id} ➔ 账号 {acc_id}"
            )

        # Detect account rotation on this slot
        is_switch = False
        with self._state_lock:
            last_acc = self._slots[instance_index].get("last_used_account")
            if last_acc and last_acc != acc_id:
                is_switch = True
                logger.info(f"[*] Account rotation detected on VM [{instance_index}]: {last_acc} ➔ {acc_id}")
            self._slots[instance_index]["last_used_account"] = acc_id

        if is_switch and self.telemetry_store:
            self.telemetry_store.add_log(
                "INFO",
                f"🔄 [账号轮转] VM [{instance_index}] 检测到账号变更: {last_acc} ➔ {acc_id}"
            )

        executor = TaskExecutor(
            mission_manager=self.mission_mgr,
            account_manager=self.account_mgr,
            telemetry_store=self.telemetry_store,
            instance_index=instance_index
        )

        try:
            res = executor.execute_mission(mission)
            logger.info(f"[+] VM [{instance_index}] execution result for {m_id}: {res}")
        except Exception as e:
            logger.error(f"[!] VM [{instance_index}] worker failed for {m_id}: {e}")
            self.mission_mgr.fail_mission(m_id, str(e))
        finally:
            with self._state_lock:
                if instance_index in self._slots:
                    self._slots[instance_index]["status"] = "IDLE"
                    self._slots[instance_index]["current_account"] = None
                    self._slots[instance_index]["current_mission_id"] = None
                    self._slots[instance_index]["current_mission_type"] = None
                    self._slots[instance_index]["progress"] = "待命就绪"

            # After freeing slot, check if more queued missions are waiting
            time.sleep(0.5)
            self.dispatch_pending_missions()

    def stop_all(self, reason: str = "指挥官中止全局多开"):
        """Emergency stop across all active VM workers."""
        AbortController.trigger_abort(reason)
        self.mission_mgr.abort_all_running_missions(reason)
        with self._state_lock:
            for idx, slot in self._slots.items():
                slot["status"] = "IDLE"
                slot["current_account"] = None
                slot["current_mission_id"] = None
                slot["progress"] = f"已中止: {reason}"
        logger.warning("🛑 [FleetOrchestrator] All VM worker slots stopped.")
