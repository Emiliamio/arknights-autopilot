# ASTA Route A (Copilot 双轨自愈路线) 完美化全景方案

## 🎯 目标阐述 (Goal Description)
全面攻克 Route A 当前的“作业强依赖、缺干员直接卡死、时轴对齐脆弱、应急手段单一”四大物理软肋，将其打造成一套**“具备智能下位干员替代、费用自适应偏移补偿、时序漂移熔断自愈、三级应急立体防御与全高频关卡作业库”的工业级无翻车执行体系**。

---

## ⚠️ 用户审核重点 (User Review Required)

> [!IMPORTANT]
> **1. 干员替代策略与费用偏移机制**：当客户账号缺少作业指定的特定干员时，系统将依据职能原型树自动推荐最佳替代干员（如玛恩纳 $\rightarrow$ 银灰，塞雷娅 $\rightarrow$ 临光/斑点），并动态调整下场费用的门槛值 ($\Delta \text{Cost}$)。
> **2. 软时轴容差与死锁打破**：当实际战斗中杀敌数与费用无法严格同步（如击杀数滞后但费用已满，或费用稍差但防线吃紧），系统将允许柔性阈值超时强制推进，彻底消灭死锁。
> **3. 生产级作业库扩展**：内置 1-7、LS-6、CE-6 等主流日常关卡经过验证的低配/通用 Copilot 作业文件。

---

## 🏛️ 架构设计与改动方案 (Proposed Changes)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Route A: 完美化 Copilot 双轨自愈体系                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. 智能干员下位替代器 (CopilotFuzzyMatcher)                                │
│     • 8大职业细分子分支特征映射  • 费用差额 ΔCost 动态自动补正  • 练度权重匹配 │
├─────────────────────────────────────────────────────────────────────────────┤
│  2. 时序漂移与死锁熔断器 (DesyncDeadlockBreaker)                            │
│     • 杀敌滞后超时强推 (Soft-Condition)  • 费用溢出提前下场  • 决战技自愈抢开 │
├─────────────────────────────────────────────────────────────────────────────┤
│  3. PanicDaemon 三级立体应急防线 (Multi-Tier Panic Arsenal)                  │
│     • Tier 1: 0.37ms 快活空投截停 (砾/红/夜刀)                              │
│     • Tier 2: 决战技全员爆发强开 (Burst Mode 熔化高威胁怪)                   │
│     • Tier 3: 残血干员战术接力撤退 (退费换防，避免被击杀掉落防线)             │
├─────────────────────────────────────────────────────────────────────────────┤
│  4. 全高频日常作业库资产 (1-7, LS-6, CE-6, PR-X) + PRTS Web HUD 实时可视化   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Component 1: 战术智能层 (Tactical Intelligence Layer)

#### [NEW] [copilot_fuzzy_matcher.py](file:///d:/arknights-autopilot/tactical/copilot_fuzzy_matcher.py)
- **核心职能**：
  - 基于 [operator_archetypes.py](file:///d:/arknights-autopilot/tactical/operator_archetypes.py)，构建各职业分支的阶梯式下位替代映射树（领头羊 $\rightarrow$ 领主 $\rightarrow$ 强攻手；急救重装 $\rightarrow$ 庇护/斑点等）；
  - 输入：CopilotAction 中要求的干员名称、客户拥有的干员库（Roster）；
  - 输出：最佳可用替代干员、费用偏差 $\Delta \text{Cost}$、技能等效映射；
  - 动态修正该步骤的 `min_costs` 门槛值。

#### [MODIFY] [copilot_brain.py](file:///d:/arknights-autopilot/tactical/copilot_brain.py)
- **改进点**：
  - 接入 `CopilotFuzzyMatcher`：在战斗开始前执行预检与干员绑定，无缝支持替代干员；
  - 引入 `DesyncDeadlockBreaker` 柔性条件推演：
    - 若 `current_dp >= min_costs + 5` 且超时等待超过 12 秒，即使击杀数差 1~2 个也强制放行下人，杜绝前锋阵亡；
    - 若击杀数已大幅超前（客户干员练度偏高），达到费用后立即提前下达后续步骤；
  - 接入 PanicDaemon 三级立体联动：遭遇漏怪威胁时，不仅空投快活，更联动在场高台决战技爆发。

#### [MODIFY] [panic_daemon.py](file:///d:/arknights-autopilot/tactical/panic_daemon.py)
- **改进点**：
  - 扩充应急处置策略：
    - `EMERGENCY_DROP`：传统快活/低费干员脸前截停；
    - `EMERGENCY_BURST`：距离蓝门 $\le 1$ 且阻挡满载时，广播触发全员决战技爆发；
    - `EMERGENCY_RETREAT_RELAY`：检测在场阻挡干员血量危急且无法回血时，战术撤退返费并空投替补接力。

---

### Component 2: 关卡资产与数据层 (Data & Copilot Plans Layer)

#### [NEW] [1-7_universal_farm.json](file:///d:/arknights-autopilot/data/copilots/1-7_universal_farm.json)
- 固源岩圣地全通低配/通用作业，支持煌/提丰/山双人挂机或低星阵容。

#### [NEW] [LS-6_universal.json](file:///d:/arknights-autopilot/data/copilots/LS-6_universal.json)
- 作战记录 6（经验本最高阶）通解作业：回费先锋开局 + 医疗覆盖 + 单法/狙击输出。

#### [NEW] [CE-6_universal.json](file:///d:/arknights-autopilot/data/copilots/CE-6_universal.json)
- 龙门币 6（钱本最高阶）通解作业：先锋前压回费 + 重装守门 + 术士群攻。

---

### Component 3: 遥测展示与前端联动 (PRTS Web HUD)

#### [MODIFY] [server.py](file:///d:/arknights-autopilot/fleet/dashboard/server.py)
- **改进点**：
  - `TelemetryStore` 接入 Copilot 实时步进状态、替代干员徽标（如 `玛恩纳 ➔ 银灰 (+8 DP)`）；
  - Web 界面增加作业方案切换与替代干员预览面板；
  - 记录并展示救场哨兵各级别的触发次数与时间轴。

---

## 🧪 验证方案 (Verification Plan)

### 自动化单元与集成测试 (Automated Tests)
1. **干员下位替代与费用补偿测试**：
   - `tests/test_copilot_fuzzy_matcher.py`：测试各种职业缺失时的阶梯式降级匹配与 $\Delta \text{Cost}$ 修正，100% 覆盖。
2. **时轴漂移与柔性熔断测试**：
   - `tests/test_copilot_desync.py`：模拟“击杀数滞后但费用溢出”、“击杀数超前”以及“高危时提前开技能”等 5 种典型漂移场景，确保零死锁。
3. **三级应急防御联动测试**：
   - `tests/test_panic_multi_tier.py`：测试单点空投截停、全员决战技爆发与战术撤退接力。
4. **全套作业 JSON 语法与连贯性校验**：
   - `tests/test_copilot_plans_integrity.py`：对 `data/copilots/` 下所有作业校验坐标有效性、费用递增合理性与职业契约。
5. **全量工程回归**：
   - 执行 `pytest tests/`，确保全部测试套件 100% 绿色通过（预期用例数扩充至 115+ 项）。
