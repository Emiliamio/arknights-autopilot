# 📋 ASTA (arknights-autopilot) 项目无缝交接白皮书 (Handover Specification)
> **交接状态**：开发中阶段性交接 (In-Flight Development Handover)  
> **交接目标环境**：Google Antigravity IDE (反重力智能体)  
> **唯一作者与架构师**：`Emiliamio <mio2110767128@163.com>`  
> **基准日期**：2026-09-20  
> **当前工程健康度**：`81 / 81` 单元测试全部通过 (`pytest tests/`)

---

## 🧭 一、项目定位与系统全景 (Project Overview)

ASTA 是专为《明日方舟》打造的**工业级全自主空间战术导航、拟人反作弊物理执行与多账号商业代肝中台**。
拒绝死板 JSON 脚本抄作业，核心采用 2.5D 透视单应性几何映射、拓扑网络流、毫秒级抢占式防漏怪看门狗与无头多开舰队编排调度。

### 目录与分层拓扑 (Architecture Map)
```
D:\arknights-autopilot\
├── core/                       # 底层硬件交互与反检测执行底座
│   ├── adb_client.py           # 高性能 ADB 封装 (支持直连/端口嗅探/截图流/物理输入)
│   ├── touch_humanizer.py      # 3阶贝塞尔曲线拟人防检测滑动、高斯散布点击
│   ├── homography_mapper.py    # 2.5D 战场斜透视投影单应性矩阵双向变换 (<0.05px 误差)
│   ├── vision_engine.py        # 模板匹配、色彩阈值感知、多分辨率自适应
│   ├── auto_authenticator.py   # 账号自动换绑/密码登录/Token鉴权管理
│   ├── abort_controller.py     # 线程安全的一键中断与平滑退出控制器
│   ├── game_launcher.py        # 游戏进程生命周期管理与崩溃重启保活
│   └── rapid_ocr_driver.py     # OCR 费用与击杀数文本直读
├── tactical/                   # 战术决策与认知推演大脑
│   ├── universal_combat_pilot.py # 通用自适应实战驾驶主脑 (状态机/技能轮转/下场规划)
│   ├── panic_daemon.py         # 毫秒级抢占式防漏怪与即兴空投救场看门狗
│   ├── threat_monitor.py       # 战局威胁度分级监护 (Green/Yellow/Red)
│   ├── operator_archetypes.py  # 8大职业与细分分支干员特征原型
│   ├── squad_synthesizer.py    # 动态阵容评分与干员出战优先级合成
│   ├── stage_database.py       # 内置核心关卡元数据 (1-7, CE-6, LS-6, PR-X 等)
│   ├── stage_analyzer.py       # 关卡高低地/阻挡点/行军路线分析
│   ├── global_navigator.py     # 终端/主线/物资/活动全域 UI 导航状态机
│   ├── roguelike_brain.py      # 萨卡兹/水月肉鸽路线推演与节点规划
│   └── copilot_adapter.py      # 兼容 MAA 作业协议的双轨解析适配器
├── fleet/                      # 多开集群调度与商业代肝管理层
│   ├── fleet_orchestrator.py   # 多实例分布式舰队调度器
│   ├── account_manager.py      # SQLite WAL 账号凭据库与并发租借锁
│   ├── mission_manager.py      # 任务队列、定时排班、理智恢复策略调度
│   ├── task_executor.py        # 单任务独立 Worker 执行线程
│   ├── multi_instance_runner.py# 模拟器多实例生命周期拉起与端口分配
│   └── dashboard/server.py     # Web 遥测与监控大屏后端 (FastAPI + WebSocket)
├── data/                       # 静态数据与资产
│   ├── maps/                   # 关卡地图拓扑定义 (YAML)
│   ├── copilots/               # 作业协议文件 (JSON)
│   └── rosters/                # 玩家练度干员库 (JSON)
├── tests/                      # 自动化测试套件 (81/81 全绿)
├── config.yaml                 # 运行时全局配置文件
└── main.py                     # 统一 CLI 启动入口
```

---

## 📊 二、当前已完成与验证能力清单 (Completed & Verified)

以下模块已通过 `pytest tests/` **81 项严格单测验证**，均处于就绪状态：
- ✅ **ADB 与拟人物理输入**：`tests/test_adb_client.py`、`test_touch_humanizer.py` (高斯偏移、贝塞尔曲率、多端口兼容)；
- ✅ **透视单应性变换**：`tests/test_homography_mapper.py` (双向投影自洽、网格瓦片反查误差 < 0.05px)；
- ✅ **视觉模板与 OCR**：`tests/test_vision_engine.py` (色彩容差、特征匹配)；
- ✅ **紧急抢占式救场**：`tests/test_panic_daemon.py`、`test_threat_monitor.py` (红区抢占、防漏怪空投逻辑)；
- ✅ **作业适配与协同推演**：`tests/test_copilot_adapter.py`、`test_copilot_brain.py`；
- ✅ **关卡库与阵容合成**：`tests/test_stage_database.py`、`test_squad_synthesizer.py`；
- ✅ **全域导航状态机**：`tests/test_global_navigator.py` (终端跳转、关卡匹配)；
- ✅ **账号与多实例调度**：`tests/test_account_manager.py`、`test_mission_manager.py`、`test_fleet_orchestrator.py`；
- ✅ **优雅中断与登录鉴权**：`tests/test_abort_controller.py`、`test_auto_authenticator.py`；
- ✅ **仪表盘后端契约**：`tests/test_dashboard.py` (WebSocket 广播、状态流)。

---

## 🚧 三、未完成模块与开发断点 (What is Incomplete / Breakpoints)

**这是在反重力中需要重点推进的核心内容：**

### 1. 【核心断点】实机端到端对战主循环集成 (`tactical/universal_combat_pilot.py`)
- **当前现状**：核心状态判断与干员下场算法已单测，但尚未在实机环境下打通完整的单关全自主战斗（检测开局费用 -> 识别下场格 -> 拖拽干员 -> 调整朝向 -> 监测技能释放 -> 结算点击）。
- **待攻坚工作**：
  - 将 `universal_combat_pilot.py` 与 `core/adb_client.py` 实机截图与手势拖拽深度联调；
  - 针对实机结算掉落物弹窗的“连续快速点击跳过”逻辑进行打磨；
  - 增加战斗超时（如超过 5 分钟未结算）的主动自愈看门狗。

### 2. 【核心断点】多开模拟器实机舰队压测 (`fleet/fleet_orchestrator.py`)
- **当前现状**：SQLite WAL 任务队列与账户互斥租借已就绪，但尚未在 2~4 个真实 MuMu 模拟器实例上并发跑完一整轮任务调度。
- **待攻坚工作**：
  - 测试多实例端口分配（16384, 16416, 16448）实机并发连接与心跳；
  - 优化理智不足时的自动进入睡眠队列机制。

### 3. 【拓展功能】肉鸽全自主决策树深化 (`tactical/roguelike_brain.py`)
- **当前现状**：实现了事件节点树的数据结构与基本选择策略。
- **待攻坚工作**：
  - 接入实机肉鸽地图的 OCR 节点识别（战斗/不期而遇/诡异行商/休整）；
  - 扩充招募券根据当前阵容梯队的自动优选算法。

### 4. 【展示层】Web 遥测监控面板前端联调 (`fleet/dashboard/`)
- **当前现状**：后端 FastAPI + WebSocket (`server.py`) 已就绪，提供状态流推送。
- **待攻坚工作**：
  - 完善 `fleet/dashboard/static/` 前端页面（实时多模拟器缩略图、当前任务甘特图、理智水位监控）。

---

## ⚙️ 四、本地基础设施与模拟器环境规范 (Runtime Environment)

- **开发语言**：Python 3.12 (`C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe`)
- **模拟器标准规格**：
  - 推荐：MuMu 模拟器 12
  - 推荐分辨率：`1280 x 720`（DPI 280）
  - 默认 ADB 地址：`127.0.0.1:16384`（第二开 `127.0.0.1:16416`，夜神/雷电 `127.0.0.1:5555`）
- **测试命令**：
  ```powershell
  # 运行全量 81 个单元测试
  pytest tests/
  ```
- **CLI 运行指令**：
  ```powershell
  # 单关卡战术模式 (实机调试关卡)
  python main.py --mode combat --stage 1-7
  # 导航测试
  python main.py --mode nav --stage 1-7
  # 启动多开舰队调度器
  python main.py --mode fleet
  # 启动 Web 监控看板
  python main.py --mode dashboard --port 8080
  ```

---

## 🎯 五、给反重力智能体的接管提示词 (Antigravity Ignition Prompt)

在反重力 (Google Antigravity IDE) 中打开本工作区后，直接发送以下指令即可无缝继续研发：

> `MC。请读取 HANDOVER.md 和 TASKS.md，全面接管 ASTA (arknights-autopilot) 未完成的项目研发。当前 81 项单元测试已 100% 通过。请先汇报当前断点状态，然后优先推进第一项断点任务：实机端到端对战主循环集成 (tactical/universal_combat_pilot.py 与 core/adb_client.py 联调)。`
