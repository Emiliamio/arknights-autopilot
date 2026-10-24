# GEMINI.md - ASTA (arknights-autopilot) Agent Project Instructions
> **项目名称**：ASTA (arknights-autopilot)  
> **唯一作者与架构师**：`Emiliamio <mio2110767128@163.com>`  
> **通用规范**：`~/.dsh/AGENTS.md`（§0 为冲突仲裁序）；本项目事实见根目录 `AGENTS.md`  
> **交接备忘录**：见根目录下 `HANDOVER.md` 与 `TASKS.md`

---

## 🎯 核心使命与项目交接状态
本项目正处于研发中期。`pytest tests/` 当前 **132 项**全部通过（数量随开发变化，以实跑为准）。
接手本项目时：

1. **先读交接备忘录**：首先阅读 `HANDOVER.md` 和 `TASKS.md`，明确当前系统架构、已完成模块与断点；
2. **严禁破坏既有成果**：任何改动必须保证 `pytest tests/` 持续全绿；失败自己修到通过，不得带病提交；
3. **步步压测、拒绝浮躁**：每一项新功能（如实机对战主循环、多开编队、肉鸽决策）必须配合单元测试与实机容错验证；
4. **唯一署名锁死**：Git Author / Committer 必须且永远为 `Emiliamio <mio2110767128@163.com>`；
5. **凭据零落地**：数据库账号口令只读 `~/.dsh/private.env.md`，绝不写进本仓库任何文件——
   连"历史旧口令"也不要留，公开仓库里的旧口令会被误当成有效凭据。

---

## 🛠️ 本地运行环境与快速指令
- **Python 解释器**：`python` (Python 3.12，路径见 `D:\Antigravity\env-snapshot.json`)
- **ADB 模拟器**：默认连接 `127.0.0.1:16384` (MuMu 12) 或 `127.0.0.1:5555`，标准分辨率 `1280x720` (280 DPI)
- **单元测试回归**：`pytest tests/`
- **单关作战实机调试**：`python main.py --mode combat --stage 1-7`
- **多开集群调度**：`python main.py --mode fleet`
- **遥测监控看板**：`python main.py --mode dashboard`