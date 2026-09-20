# 🛡️ ASTA · 极星战术中枢 (Arknights Sovereign Tactical Autopilot)
> **工业级明日方舟全自主空间战术推演 · 拟人反作弊物理执行 · 多账号商业代肝矩阵**  
> **唯一作者与架构师**：`Emiliamio <mio2110767128@163.com>`

---

## 🌌 一、系统全景架构 (System Architecture)

ASTA 彻底终结了传统死板“JSON 脚本抄作业”的脆弱代挂模式，引入空间几何感知、拓扑网络流、毫秒级抢占式救场与无头低功耗多开矩阵：

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        【调度中枢与商业代肝管理层 (Fleet Daemon)】                       │
│    • 多账号调度状态机 (SQLite WAL)  • 体力/活动排班流水线  • 企业微信/Telegram 战报推送与滑块预警 │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ (派发账号与任务指令)
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                        【游戏生命周期分层状态机 (Global HFSM)】                          │
│    登录自愈 -> 签到/基建轮换 -> 自动导航选关 -> 编队匹配 -> 战斗主循环 -> 结算与掉落分析  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ (战斗触发)
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                    【战术推演与实时决策大脑 (Tactical Planner)】                        │
│   ┌─────────────────────────────┐           ┌─────────────────────────────────────┐    │
│   │  A* 最短路径与 DAG 网络流   │           │   干员下场优先级队列与转角射线计算  │    │
│   │  (消灭分叉走廊盲区/咽喉提取)│           │   (费用驱动 / 覆盖面最大化评分)     │    │
│   └──────────────┬──────────────┘           └──────────────────┬──────────────────┘    │
│                  │                                             │                       │
│                  └──────────────────────┬──────────────────────┘                       │
│                                         │ (战术指令流)                                 │
│                     ┌───────────────────▼───────────────────┐                          │
│                     │ 动态威胁监护与即兴救场 (Panic Daemon)  │                          │
│                     │ (漏怪自动骑脸空投 / 0.37ms 抢占截停)  │                          │
│                     └───────────────────────────────────────┘                          │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ (下干员 / 开技能 / 撤退)
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                        【视觉感知与状态追踪层 (Vision & OCR)】                          │
│    • 2.5D 网格单应性变换 (Homography)  • RapidOCR 费用与击杀实时推理 (字偶距修复)      │
│    • 手牌卡片饱和度/就绪检测           • 170ms 零拷贝内存直读 (Raw Framebuffer)        │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ (归一化指令: Click / Drag)
┌───────────────────────────────────────────▼────────────────────────────────────────────┐
│                    【拟人反作弊物理执行底座 (Anti-Detection I/O)】                      │
│    • Android 12 原生 motionevent 复合事件流 • 3 阶贝塞尔非线性拟人微震颤滑动轨迹       │
│    • 2D 高斯散布 (<=8.0px 严格防越界)      • 适配 MuMu 12 多开 (127.0.0.1:16384+)      │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ 二、四大核心硬核算法突破

### 1. 2.5D 透视单应性变换 (Homography Mapping)
明日方舟战场采用斜向近大远小的 2.5D 梯形透视投影。ASTA 通过 $3 \times 3$ 单应性矩阵 $H$ 建立双向无损投影：
$$\begin{bmatrix} x_{screen} \\ y_{screen} \\ 1 \end{bmatrix} \sim H \cdot \begin{bmatrix} c_{grid} \\ r_{grid} \\ 1 \end{bmatrix}$$
- **正向计算**：逻辑网格中心 $(c + 0.5, r + 0.5)$ 映射至物理像素 $(x, y)$；
- **逆向反查**：屏幕任意触控点反查所属网格瓦片，**闭环误差 $< 0.05$ 像素**；
- **自适应缩放**：支持 $1080\text{P} \leftrightarrow 720\text{P}$ 相似矩阵实时变换，换分辨率零重算。

### 2. A* 最短路径与 $O(V+E)$ DAG 网络流（消灭分叉盲区）
针对对称双走廊分叉拓扑，传统单路径 A* 存在漏防下半区的致命缺陷。ASTA 引入 Brandes 介数网络流算法：
- 构建分层有向无环图（Layered DAG）；
- 前向 DP + 后向 DP 求解每个节点的流量概率：
  $$Flow(u) = \frac{\sigma_{start}(u) \cdot \sigma_{goal}(u)}{\sigma_{total}}$$
- 自动提取流量为 100% 的地面格为 **Primary Choke（黄金堵门点）**，并输出输出/医疗双角色高台阵位。

### 3. 动态威胁监护与 0.5s 即兴救场机制 (Panic Fallback Daemon)
- 每 100ms 扫描战场红点，当怪物距离蓝门 $\le 2$ 且前方阻挡干员阵亡或被撤除时：
- AI 毫秒级打断常规循环，检索手牌就绪的快活干员（如德克萨斯/红/傀影）或低费近战；
- **0.37ms 内部计算延迟**生成截停手势，空投至敌军前方 1 格完成面朝敌人的暴力截停！

### 4. 单事务原子化连续手势 (Atomic Continuous Motionevent)
彻底告别传统双段触控导致的“部署撤回手牌”引擎冲突：
$$\text{按下手牌} \xrightarrow{\text{3阶贝塞尔曲线}} \text{目标网格停顿 80ms} \xrightarrow{\text{方向甩动}} \text{释放锁定部署}$$
全过程在一个 Shell 复合事务中执行，耗时仅 338ms，与真人手指触控手感完全一致。

---

## 💼 三、商业代肝多账号调度矩阵 (Fleet Daemon)

### 1. 账号元数据库 (`data/accounts.db`)
采用 SQLite WAL 模式，支持高并发读写与服务等级优先级调度：
- **`SVIP` (保姆级代肝)**：最高调度特权，全自动清体力 + 1-7刷石 + 基建轮换；
- **`MONTHLY` (月卡托管)**：每日定时清空体力；
- **`DAILY` (散客零单)**：单次执行后自动休眠。

### 2. MuMu 12 极限低功耗多开压榨 (8~12 开并发)
- **锁帧 15 FPS**：`dynamic_low_frame_rate_limit = 15`；
- **分辨率压榨至 720P**：单开内存占用从 2.2GB 暴降至 **550MB**；
- **设备指纹隔离**：每个实例独立绑定唯一 IMEI 与 MAC 地址，彻底免疫平台风控。

### 3. 全渠道战报推送与安全告警
- **每日清体力战报卡片**：通关次数、体力消耗、战利品掉落自动推送至企业微信/钉钉/Telegram；
- **P0 级滑块预警**：一旦识别到人机验证滑块，毫秒级熔断停机并携带截图向管理员手机推送报警。

---

## 🛠️ 四、终端统一中枢 CLI 使用指南

项目根目录下提供统一调度入口 `main.py`：

```bash
# 1. 巡检系统健康度、已录入账号与本地 MuMu 模拟器实例
python main.py status

# 2. 运行工业级 102 项自动化全量回归测试 (100% Pass)
python main.py test

# 3. 启动 PRTS 战术态势指挥大屏 (HTTP + SSE + REST, 浏览器直达 http://127.0.0.1:8848)
python main.py dashboard --port 8848

# 4. 启动商业多账号并发代肝调度中枢 (多开槽位动态分配与理智休眠轮转)
python main.py daemon --cycles 1

# 5. 启动萨卡兹/萨米肉鸽全自主探索运行 (is4 / is3 / is2 / is5)
python main.py roguelike --theme is4 --floors 3

# 6. 为指定关卡一键智能合成 12 人黄金战队阵容
python main.py squad --stage 1-7

# 7. 全局紧急安全停机 (广播 AbortController 截停全部 Worker)
python main.py stop
```

---

## 📊 五、全套自动化测试指标 (123 项 100% PASS)

```text
======================= 117 passed, 6 skipped in 29.60s =======================
- tests/test_account_manager.py         [5 tests]  (账号 CRUD / WAL 互斥检出 / 状态机)
- tests/test_adb_client.py              [6 tests]  (ADB 直连 / 170ms 截屏 / 离线优雅嗅探)
- tests/test_choke_point_analyzer.py    [6 tests]  (A* 寻路 / DAG 网络流 / 咽喉高台推演)
- tests/test_combat_brain.py            [4 tests]  (部署蓝图 / 2x速自动切换 / 胜利结算)
- tests/test_copilot_adapter.py         [2 tests]  (MAA 作业协议解析与双轨序列化)
- tests/test_copilot_brain.py           [3 tests]  (作业序列执行 / 漏怪抢占恢复 / 动作消解)
- tests/test_copilot_desync.py          [6 tests]  (软条件仲裁 / 费用溢出击穿 / 威胁紧急响应)
- tests/test_copilot_fuzzy_matcher.py   [6 tests]  (干员平替优先链 / 启发式打分 / 费用差额自补偿)
- tests/test_copilot_plans_integrity.py [5 tests]  (1-7/CE-6/LS-6 方案完整性 / 动态平替校验)
- tests/test_dashboard.py               [3 tests]  (PRTS 大屏端点 / SSE 实时流 / 全套 REST CRUD)
- tests/test_fleet_orchestrator.py      [2 tests]  (多开调度器拉起与全局紧急停机)
- tests/test_fleet_stress_concurrency.py [5 tests] (多VM并行分发 / 同槽位换号 / 理智耗尽休眠 / 急停压测)
- tests/test_global_navigator.py        [5 tests]  (主页/终端/关卡节点识别 / 章节导航)
- tests/test_homography_mapper.py       [6 tests]  (单应性正反映射 / 动态缩放 / 边界校验)
- tests/test_mission_manager.py         [3 tests]  (任务队列 CRUD / FIFO 排班 / 纳秒高熵 ID)
- tests/test_multi_instance_runner.py   [1 test ]  (多实例单周期代肝闭环)
- tests/test_notifier.py                [3 tests]  (每日战报 Markdown 格式化 / 验证码告警)
- tests/test_panic_daemon.py            [3 tests]  (阻挡器注销 / 应急手牌 / 冷却抑制)
- tests/test_panic_multi_tier.py        [4 tests]  (空投快活 / 决战技全员爆发 / 战术接力换防)
- tests/test_roguelike_brain.py         [9 tests]  (Hope预算门禁 / 阵容短板加权 / 多主题自适应)
- tests/test_squad_synthesizer.py       [3 tests]  (阵容配比配额 / 12人兜底 / 对空克制推导)
- tests/test_stage_database.py          [2 tests]  (关卡章节拓扑覆盖 / 物资芯片关元数据)
- tests/test_threat_monitor.py          [5 tests]  (红点聚类 / 距离积分 / 漏怪判定)
- tests/test_touch_humanizer.py         [5 tests]  (高斯散布 <=8.0px / 非线性时间流)
- tests/test_universal_combat_pilot.py  [9 tests]  (实战主循环 / 2x速 / 贝塞尔手势 / 动态结算跳过)
- tests/test_vision_engine.py           [8 tests]  (RapidOCR 费用 / 字偶距修复 / 状态分类)
```

---
*版权所有 © 2026 Emiliamio <mio2110767128@163.com>. 保留所有权利。*