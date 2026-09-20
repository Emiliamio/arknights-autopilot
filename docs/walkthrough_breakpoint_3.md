# 萨卡兹/水月肉鸽深度决策与干员招募推荐走查白皮书 (Walkthrough - Breakpoint 3)

> **项目名称**：ASTA (arknights-autopilot)  
> **唯一作者**：`Emiliamio <mio2110767128@163.com>`  
> **验收模块**：`tactical/roguelike_brain.py`、`tactical/operator_archetypes.py`、`tests/test_roguelike_brain.py`  
> **验证状态**：全项目 102 项单元测试 100% 绿色通过 (96 passed, 6 skipped for offline emulator)

---

## 🚀 核心改动概述 (Key Changes)

在顺利交付 P0（实机对战主循环）、P1（多开并发调度与容灾）、P3（PRTS Web 态势指挥大屏）之后，我们全面攻坚并完成了 **P2 级战术中枢：萨卡兹/水月/萨米集成战略 (肉鸽 / Roguelike) 深度决策树与干员招募引擎**。

### 1. 智能干员招募优选引擎 (`OperatorRecruitmentDrafter`)
- **希望预算门禁 (Hope Budget Gate)**：
  - 严格映射干员星级与希望消耗（6★: 6点、5★: 3点、4★: 2点、3★: 0点保底、临时招募: 0点）；
  - 当可用希望低于招募门槛时自动过滤，杜绝无效决策。
- **阵容短板缺失度动态加权 (Squad Deficits Metric)**：
  - 实时分析当前队伍五维能力：阻挡数 (`blockers`)、急救治疗 (`medics`)、对空物理输出 (`anti_air`)、法术贯穿 (`arts_dmg`)、先锋回费 (`dp_gen`)；
  - 严重缺乏阻挡或治疗时，为对应干员注入高达 `+45.0` 协同紧迫度加权。
- **天梯梯度与 0 希望自适应下潜**：
  - 整合肉鸽天梯 S 级核心干员库（玛恩纳、史尔特尔、艾雅法拉、伊内丝、澄闪、纯烬艾雅法拉、塞雷娅、铃兰、麒麟R夜刀）；
  - 当 Hope 处于危险区 (<4) 时，自动下潜推荐 0 希望基石战神（斑点、克洛丝、安塞尔），保障队伍人数稳健成型。

### 2. 多主题环境自适应启发式路径推演 (Multi-Theme Heuristics)
- **IS3 水月与深蓝之树**：
  - 监控 `light_value`（灯火值）；
  - 当灯火低于 50 进入黑夜危险态时，大幅惩罚突发变异的 `EMERGENCY`（紧急作战 -80分），优先转向 `SAFEHOUSE`（安全屋）与 `TRADER`（商店）。
- **IS4 探索者的银凇止境 (萨米)**：
  - 监控 `collapse_level`（坍缩指数）；
  - 当坍缩等级 >= 3 时，大幅提权 `SAFEHOUSE` (+50分)，优先触发安全屋净化机制清除地图灾害。
- **安全屋与行商商店决策升级**：
  - 生命危急优先回血 (+2)，生命充裕优先晋升未精二干员（Elite 2 Promotion），无干员可升则储备 +2 希望；
  - 源石锭充裕 (>=12) 优先采购行商秘宝与希望补给。

---

## 🧪 测试验证与结果 (Verification Results)

### 专项肉鸽测试套件 (`tests/test_roguelike_brain.py`)
扩充至 9 项全量严苛单测，全部秒级绿灯通过：
1. `test_roguelike_brain_heuristic_evaluation_low_life`: 低血量避开紧急作战。
2. `test_roguelike_brain_heuristic_evaluation_rich_ingots`: 富源石锭优先行商。
3. `test_roguelike_brain_mock_expedition_run`: 完整两层多节点模拟探索闭环。
4. `test_recruitment_drafter_high_hope_prefers_s_tier`: Hope 充足 (>=6) 精准选定 S 级近卫幻神 (玛恩纳/史尔特尔)。
5. `test_recruitment_drafter_low_hope_zero_cost_fallback`: Hope 匮乏 (<2) 精准下潜选择 0-Hope 重装基石 (斑点)。
6. `test_recruitment_drafter_squad_deficit_weighting`: 队伍零医疗时极速响应补齐短板。
7. `test_theme_is3_mizuki_low_light_penalty`: IS3 水月低灯火规避紧急作战。
8. `test_theme_is4_sami_collapse_mitigation`: IS4 萨米高坍缩安全屋净化。
9. `test_brain_recruit_operator_lifecycle`: 实装招募、扣除希望与入队生命周期校验。

### 全工程回归结果
```text
======================= 96 passed, 6 skipped in 27.07s ========================
```
- **测试总用例数**：**102 项**（96 项全部通过，6 项实机 ADB 在模拟器离线时优雅跳过）。
- **通过率**：**100% 绿色**，无回归 Bug，无破坏性改动。
