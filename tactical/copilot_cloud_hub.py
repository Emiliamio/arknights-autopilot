# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Cloud Copilot Hub: Online MAA Community Plan Crawler, Search Engine & Auto-Downloader
Author: Emiliamio <mio2110767128@163.com>
"""

import os
import re
import json
import logging
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple

from tactical.copilot_adapter import CopilotAdapter, CopilotPlan

logger = logging.getLogger("ASTA.CopilotCloudHub")


class CopilotCloudHub:
    """
    Online MAA Community Plan Discovery & Auto-Download Hub:
    - Queries public PRTS / MAA Copilot endpoints for any stage across all chapters & events.
    - Extracts author (uploader), rating score, like count, view count, and strategy summary.
    - Downloads full copilot action sequence and caches locally in data/copilots/.
    - Provides automatic resolution of the #1 highest-rated community plan for any stage.
    """

    QUERY_API = "https://prts.maa.plus/copilot/query"
    GET_API = "https://prts.maa.plus/copilot/get"
    CACHE_DIR = os.path.abspath("data/copilots")

    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = cache_dir or self.CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

    @classmethod
    def get_candidate_keywords(cls, stage_code: str) -> List[str]:
        """Maps user display codes (e.g. '1-7', 'H12-2', 'CW-10') to MAA levelKeywords."""
        code = stage_code.strip().upper()
        candidates = [code]

        # 1. Mainline normal: e.g. 1-7 -> main_01-07, 0-4 -> main_00-04, 14-21 -> main_14-21
        m = re.match(r"^(\d+)\-(\d+)$", code)
        if m:
            ch, st = int(m.group(1)), int(m.group(2))
            candidates.insert(0, f"main_{ch:02d}-{st:02d}")

        # 2. Mainline Hard: e.g. H12-2 -> hard_12-02
        m_hard = re.match(r"^H(\d+)\-(\d+)$", code)
        if m_hard:
            ch, st = int(m_hard.group(1)), int(m_hard.group(2))
            candidates.insert(0, f"hard_{ch:02d}-{st:02d}")

        return candidates

    def search_cloud_plans(
        self,
        stage_keyword: str,
        page: int = 1,
        limit: int = 10,
        timeout_sec: float = 6.0
    ) -> List[Dict[str, Any]]:
        """
        Searches community MAA copilot plans for the target stage.
        Returns a structured list of available plan previews.
        """
        keyword = stage_keyword.strip().upper()
        candidates = self.get_candidate_keywords(keyword)

        for candidate in candidates:
            params = urllib.parse.urlencode({
                "page": page,
                "limit": limit,
                "levelKeyword": candidate
            })
            url = f"{self.QUERY_API}?{params}"
            logger.info(f"[*] Querying cloud copilot plans for candidate [{candidate}] (stage: [{keyword}]) from: {url}")

            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ASTA/2026.09 (PRTS Command)",
                    "Accept": "application/json"
                }
            )

            try:
                with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                    if response.status != 200:
                        continue

                    raw_data = json.loads(response.read().decode("utf-8"))
                    items = raw_data.get("data", {}).get("data", [])
                    results = []

                    for item in items:
                        plan_id = item.get("id")
                        uploader = item.get("uploader", "社区指挥官")
                        likes = item.get("like", 0)
                        views = item.get("views", 0)
                        rating_ratio = item.get("rating_ratio", 0.0)

                        content_str = item.get("content", "{}")
                        title = f"{keyword} 社区作业"
                        details = ""
                        opers_count = 0
                        actual_stage = ""
                        try:
                            inner = json.loads(content_str)
                            doc = inner.get("doc", {})
                            title = doc.get("title") or title
                            details = doc.get("details", "")
                            opers_count = len(inner.get("opers", []))
                            actual_stage = inner.get("stage_name", "")
                        except Exception:
                            pass

                        clean_kw = keyword.replace("-", "")
                        clean_cand = candidate.replace("-", "").replace("_", "")
                        clean_actual = actual_stage.upper().replace("-", "").replace("_", "")
                        clean_title = title.upper().replace("-", "").replace("_", "")

                        matched = (
                            clean_cand in clean_actual or
                            clean_kw in clean_actual or
                            clean_kw in clean_title or
                            clean_kw in details.upper()
                        )
                        if not matched:
                            continue

                        results.append({
                            "id": plan_id,
                            "title": title,
                            "stage_name": keyword,
                            "uploader": uploader,
                            "likes": likes,
                            "views": views,
                            "rating_ratio": round(rating_ratio, 2),
                            "details": details,
                            "opers_count": opers_count,
                            "source": "MAA_COMMUNITY"
                        })

                    if results:
                        results.sort(key=lambda x: -x["likes"])
                        logger.info(f"[+] Found {len(results)} cloud copilot plans for [{keyword}] (via candidate {candidate})")
                        return results

            except Exception as e:
                logger.warning(f"[!] Candidate [{candidate}] search exception: {e}")
                continue

        # Fallback to local cache search if online returned nothing
        return self._fallback_local_search(keyword)

    def fetch_and_cache_plan(
        self,
        plan_id: int,
        stage_name: str,
        timeout_sec: float = 8.0
    ) -> Tuple[Optional[CopilotPlan], str]:
        """
        Downloads a full copilot plan JSON by plan_id and caches it locally.
        Returns: (CopilotPlan, local_filepath)
        """
        # Check if already cached locally
        safe_stage = re.sub(r'[^\w\-]', '_', stage_name)
        cached_filename = f"{safe_stage}_{plan_id}.json"
        cached_path = os.path.join(self.cache_dir, cached_filename)

        if os.path.exists(cached_path) and os.path.getsize(cached_path) > 50:
            logger.info(f"[+] Loading cached cloud copilot plan from: {cached_path}")
            plan = CopilotAdapter.load_file(cached_path)
            return plan, cached_path

        url = f"{self.GET_API}/{plan_id}"
        logger.info(f"[*] Downloading cloud copilot plan #{plan_id} from: {url}")

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ASTA/2026.09 (PRTS Command)",
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP error {response.status} fetching copilot plan {plan_id}")

                raw_data = json.loads(response.read().decode("utf-8"))
                content_str = raw_data.get("data", {}).get("content")
                if not content_str:
                    raise ValueError(f"Plan #{plan_id} content is empty or invalid")

                # Parse and pretty write to local cache file
                plan_json = json.loads(content_str)
                with open(cached_path, "w", encoding="utf-8") as f:
                    json.dump(plan_json, f, ensure_ascii=False, indent=2)

                logger.info(f"[+] Successfully cached plan #{plan_id} to: {cached_path}")
                plan = CopilotAdapter.load_file(cached_path)
                return plan, cached_path

        except Exception as e:
            logger.error(f"[!] Failed to fetch plan #{plan_id}: {e}")
            raise

    def auto_resolve_best_plan(self, stage_name: str) -> Tuple[CopilotPlan, str]:
        """
        Auto-resolves the single best copilot plan for any stage:
        1. Checks if a verified local plan for this stage exists.
        2. Otherwise, queries cloud community API and downloads the #1 liked plan.
        3. If all fails, falls back to a synthesized universal baseline.
        """
        norm_stage = stage_name.strip().upper()
        clean_norm = norm_stage.replace("-", "")

        # Check local plans first (strict stage_name matching)
        import glob
        for fpath in glob.glob(os.path.join(self.cache_dir, "*.json")):
            try:
                plan = CopilotAdapter.load_file(fpath)
                p_stage = (plan.stage_name or "").upper().replace("-", "")
                if clean_norm and clean_norm == p_stage:
                    logger.info(f"[+] Found local verified copilot plan for [{norm_stage}]: {fpath}")
                    return plan, fpath
            except Exception:
                pass

        # Search online
        cloud_list = self.search_cloud_plans(norm_stage, limit=5)
        if cloud_list:
            best_id = cloud_list[0]["id"]
            logger.info(f"[*] Auto-selecting highest-rated cloud plan #{best_id} for [{norm_stage}]")
            return self.fetch_and_cache_plan(best_id, norm_stage)

        # Fallback: create emergency universal baseline plan
        fallback_path = self._create_emergency_baseline_plan(norm_stage)
        return CopilotAdapter.load_file(fallback_path), fallback_path

    def _fallback_local_search(self, stage_keyword: str) -> List[Dict[str, Any]]:
        """Scans local data/copilots directory when network is unavailable."""
        import glob
        results = []
        norm = stage_keyword.upper().replace("-", "")
        for fpath in glob.glob(os.path.join(self.cache_dir, "*.json")):
            try:
                plan = CopilotAdapter.load_file(fpath)
                p_stage = (plan.stage_name or "").upper().replace("-", "")
                p_title = (plan.title or "").upper().replace("-", "")
                if norm and (norm in p_stage or norm in p_title):
                    results.append({
                        "id": hash(os.path.basename(fpath)) % 100000,
                        "title": plan.title or os.path.basename(fpath),
                        "stage_name": plan.stage_name or stage_keyword,
                        "uploader": "本地作业库 (Cached)",
                        "likes": 999,
                        "views": 1000,
                        "rating_ratio": 1.0,
                        "details": plan.details or "本地离线作业方案",
                        "opers_count": len(plan.opers),
                        "source": "LOCAL_CACHE",
                        "filepath": fpath
                    })
            except Exception:
                pass
        return results

    def _create_emergency_baseline_plan(self, stage_name: str) -> str:
        """Generates a minimal fallback copilot plan if none exists anywhere."""
        fallback_file = os.path.join(self.cache_dir, f"{stage_name}_auto_baseline.json")
        baseline_data = {
            "stage_name": stage_name,
            "minimum_required": "v4.0.0",
            "doc": {
                "title": f"{stage_name} ASTA 自适应通用防守方案",
                "details": "由 ASTA 战术中枢自动推演生成的保底防线方案，底层搭载 PanicDaemon 抢占式截停。"
            },
            "opers": [
                {"name": "芬", "skill": 1, "skill_usage": 0},
                {"name": "克洛丝", "skill": 1, "skill_usage": 1},
                {"name": "斑点", "skill": 1, "skill_usage": 0},
                {"name": "砾", "skill": 1, "skill_usage": 0}
            ],
            "actions": [
                {"type": "二倍速"},
                {"type": "部署", "name": "芬", "location": [9, 2], "direction": "右", "costs": 10},
                {"type": "部署", "name": "克洛丝", "location": [6, 0], "direction": "下", "costs": 12},
                {"type": "部署", "name": "斑点", "location": [9, 3], "direction": "上", "costs": 16}
            ]
        }
        with open(fallback_file, "w", encoding="utf-8") as f:
            json.dump(baseline_data, f, ensure_ascii=False, indent=2)
        return fallback_file
