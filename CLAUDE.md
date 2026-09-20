# CLAUDE.md - ASTA (明日方舟全自主战术中枢) Claude Code 专属开发指令
> **项目路径**：`D:\arknights-autopilot`  
> **最高主权人与唯一作者**：`Emiliamio <mio2110767128@163.com>`  
> **遵循总宪**：`C:\Users\Administrator\.claude\CLAUDE.md` (Mio-Charter)  
> **核心交接白皮书**：必须优先阅读根目录下 `HANDOVER.md` 与 `TASKS.md`

---

## 🎯 当前工程状态与研发断点
- **测试健康度**：全套 **81/81** 个单元测试 100% 绿色通过 (`pytest tests/`)。
- **当前所处阶段**：研发中期攻坚阶段（绝非完结状态）。
- **当前核心断点 (P0)**：
  - `tactical/universal_combat_pilot.py` 与 `core/adb_client.py` 联调：实机端到端对战主循环（识别开局费用 -> 单应性映射拖拽下干员 -> 技能释放 -> 结算跳过）。

---

## 🛠️ 本地运行与验证命令
- **自动化测试回归**：`pytest tests/`
- **单关卡实机作战**：`python main.py --mode combat --stage 1-7`
- **多开舰队调度**：`python main.py --mode fleet`
- **Web 监控大屏**：`python main.py --mode dashboard`
- **模拟器标准环境**：MuMu 12，分辨率 1280x720，DPI 280，ADB 端口 127.0.0.1:16384
