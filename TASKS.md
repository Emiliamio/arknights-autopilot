# 🎯 ASTA 研发进度与待办看板 (TASKS.md)

## 📌 当前状态总览
- 状态：开发中阶段性交接 (In-Flight Handover)
- 单元测试：`81 / 81` (100% 绿色通过)
- 架构分层：`core` (底层), `tactical` (战术大脑), `fleet` (多开调度)

---

## ✅ 已完成功能与已验收单测 (Completed)
- [x] **Core 底层驱动**
  - [x] 高性能 ADB 客户端与多端口发现 (`core/adb_client.py`)
  - [x] 3阶贝塞尔曲线拟人防检测滑动与高斯抖动 (`core/touch_humanizer.py`)
  - [x] 2.5D 透视投影单应性矩阵变换器 (`core/homography_mapper.py`)
  - [x] 视觉模板匹配与色彩特征检测 (`core/vision_engine.py`)
  - [x] 账号自动换绑与密码输入 (`core/auto_authenticator.py`)
  - [x] 线程安全一键中断控制器 (`core/abort_controller.py`)
  - [x] 游戏启动保活看门狗 (`core/game_launcher.py`)
- [x] **Tactical 战术中枢**
  - [x] 漏怪毫秒级抢占式救场看门狗 (`tactical/panic_daemon.py`)
  - [x] 战局威胁等级监护 (`tactical/threat_monitor.py`)
  - [x] 8大职业与干员特征原型库 (`tactical/operator_archetypes.py`)
  - [x] 动态阵容搭配评分器 (`tactical/squad_synthesizer.py`)
  - [x] 内置关卡拓扑与阻挡数据库 (`tactical/stage_database.py`)
  - [x] 全域终端与关卡跳转导航机 (`tactical/global_navigator.py`)
  - [x] MAA 作业协议双轨适配器 (`tactical/copilot_adapter.py`)
  - [x] 萨卡兹/水月肉鸽基础决策树 (`tactical/roguelike_brain.py`)
- [x] **Fleet 集群调度**
  - [x] 多账号 SQLite WAL 互斥检出 (`fleet/account_manager.py`)
  - [x] 任务队列与理智排班器 (`fleet/mission_manager.py`)
  - [x] 多实例调度中枢 (`fleet/fleet_orchestrator.py`)
  - [x] 任务 Worker 执行器 (`fleet/task_executor.py`)
  - [x] Web 监控面板 FastAPI + WebSocket 后端 (`fleet/dashboard/server.py`)

---

## 🚧 待攻坚任务清单 (Pending / Backlog) - 反重力接手优先级

### 优先级 P0：核心实机作战链路打通
- [ ] **Task 1: 实机作战主循环完整联调 (`tactical/universal_combat_pilot.py`)**
  - [ ] 联调 `core/adb_client.py` 实机截图与干员卡片费用识别
  - [ ] 联调 2.5D 单应性坐标映射到实机屏幕拖拽动作
  - [ ] 针对作战结束弹窗（理智耗尽/升级/掉落物多次点击）的容错循环
  - [ ] 编写实机模拟作战集成测试或回放测试

### 优先级 P1：多开模拟器集群实机联调
- [ ] **Task 2: 多开舰队并发压测 (`fleet/fleet_orchestrator.py`)**
  - [ ] 实机拉起 2 个 MuMu 模拟器实例（端口 16384 与 16416）
  - [ ] 验证任务交替执行、账号登出切换与理智恢复等待休眠

### 优先级 P2：肉鸽与高级战术策略深化
- [ ] **Task 3: 肉鸽地图实机节点导航 (`tactical/roguelike_brain.py`)**
  - [ ] 识别实机肉鸽节点图标与分支选择
  - [ ] 招募券自动匹配最优干员算法

### 优先级 P3：Web 监控面板前端建设
- [ ] **Task 4: Dashboard 前端界面完善 (`fleet/dashboard/static/`)**
  - [ ] 实时实例状态卡片与截图预览
  - [ ] 任务执行日志流展示
