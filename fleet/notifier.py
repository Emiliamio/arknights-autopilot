# -*- coding: utf-8 -*-
"""
ASTA - Arknights Sovereign Tactical Autopilot
Fleet Notifier & Multi-Channel Alert Broadcaster
Author: Emiliamio <mio2110767128@163.com>
"""

from typing import Dict, Any, Optional
import json
import logging
import requests

logger = logging.getLogger("ASTA.FleetNotifier")


class FleetNotifier:
    """
    Broadcasts rich Markdown battle reports, sanity summaries,
    and CAPTCHA slider security alerts to WeCom, DingTalk, or Telegram.
    """

    def __init__(self, default_webhook: Optional[str] = None):
        self.default_webhook = default_webhook
        self.sent_messages: list = []  # For audit & test isolation

    def format_daily_report_markdown(
        self,
        account_id: str,
        client_name: str,
        task_name: str,
        runs_completed: int,
        drops: Dict[str, int],
        sanity_spent: int
    ) -> str:
        """Formats an industrial executive daily battle report in Markdown."""
        drops_formatted = "\n".join([f"> • **{k}**: `+{v} 件`" for k, v in drops.items()]) if drops else "> • 暂无特殊掉落"

        md = f"""### 🛡️ ASTA 极星战术中枢 · 今日代肝结算战报
> **客户标识**：`{client_name}` (`{account_id}`)  
> **执行任务**：`{task_name}`  
> **作战统计**：通关 **{runs_completed}** 次 | 消耗理智 **{sanity_spent}** 点  
> **状态反馈**：✅ **理智已全部清空，账号已安全休眠下线**

#### 📦 战利品掉落统计：
{drops_formatted}

---
*Powered by ASTA Sovereign Tactical Autopilot | 工业级拟人防封*
"""
        return md.strip()

    def format_captcha_alert_markdown(
        self,
        account_id: str,
        client_name: str,
        screenshot_path: Optional[str] = None
    ) -> str:
        """Formats an urgent P0 security warning card when human slider verification is detected."""
        md = f"""### 🚨 【P0 紧急安全预警】检测到人机验证滑块！
> **受影响账号**：`{client_name}` (`{account_id}`)  
> **事件级别**：`CAPTCHA_LOCKED` (需人工干预)  
> **守护措施**：**已毫秒级强制熔断停机，杜绝连续失误引发平台风控！**  
> **现场截图**：`{screenshot_path or "已捕获并留存"}`

请管理员或客户立即使用手机或在客户端完成滑动验证后，回复指令继续执行！
"""
        return md.strip()

    def send_wecom_markdown(
        self,
        markdown_text: str,
        webhook_url: Optional[str] = None,
        mock: bool = False
    ) -> Dict[str, Any]:
        """Dispatches Markdown payload to Enterprise WeChat Bot."""
        target_url = webhook_url or self.default_webhook

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": markdown_text
            }
        }

        self.sent_messages.append({"type": "wecom", "payload": payload, "url": target_url})

        if mock or not target_url:
            return {"errcode": 0, "errmsg": "ok (mock or url omitted)"}

        try:
            resp = requests.post(target_url, json=payload, timeout=5.0)
            return resp.json() if resp.status_code == 200 else {"errcode": resp.status_code, "errmsg": resp.text}
        except Exception as e:
            logger.warning(f"WeCom notification failed: {e}")
            return {"errcode": -1, "errmsg": str(e)}

    def dispatch_daily_report(
        self,
        account_id: str,
        client_name: str,
        task_name: str,
        runs: int,
        drops: Dict[str, int],
        sanity_spent: int,
        webhook_url: Optional[str] = None,
        mock: bool = False
    ) -> Dict[str, Any]:
        """Convenience method to format and dispatch daily battle report."""
        md = self.format_daily_report_markdown(
            account_id, client_name, task_name, runs, drops, sanity_spent
        )
        return self.send_wecom_markdown(md, webhook_url=webhook_url, mock=mock)

    def dispatch_captcha_alert(
        self,
        account_id: str,
        client_name: str,
        screenshot_path: Optional[str] = None,
        webhook_url: Optional[str] = None,
        mock: bool = False
    ) -> Dict[str, Any]:
        """Convenience method to format and dispatch P0 slider alarm."""
        md = self.format_captcha_alert_markdown(account_id, client_name, screenshot_path)
        return self.send_wecom_markdown(md, webhook_url=webhook_url, mock=mock)