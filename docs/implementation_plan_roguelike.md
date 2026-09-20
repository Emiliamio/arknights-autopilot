# 实施方案：萨卡兹/水月肉鸽深度决策树与干员招募推荐系统 (P2: RoguelikeBrain)

> **项目名称**：ASTA (arknights-autopilot)  
> **唯一作者**：`Emiliamio <mio2110767128@163.com>`  
> **所属模块**：`tactical/roguelike_brain.py`、`tactical/operator_archetypes.py`、`tests/test_roguelike_brain.py`  
> **当前状态**：方案设计中 (Phase 2: Architect Mode) · 等待用户明确批准后方可编码

---

## 🎯 一、需求背景与业务目标

《明日方舟》集成战略（肉鸽 / Roguelike，涵盖 IS2 傀影、IS3 水月、IS4 萨米、IS5 萨卡兹）是全游戏战术深度最高、随机性最强的玩法模块。
当前 `tactical/roguelike_brain.py` 已具备基础的状态机与节点评分框架，但仍存在以下关键断点：
1. **干员招募缺乏博弈推演**：目前仅有固定初始三人组，缺少根据“职业招募券类型 + 当前希望(Hope)预算 + 队伍短板(缺对空/阻挡/治疗) + 玩家实际干员练度”的全局动态优选算法；
2. **多主题特殊机制未深度联动**：IS3 水月（灯火值）、IS4 萨米（坍缩值/抗性）等未纳入节点路线博弈惩罚项；
3. **商店与安全屋决策较单一**：缺少对高价值藏品（如回费/加技力/折射/增伤）与干员精二进阶的背包价值评估。

---

## 🏛️ 二、系统架构设计与核心逻辑

```
[职业招募券输入 (先锋/近卫/狙击/术师/重装/医疗/辅助/特种)]
       │
       ▼
[RecruitmentDrafter 招募优选引擎]
   ├─ 1. 希望预算门禁 (Hope Budget Gate): 6★ (6/3)、5★ (3/2)、4★ (2/1)、3★/临时 (0)
   ├─ 2. 阵容短板缺失度度量 (Squad Deficit Metric): 统计阻挡/对空/法伤/急救指数
   └─ 3. 肉鸽天梯梯度打分 (Tier Score): 幻神核心(玛恩纳/史尔特尔/艾雅法拉) > 战神基石 > 0希望保底(克洛丝/斑点)
       │
       ▼
[最优干员推荐与进阶序列]
```

### 1. 干员招募推荐打分公式
对候选干员 \( O \) 的招募期望得分 \( S(O) \) 定义为：
\[
S(O) = W_{\text{tier}}(O) + W_{\text{need}}(O.\text{class}) \times 25.0 - \text{HopeCost}(O) \times \lambda_{\text{hope}}
\]
- \( W_{\text{tier}} \)：肉鸽专属梯度权重（S级幻神 100分，A级主力 75分，B级过渡 50分，0希望保底 40分）；
- \( W_{\text{need}} \)：当前已招募队伍对该职业的迫切度（若队伍中 0 重装，则重装 need=1.5；已有 2 重装，则 need=0.2）；
- \( \lambda_{\text{hope}} \)：希望紧迫度系数（当剩余 Hope < 4 时大幅惩罚高星干员，优先保底；当 Hope >= 12 时惩罚极小，优先顶级干员）。

### 2. 多主题环境自适应 (Theme Heuristic Routing)
- **IS4 萨米**：监控 `collapse_level`（坍缩指数），若坍缩值超标，大幅提高安全屋与净化节点权重，严禁进未知事件；
- **IS3 水月**：监控 `light_value`（灯火值），灯火低于 50 时进入黑夜减益态，规避突发紧急战斗，优先走商店与休整；
- **IS5 萨卡兹**：思绪整理与抗性优先。

---

## 📝 三、拟变更与新建文件清单

| 操作类型 | 文件路径 | 变更概述 |
| :--- | :--- | :--- |
| **[MODIFY]** | [`tactical/roguelike_brain.py`](file:///d:/arknights-autopilot/tactical/roguelike_brain.py) | 实现 `OperatorRecruitmentDrafter` 招募算法类、扩充 `RoguelikeState`（灯火/坍缩/队伍短板统计）、集成节点深度推演 |
| **[MODIFY]** | [`tactical/operator_archetypes.py`](file:///d:/arknights-autopilot/tactical/operator_archetypes.py) | 扩充肉鸽核心干员梯度（斑点、梓兰、克洛丝、史尔特尔、玛恩纳、澄闪等）元数据 |
| **[MODIFY]** | [`tests/test_roguelike_brain.py`](file:///d:/arknights-autopilot/tests/test_roguelike_brain.py) | 新增 6 项专项单测：招募券评分、Hope不足0费保底、阵容短板加权、坍缩/灯火惩罚、商店购买价值判断 |
| **[MODIFY]** | [`TASKS.md`](file:///d:/arknights-autopilot/TASKS.md) / [`HANDOVER.md`](file:///d:/arknights-autopilot/HANDOVER.md) | 同步更新 P2 研发进度与单测指标 |

---

## 🧪 四、测试与验证计划 (Verification Plan)

### 1. 自动化回归测试 (Automated Pytest)
```powershell
# 1. 运行肉鸽战术专项单元测试套件
python -m pytest tests/test_roguelike_brain.py -v

# 2. 运行全工程 100% 回归测试 (目标: 102 项全部通过，零报错)
python -m pytest tests/ -v
```

### 2. 边界验证 (Edge Cases)
- **极限 Hope 紧缺**：Hope 仅剩 0~2 点时，确保绝不选 6★ 导致抛异常，必须精准下潜推荐 3★ 优质 0-Hope 干员（克洛丝、安塞尔、斑点）；
- **职业严重失衡**：当队伍只有狙击术师且 0 阻挡时，重装与先锋加权提升；
- **极危生命与灯火**：生命值 <= 2 且灯火 < 30 时，确保候选节点绝对避开 EMERGENCY。

---

## ⚠️ 五、用户确认与授权节点 (User Review Required)

> [!IMPORTANT]
> 按照 **Mio-Charter** 与虚拟多智能体状态机规范，本方案当前处于 **Phase 2 (Architect Mode)**。
> **在收到您在聊天窗口中亲手键入的明确批准指令（如“同意/批准/可以/Approve”）前，我将保持代码库只读，绝不动任何现有代码**。
