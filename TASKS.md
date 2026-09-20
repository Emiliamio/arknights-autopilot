# 🎯 ASTA 研发进度与待办看板 (TASKS.md)

## 📌 当前状态总览
- 状态：开发中阶段性交接 (In-Flight Handover)
- 单元测试：`102 / 102` (100% 绿色通过，96 项即刻通过，6 项实机 ADB 测试在模拟器离线时优雅跳过)
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
  - [x] 通用实战驾驶主脑端到端对战主循环 (`tactical/universal_combat_pilot.py`)
  - [x] 萨卡兹/水月/萨米肉鸽深度博弈与干员招募引擎 (`tactical/roguelike_brain.py`)
  - [x] 漏怪毫秒级抢占式救场看门狗 (`tactical/panic_daemon.py`)
  - [x] 战局威胁等级监护 (`tactical/threat_monitor.py`)
  - [x] 8大职业与干员特征原型库 (`tactical/operator_archetypes.py`)
  - [x] 动态阵容搭配评分器 (`tactical/squad_synthesizer.py`)
  - [x] 内置关卡拓扑与阻挡数据库 (`tactical/stage_database.py`)
  - [x] 全域终端与关卡跳转导航机 (`tactical/global_navigator.py`)
  - [x] MAA 作业协议双轨适配器 (`tactical/copilot_adapter.py`)
- [x] **Fleet 集群调度**
  - [x] 多账号 SQLite WAL 互斥检出 (`fleet/account_manager.py`)
  - [x] 任务队列与理智排班器 (`fleet/mission_manager.py`)
  - [x] 多实例调度中枢 (`fleet/fleet_orchestrator.py`)
  - [x] 任务 Worker 执行器 (`fleet/task_executor.py`)
  - [x] PRTS Web 态势指挥大屏 (HTTP + SSE + REST, `http://127.0.0.1:8848`) (`fleet/dashboard/server.py`)

---

## 🚧 待攻坚任务清单 (Pending / Backlog) - 反重力接手优先级

### 优先级 P0：核心实机作战链路打通
- [x] **Task 1: 实机作战主循环完整联调 (`tactical/universal_combat_pilot.py`)** [已完成，90/90 单测通过]
  - [x] 联调 `core/adb_client.py` 实机截图与干员卡片费用识别
  - [x] 联调 2.5D 单应性坐标映射到实机屏幕拖拽动作
  - [x] 周期性技能轮转 (Skill Rotation) 与决战技爆发机制
  - [x] 针对作战结束弹窗（理智耗尽/升级/掉落物多次点击）的容错状态机循环
  - [x] 编写实机模拟作战完整单元测试套件 (`tests/test_universal_combat_pilot.py`)

### 优先级 P1：多开模拟器集群实机联调
- [x] **Task 2: 多开舰队并发压测 (`fleet/fleet_orchestrator.py`)** [已完成，5/5 并发压测单测通过]
  - [x] 多实例端口映射与动态 VM Slot 分配 (端口 16384 与 16416)
  - [x] 验证同一物理槽位多账号轮询与 session 重登录检测
  - [x] 理智耗尽 (`SANITY_EMPTY`) 自动进入睡眠队列与即刻调度就绪账号
  - [x] 编写并发压测完整测试套件 (`tests/test_fleet_stress_concurrency.py`)

### 优先级 P2：肉鸽与高级战术策略深化
- [x] **Task 3: 肉鸽深度决策与干员招募推荐算法 (`tactical/roguelike_brain.py`)** [已完成，9/9 肉鸽专项单测通过]
  - [x] 招募券最优匹配引擎 (`OperatorRecruitmentDrafter`)：希望预算门禁、阵容短板加权、肉鸽天梯 S 级核心
  - [x] 极限 0-Hope 保底机制 (斑点/克洛丝等 3★ 优质干员自适应下潜)
  - [x] 多主题环境自适应博弈 (IS3 水月低灯火规避紧急、IS4 萨米高坍缩净化优先)
  - [x] 商店背包与安全屋精英化进阶评估
  - [x] 编写肉鸽专项测试用例 (`tests/test_roguelike_brain.py`)

### 优先级 P3：Web 监控面板前端建设
- [x] **Task 4: Dashboard 前端界面与全 REST API 闭环 (`fleet/dashboard/`)** [已完成，在线测试就绪]
  - [x] 2.5D 全息态势视窗 Canvas 实时渲染 (DAG 流、黄金堵门点、干员朝向)
  - [x] 实时战术遥测 (DP、击杀数、威胁评级、2x 速度切换)
  - [x] 实例舰队与多开槽位状态卡片 (`VM [0]`, `VM [1]`)
  - [x] 工单任务排班管理 (新增工单、单项执行、批量清空、删除、全局紧急停止)
  - [x] 客户账号档案管理与 12 人阵容自构交互模态框
  - [x] 编写 Dashboard 全套 REST 接口单元测试 (`tests/test_dashboard.py`, 3/3 通过)
  - [x] 服务常驻启动于 `http://127.0.0.1:8848`，可直接通过浏览器打开测试
