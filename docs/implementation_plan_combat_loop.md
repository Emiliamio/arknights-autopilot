# ASTA P0 Breakpoint: 实机端到端对战主循环设计规范 (UniversalCombatPilot)
> **项目名称**：ASTA (arknights-autopilot)  
> **唯一作者与架构师**：`Emiliamio <mio2110767128@163.com>`  
> **状态**：已批准并执行 (Approved & Executing)  
> **物理存储基准**：`D:\arknights-autopilot\docs\implementation_plan_combat_loop.md`

---

## 📌 背景与任务目标
本项目 ASTA (Arknights Sovereign Tactical Autopilot) 当前处于攻坚研发期，81 项底层核心单元测试保持 100% 绿色通过。
本次任务攻坚 **P0 优先级首个核心未完成断点**：
联调 `tactical/universal_combat_pilot.py` 与 `core/adb_client.py`，构建具备工业级鲁棒性的实机端到端对战主循环：
**战前加载 ➔ 费用识别 (DP Gate) ➔ 下干员拖拽 (Bezier Deployment) ➔ 技能轮转 (Skill Rotation) ➔ 结算跳过 (Multi-Tap Dismissal) + 看门狗容错**。

---

## 🏛️ 系统架构设计与实施细节

### 1. 战前自适应加载 (Pre-Battle Handshake)
- 检测 `BattleState.PRE_BATTLE`；
- 自动触发蓝色开始行动 `(1700, 920)` / 红色编队确认 `(1655, 780)`；
- 轮询等待加载完成并确认进入 `BattleState.IN_BATTLE`（最长等待 30s）。

### 2. 2x 战斗速度锁定
- 视觉检测 2x 速度图标状态（`vision.is_2x_speed_active(frame)`）；
- 若为 1x 速则触发精确拟人点击 `(1645, 69)` 并验证生效。

### 3. 费用识别与下干员拖拽流水线 (DP Gate & Bezier Deployment)
- 调用 `vision.read_cost(frame)`，集成历史数据平滑容错；
- 支持像素坐标 `(x, y)` 与 2.5D 透视网格坐标 `(col, row)` 自动投影换算；
- 提取可用手牌 `vision.detect_deployable_cards(frame)`；
- 生成“DOWN ➔ 贝塞尔拖拽 ➔ 磁吸微停顿 ➔ 朝向 Flick ➔ UP”原子连续手势；
- 登记阻挡干员至 `panic_daemon`，登记已下场干员至 `self.deployed_operators`。

### 4. 周期性技能轮转引擎 (Skill Rotation Engine)
- 技能巡检时钟（`skill_rotation_interval` 默认为 6.0s）；
- 轮转遍历已部署干员：
  - 点击干员中心 `(tx, ty)` 唤起技能环；
  - 极速跟随点击技能按钮 `(tx, ty - 60)`；
  - 更新最后释放尝试时间戳；
- 暴露 `trigger_all_skills()`（全员决战技爆发模式）。

### 5. 战局紧急漏怪抢占预警 (PanicDaemon Preemption)
- 每 tick 扫描战场威胁，一旦触发 `ThreatLevel.PANIC_LEAK`，立即挂起普通轮转，执行最高优先级空投拦截。

### 6. 实机掉落物与多层结算弹窗连续快速跳过 (`_dismiss_settlement`)
- 状态机驱动的连续拟人点击（中右安全区 `(960, 540)` / `(1100, 540)`）；
- 最多 10~12 次安全跳过，以 `vision.detect_battle_state(frame)` 为守卫；
- 页面脱离结算态并回退到大厅即刻确认成功。

### 7. 全周期超时与异常看门狗
- `AbortController.is_aborted()` 实时中断保障；
- 300s 战斗超时自愈退出机制。
