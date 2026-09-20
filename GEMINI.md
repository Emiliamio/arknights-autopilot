# GEMINI.md - Google Antigravity Agent Project Instructions
> **项目名称**：ASTA (arknights-autopilot)  
> **唯一作者与架构师**：`Emiliamio <mio2110767128@163.com>`  
> **最高法典**：继承本地 `D:\Antigravity\MEMORY.md` (Mio-Charter)  
> **交接备忘录**：见根目录下 `HANDOVER.md` 与 `TASKS.md`

---

## 🎯 核心使命与项目交接状态
本项目正处于研发中期。当前 **81 项单元测试已 100% 绿色通过**。
接手本项目的 Antigravity 智能体必须：
1. **先读交接备忘录**：首先阅读 `HANDOVER.md` 和 `TASKS.md`，明确当前系统架构、已完成模块与断点；
2. **严禁破坏既有成果**：任何改动必须保证现有的 81 个单元测试（`pytest tests/`）持续保持 100% 通过；
3. **步步压测、拒绝浮躁**：每一项新功能（如实机对战主循环、多开编队、肉鸽决策）必须配合单元测试与实机容错验证；
4. **唯一署名绝对锁死**：Git Author / Committer 必须且永远为 `Emiliamio <mio2110767128@163.com>`。

---

## 🛠️ 本地运行环境与快速指令
- **Python 解释器**：`python` (Python 3.12 位于 `C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe`)
- **ADB 模拟器**：默认连接 `127.0.0.1:16384` (MuMu 12) 或 `127.0.0.1:5555`，标准分辨率 `1280x720` (280 DPI)
- **单元测试回归**：`pytest tests/`
- **单关作战实机调试**：`python main.py --mode combat --stage 1-7`
- **多开集群调度**：`python main.py --mode fleet`
- **遥测监控看板**：`python main.py --mode dashboard`
