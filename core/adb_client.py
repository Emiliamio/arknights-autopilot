# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Industrial ADB Client & MuMu 12 Auto-Daemon
Author: Emiliamio <mio2110767128@163.com>
"""

import os
import sys
import time
import json
import logging
import subprocess
from typing import Optional, Tuple, Dict, Any, List
import numpy as np
import cv2

try:
    import adbutils
    HAS_ADBUTILS = True
except ImportError:
    HAS_ADBUTILS = False

from core.touch_humanizer import TouchHumanizer

logger = logging.getLogger("ASTA.ADB")


class ADBClient:
    """
    Industrial-grade ADB interface tailored for MuMu Player 12.
    Features:
    1. Zero-downtime auto-boot & socket reconnection.
    2. Accurate screen orientation detection (Portrait vs Landscape).
    3. Multi-tier zero-copy screencap pipeline (raw uncompressed framebuffer 160ms -> adbutils -> PNG fallback).
    4. Hardware-level multi-point Bezier motion events (input motionevent DOWN->MOVE...->UP).
    5. Screen boundary safety clamping to prevent illegal coordinates.
    6. Atomic single-stream operator deployment (card pickup -> drag -> tile pause -> flick -> release).
    """

    def __init__(
        self,
        mumu_manager_path: str = r"D:\mumu模拟器\MuMu Player 12\nx_main\MuMuManager.exe",
        adb_path: str = r"D:\mumu模拟器\MuMu Player 12\nx_device\12.0\shell\adb.exe",
        instance_index: int = 0,
        target_host: str = "127.0.0.1",
        default_ports: Optional[List[int]] = None,
        humanizer: Optional[TouchHumanizer] = None,
        preferred_screencap_method: str = "auto"
    ):
        self.mumu_manager_path = mumu_manager_path
        self.adb_path = adb_path
        self.instance_index = instance_index
        self.target_host = target_host
        self.default_ports = default_ports or [16384, 16416, 7555, 5555, 5557]
        self.humanizer = humanizer or TouchHumanizer()
        self.preferred_screencap_method = preferred_screencap_method

        self.device_serial: Optional[str] = None
        self.connected_port: Optional[int] = None
        self.resolution: Optional[Tuple[int, int]] = None
        self._adbutils_device = None

    def _auto_discover_mumu_path(self) -> str:
        """Self-heals MuMuManager.exe location across common paths or active processes."""
        candidates = [
            self.mumu_manager_path,
            r"D:\mumu模拟器\MuMu Player 12\nx_main\MuMuManager.exe",
            r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\MuMuManager.exe",
            r"D:\Program Files\Netease\MuMuPlayer-12.0\shell\MuMuManager.exe",
            r"C:\Program Files\Netease\MuMuPlayer-12.0\nx_main\MuMuManager.exe",
            r"D:\Program Files\Netease\MuMuPlayer-12.0\nx_main\MuMuManager.exe"
        ]
        for path in candidates:
            if path and os.path.exists(path):
                return path

        if sys.platform == "win32":
            try:
                cmd = "Get-Process | Where-Object { $_.ProcessName -like '*MuMu*' } | Select-Object -ExpandProperty Path -First 1"
                res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=3)
                proc_path = res.stdout.strip()
                if proc_path and os.path.exists(proc_path):
                    dir_name = os.path.dirname(proc_path)
                    cand = os.path.join(dir_name, "MuMuManager.exe")
                    if os.path.exists(cand):
                        return cand
            except Exception:
                pass

        return self.mumu_manager_path

    def execute_mumu_cmd(self, args: List[str], timeout: int = 15) -> Dict[str, Any]:
        """Executes a command on MuMuManager.exe and parses JSON output."""
        if not os.path.exists(self.mumu_manager_path):
            self.mumu_manager_path = self._auto_discover_mumu_path()
        if not os.path.exists(self.mumu_manager_path):
            raise FileNotFoundError(f"MuMuManager.exe not found at: {self.mumu_manager_path}")

        cmd = [self.mumu_manager_path] + args
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        try:
            return json.loads(res.stdout) if res.stdout.strip() else {}
        except Exception:
            return {"raw_stdout": res.stdout, "raw_stderr": res.stderr}

    def get_instance_info(self) -> Dict[str, Any]:
        """Queries status of all instances from MuMuManager."""
        data = self.execute_mumu_cmd(["info", "-v", "all"])
        return data.get(str(self.instance_index), {})

    def is_instance_running(self) -> bool:
        """Checks whether target MuMu 12 instance is booted."""
        info = self.get_instance_info()
        return bool(info.get("is_android_started", False))

    def bring_mumu_to_foreground(self):
        """Brings MuMu 12 window to the front of Windows desktop so the user sees it."""
        try:
            ps_script = """
            $p = Get-Process | Where-Object {($_.ProcessName -like "*MuMu*" -or $_.ProcessName -like "*Nemu*") -and $_.MainWindowHandle -ne 0} | Select-Object -First 1
            if ($p) {
                Add-Type @"
                    using System;
                    using System.Runtime.InteropServices;
                    public class Win32 {
                        [DllImport("user32.dll")]
                        [return: MarshalAs(UnmanagedType.Bool)]
                        public static extern bool SetForegroundWindow(IntPtr hWnd);
                        [DllImport("user32.dll")]
                        public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                    }
"@
                [Win32]::ShowWindow($p.MainWindowHandle, 9)
                [Win32]::SetForegroundWindow($p.MainWindowHandle)
            }
            """
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], timeout=6, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def launch_instance(self, wait_timeout: int = 60) -> bool:
        """Launches target MuMu 12 instance via MuMuManager and waits until Android boots."""
        print(f"[*] Launching MuMu 12 instance {self.instance_index} via MuMuManager...")
        self.execute_mumu_cmd(["control", "-v", str(self.instance_index), "launch"])

        t0 = time.time()
        while time.time() - t0 < wait_timeout:
            info = self.get_instance_info()
            if info.get("is_android_started", False):
                print(f"[+] MuMu 12 instance {self.instance_index} booted successfully in {time.time() - t0:.1f}s!")
                time.sleep(3)  # Allow internal adbd to bind socket
                return True
            time.sleep(2)

        raise TimeoutError(f"MuMu 12 instance {self.instance_index} failed to boot within {wait_timeout}s.")

    def run_adb(self, args: List[str], timeout: int = 15, binary: bool = False) -> subprocess.CompletedProcess:
        """Executes an ADB command with device targeting and auto-reconnection recovery."""
        if not os.path.exists(self.adb_path):
            raise FileNotFoundError(f"adb.exe not found at: {self.adb_path}")

        prefix = [self.adb_path]
        if self.device_serial:
            prefix += ["-s", self.device_serial]

        full_cmd = prefix + args
        res = subprocess.run(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )

        # Auto-reconnection guard if device disconnected
        if res.returncode != 0 and any(err in res.stderr.decode("utf-8", errors="ignore").lower() for err in ["device not found", "device offline"]):
            try:
                self.connect(auto_launch=False)
                prefix = [self.adb_path, "-s", self.device_serial]
                res = subprocess.run(prefix + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            except Exception:
                pass

        return res

    def shell(self, cmd: str, timeout: int = 15) -> str:
        """Executes an adb shell command and returns trimmed stdout string."""
        res = self.run_adb(["shell", cmd], timeout=timeout)
        out = res.stdout.decode("utf-8", errors="replace") if isinstance(res.stdout, bytes) else str(res.stdout)
        return out.strip()

    def connect(self, auto_launch: bool = True) -> str:
        """
        Discovers, boots (if needed), and establishes reliable ADB connection.
        Returns the connected device serial.
        """
        if not self.is_instance_running():
            if auto_launch:
                self.launch_instance()
            else:
                raise RuntimeError(f"MuMu 12 instance {self.instance_index} is not running.")

        try:
            self.execute_mumu_cmd(["adb", "-v", str(self.instance_index), "-c", "connect"])
        except Exception:
            pass

        candidate_ports = [16384 + 32 * self.instance_index] + self.default_ports
        candidate_ports = list(dict.fromkeys(candidate_ports))

        connected_serial = None
        for port in candidate_ports:
            target = f"{self.target_host}:{port}"
            res = self.run_adb(["connect", target], timeout=5)
            out = res.stdout.decode("utf-8", errors="ignore")
            if "connected" in out.lower() or "already connected" in out.lower():
                state_res = subprocess.run(
                    [self.adb_path, "-s", target, "get-state"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5
                )
                if state_res.stdout.strip() == "device":
                    connected_serial = target
                    self.connected_port = port
                    print(f"[+] Connected to ADB target: {target}")
                    break

        if not connected_serial:
            dev_res = self.run_adb(["devices"], timeout=5)
            dev_out = dev_res.stdout.decode("utf-8", errors="ignore")
            for line in dev_out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and parts[1] == "device":
                    connected_serial = parts[0]
                    print(f"[+] Connected to fallback device: {connected_serial}")
                    break

        if not connected_serial:
            raise ConnectionError(f"Failed to connect to ADB for instance {self.instance_index}.")

        self.device_serial = connected_serial

        if HAS_ADBUTILS:
            try:
                adb_server = adbutils.AdbClient(host="127.0.0.1", port=5037)
                self._adbutils_device = adb_server.device(self.device_serial)
            except Exception as e:
                logger.warning(f"Failed to init adbutils device: {e}")
                self._adbutils_device = None

        self.get_resolution(force_refresh=True)
        return self.device_serial

    def get_resolution(self, force_refresh: bool = False) -> Tuple[int, int]:
        """Retrieves true active screen viewport resolution (width, height)."""
        if self.resolution and not force_refresh:
            return self.resolution

        try:
            res = self.run_adb(["shell", "dumpsys", "input"])
            out = res.stdout.decode("utf-8", errors="ignore")
            for line in out.splitlines():
                if "Viewport Width:" in line:
                    vw = int(line.split(":")[-1].strip())
                elif "Viewport Height:" in line:
                    vh = int(line.split(":")[-1].strip())
                    if "vw" in locals() and vw > 0 and vh > 0:
                        self.resolution = (vw, vh)
                        self.humanizer.set_screen_bounds(vw, vh)
                        return self.resolution
        except Exception:
            pass

        try:
            size_res = self.run_adb(["shell", "wm", "size"])
            size_out = size_res.stdout.decode("utf-8", errors="ignore")
            raw_w, raw_h = 1920, 1080
            for line in size_out.splitlines():
                if "size:" in line.lower() and "x" in line:
                    parts = line.split(":")[-1].strip().split("x")
                    raw_w, raw_h = int(parts[0]), int(parts[1])
                    break

            orient_res = self.run_adb(["shell", "dumpsys", "window", "displays"])
            orient_out = orient_res.stdout.decode("utf-8", errors="ignore")
            is_landscape = True
            for line in orient_out.splitlines():
                if "mCurrentRotation" in line or "cur=" in line:
                    if "=1" in line or "=3" in line or "ROTATION_90" in line or "ROTATION_270" in line:
                        is_landscape = True
                        break
                    elif "=0" in line or "=2" in line:
                        is_landscape = False
                        break

            if is_landscape:
                true_w = max(raw_w, raw_h)
                true_h = min(raw_w, raw_h)
            else:
                true_w = min(raw_w, raw_h)
                true_h = max(raw_w, raw_h)

            self.resolution = (true_w, true_h)
            self.humanizer.set_screen_bounds(true_w, true_h)
            return self.resolution
        except Exception:
            pass

        self.resolution = (1920, 1080)
        self.humanizer.set_screen_bounds(1920, 1080)
        return self.resolution

    def get_current_app(self) -> Dict[str, str]:
        """Retrieves currently focused package and activity."""
        res = self.run_adb(["shell", "dumpsys", "window"])
        out = res.stdout.decode("utf-8", errors="ignore")
        package, activity = "", ""
        for line in out.splitlines():
            if "mCurrentFocus" in line or "mFocusedApp" in line:
                if "/" in line:
                    segment = line.split("/")
                    pkg_part = segment[0].split()[-1]
                    act_part = segment[1].split()[0].rstrip("}")
                    package = pkg_part
                    activity = act_part
                    break
        return {"package": package, "activity": activity}

    def _screencap_raw_framebuffer(self) -> Optional[np.ndarray]:
        """Tier 1: Direct uncompressed raw framebuffer read (~160ms)."""
        try:
            res = self.run_adb(["exec-out", "screencap"], timeout=4, binary=True)
            raw = res.stdout
            if len(raw) < 16:
                return None
            w = int.from_bytes(raw[0:4], byteorder="little")
            h = int.from_bytes(raw[4:8], byteorder="little")
            expected_bytes = 16 + w * h * 4
            if len(raw) >= expected_bytes and w > 0 and h > 0:
                img_rgba = np.frombuffer(raw[16:expected_bytes], dtype=np.uint8).reshape((h, w, 4))
                return cv2.cvtColor(img_rgba, cv2.COLOR_RGBA2BGR)
        except Exception:
            pass
        return None

    def _screencap_adbutils(self) -> Optional[np.ndarray]:
        """Tier 2: Socket screencap via adbutils."""
        if not self._adbutils_device:
            return None
        try:
            pil_img = self._adbutils_device.screenshot()
            img_rgb = np.array(pil_img)
            return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            return None

    def _screencap_png_fallback(self) -> np.ndarray:
        """Tier 3: Standard PNG decode fallback (~750ms)."""
        res = self.run_adb(["exec-out", "screencap", "-p"], timeout=6, binary=True)
        if not res.stdout:
            raise RuntimeError(f"Screencap failed: {res.stderr.decode('utf-8', errors='ignore')}")
        img_array = np.frombuffer(res.stdout, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Failed to decode screencap buffer of size {len(res.stdout)} bytes.")
        return img

    def screencap(self, method: Optional[str] = None) -> np.ndarray:
        """Captures a frame using the fastest available pipeline."""
        sel_method = method or self.preferred_screencap_method
        img = None

        if sel_method in ("auto", "raw"):
            img = self._screencap_raw_framebuffer()

        if img is None and sel_method in ("auto", "adbutils"):
            img = self._screencap_adbutils()

        if img is None:
            img = self._screencap_png_fallback()

        if img is not None and len(img.shape) >= 2:
            h, w = img.shape[0], img.shape[1]
            if not self.resolution or self.resolution != (w, h):
                self.resolution = (w, h)
                self.humanizer.set_screen_bounds(w, h)

        return img

    def benchmark_screencap(self, n_frames: int = 5) -> Dict[str, Any]:
        """Benchmarks all available screencap tiers and reports performance comparison."""
        tiers = {}

        times_raw = []
        for _ in range(n_frames):
            t0 = time.perf_counter()
            img = self._screencap_raw_framebuffer()
            if img is not None:
                times_raw.append((time.perf_counter() - t0) * 1000.0)
        if times_raw:
            tiers["raw_framebuffer"] = {
                "avg_ms": round(sum(times_raw) / len(times_raw), 1),
                "min_ms": round(min(times_raw), 1),
                "max_ms": round(max(times_raw), 1)
            }

        if self._adbutils_device:
            times_adb = []
            for _ in range(min(3, n_frames)):
                t0 = time.perf_counter()
                img = self._screencap_adbutils()
                if img is not None:
                    times_adb.append((time.perf_counter() - t0) * 1000.0)
            if times_adb:
                tiers["adbutils_stream"] = {
                    "avg_ms": round(sum(times_adb) / len(times_adb), 1),
                    "min_ms": round(min(times_adb), 1),
                    "max_ms": round(max(times_adb), 1)
                }

        times_png = []
        for _ in range(min(2, n_frames)):
            t0 = time.perf_counter()
            img = self._screencap_png_fallback()
            if img is not None:
                times_png.append((time.perf_counter() - t0) * 1000.0)
        if times_png:
            tiers["png_exec_out"] = {
                "avg_ms": round(sum(times_png) / len(times_png), 1),
                "min_ms": round(min(times_png), 1),
                "max_ms": round(max(times_png), 1)
            }

        active_times = []
        sample_img = None
        for _ in range(n_frames):
            t0 = time.perf_counter()
            sample_img = self.screencap()
            active_times.append((time.perf_counter() - t0) * 1000.0)

        avg_lat = sum(active_times) / len(active_times)
        fps = 1000.0 / avg_lat if avg_lat > 0 else 0.0

        return {
            "n_frames": n_frames,
            "avg_latency_ms": round(avg_lat, 2),
            "min_latency_ms": round(min(active_times), 2),
            "max_latency_ms": round(max(active_times), 2),
            "approx_fps": round(fps, 1),
            "frame_shape": list(sample_img.shape) if sample_img is not None else [],
            "tiers_benchmark": tiers
        }

    def tap(self, x: float, y: float) -> Dict[str, Any]:
        """Executes an anti-detection humanized tap with Gaussian scatter."""
        tap_info = self.humanizer.generate_tap(x, y)
        jx, jy = tap_info["x"], tap_info["y"]
        dur_ms = tap_info["duration_ms"]
        self.run_adb(["shell", "input", "swipe", str(jx), str(jy), str(jx), str(jy), str(dur_ms)])
        return tap_info

    def swipe_bezier(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        steps: int = 15,
        duration_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """Executes a true hardware-level Cubic Bezier curved swipe."""
        trajectory = self.humanizer.generate_bezier_trajectory(
            x1, y1, x2, y2, steps=steps, duration_ms=duration_ms
        )

        cmds = []
        p0 = trajectory[0]
        cmds.append(f"input motionevent DOWN {p0[0]} {p0[1]}")
        for p in trajectory[1:-1]:
            cmds.append(f"input motionevent MOVE {p[0]} {p[1]}")
        pn = trajectory[-1]
        cmds.append(f"input motionevent UP {pn[0]} {pn[1]}")

        compound_cmd = "; ".join(cmds)
        t0 = time.perf_counter()
        res = self.run_adb(["shell", compound_cmd], timeout=8)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "trajectory_steps": len(trajectory),
            "start": (p0[0], p0[1]),
            "end": (pn[0], pn[1]),
            "execution_time_ms": round(elapsed_ms, 1),
            "status": "success" if res.returncode == 0 else "error",
            "stderr": res.stderr.decode("utf-8", errors="ignore")
        }

    def deploy_operator_gesture(self, gesture_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes an atomic, continuous deployment touch sequence:
        DOWN at card -> Drag along Bezier -> Pause on grid -> Flick towards orientation -> UP to lock.
        Zero multi-session lifts, 100% faithful to Arknights engine mechanics.
        """
        drag_pts = gesture_dict["drag_trajectory"]
        flick_pts = gesture_dict["flick_trajectory"]
        pause_ms = gesture_dict.get("pause_before_flick_ms", 100)

        cmds = []
        p0 = drag_pts[0]
        cmds.append(f"input motionevent DOWN {p0[0]} {p0[1]}")
        for p in drag_pts[1:]:
            cmds.append(f"input motionevent MOVE {p[0]} {p[1]}")

        # Magnetic tile pause
        cmds.append(f"sleep {pause_ms / 1000.0:.3f}")

        # Directional orientation flick
        for p in flick_pts:
            cmds.append(f"input motionevent MOVE {p[0]} {p[1]}")

        # Confirm and deploy
        pn = flick_pts[-1]
        cmds.append(f"input motionevent UP {pn[0]} {pn[1]}")

        compound_cmd = "; ".join(cmds)
        t0 = time.perf_counter()
        res = self.run_adb(["shell", compound_cmd], timeout=10)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "drag_steps": len(drag_pts),
            "flick_steps": len(flick_pts),
            "execution_time_ms": round(elapsed_ms, 1),
            "status": "success" if res.returncode == 0 else "error",
            "stderr": res.stderr.decode("utf-8", errors="ignore")
        }

    def swipe(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        duration_ms: Optional[int] = None,
        bezier: bool = True
    ) -> Dict[str, Any]:
        """Executes a humanized swipe."""
        if bezier:
            return self.swipe_bezier(x1, y1, x2, y2, steps=15, duration_ms=duration_ms)

        p1 = self.humanizer.jitter_point(x1, y1)
        p2 = self.humanizer.jitter_point(x2, y2)
        if duration_ms is None:
            import random
            duration_ms = random.randint(self.humanizer.swipe_duration_ms[0], self.humanizer.swipe_duration_ms[1])

        self.run_adb([
            "shell", "input", "swipe",
            str(p1[0]), str(p1[1]),
            str(p2[0]), str(p2[1]),
            str(duration_ms)
        ])
        return {"start": p1, "end": p2, "duration_ms": duration_ms, "type": "linear"}