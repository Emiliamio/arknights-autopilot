# PRTS Web 全域关卡大屏选关 (含主线 0~17 章与全活动) · 云端作业检索与一键通关实施方案

## 📌 需求升级对齐
根据指挥官的最高明确指示：
1. **主线全章节覆盖至第 17 章**：必须涵盖 `EPISODE 00` 至 `EPISODE 17` 全部普通关、死境/突袭、绝境作战（H系列）；
2. **所有关卡全量纳入 (Zero-Omission All-Stage Coverage)**：
   - 主线 0~17 章全部关卡；
   - 全部常驻插曲与别传活动（从骑兵与猎人、覆潮之下、叙拉古人、孤星，到怀黍离、巴别塔等全部活动）；
   - 全部物资筹备（龙门币 CE-1~6、经验 LS-1~6、红票 AP-1~5、碳素 SK-1~5、技巧 CA-1~5）与芯片搜索（PR-A/B/C/D-1/2）；
3. **支持全域任意关卡代号自由搜索直达 (Universal Free Search)**：
   - 除了海量分类树外，输入框支持输入任何关卡代号（如 `17-21`, `H17-4`, `CW-10`, `BB-9`），直连云端搜索，对所有关卡 100% 永久零遗漏！

---

## 🏛️ 系统架构与全域关卡数据流

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        PRTS Web Cyberpunk HUD (Browser @ 8848)                         │
│  【分类树】                                                                             │
│  ├── 主线全幕：第 0 章 至 第 17 章 (全关卡 + 突袭 + H系列)                               │
│  ├── 活动全录：别传/插曲/新活动全系 (孤星/怀黍离/巴别塔/叙拉古人等)                         │
│  └── 物资芯片：CE/LS/AP/SK/CA/PR 全覆盖                                                 │
│  【自由关卡直达输入框】：可输入任意关卡代码 (支持最新或未录入关卡)                       │
│                                                                                        │
│  点击【🔍 联网检索云端作业】 ➔ 毫秒级展示高赞作业 (作者/赞数/阵容/打法)                │
│  点击【▶ 一键智能下载并拉起通关】                                                      │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTP POST /api/copilot/auto_dispatch
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               Cloud Copilot Hub 引擎 (tactical/copilot_cloud_hub.py)                    │
│  • 直连 MAA 官方接口: GET https://prts.maa.plus/copilot/query?levelKeyword={stage}    │
│  • 智能抓取最高赞/最优解作业 JSON (GET /copilot/get/{id})                               │
│  • 本地缓存至 data/copilots/{stage}_{id}.json                                           │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        TaskExecutor (fleet/task_executor.py)                           │
│  1. 调度 CopilotFuzzyMatcher：依据玩家号已有干员自动平替，动态重算费用时间轴             │
│  2. 轻触【开始行动】进入战场，启动 CopilotBrain 双轨执行                                │
│  3. 实时战场 DP / 击杀 / 步骤 ➔ SSE 投影到大屏 2.5D Canvas                             │
│  4. PanicDaemon 毫秒级三级态势防漏怪保护                                                │
│  5. 战斗胜利自动跳过结算弹窗，工单归档                                                  │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 变更与新建文件清单

### 1. `tactical/stage_database.py` [MODIFY]
**全域全量关卡大字典 (All-Stages Database)**：
- 注册 `EPISODE 00` 至 `EPISODE 17`（包含各章全部普通主线关卡与突袭/H系列绝境关卡）；
- 注册全部 Side Story / Intermezzo 别传插曲代号；
- 注册全部物资与职业芯片关；
- 输出完整的全域关卡分类目录供大屏级联渲染。

### 2. `tactical/copilot_cloud_hub.py` [NEW]
**云端 MAA 作业实时搜索引擎与下载器**：
- `search_cloud_plans(stage_name, page=1, limit=6)`：实时向 `https://prts.maa.plus/copilot/query` 检索作业；
- `fetch_and_cache_plan(plan_id, stage_name)`：下载并解析完整作业 JSON，缓存于 `data/copilots/`；
- `auto_resolve_best_plan(stage_name)`：自动选择最佳高赞作业。

### 3. `fleet/dashboard/server.py` [MODIFY]
**服务端 API 路由**：
- `GET /api/stages/catalog`：返回全量 0~17 章与全活动关卡树；
- `GET /api/copilot/cloud/search?stage=...`：在线搜索作业；
- `POST /api/copilot/cloud/download`：按 ID 下载作业；
- `POST /api/copilot/auto_dispatch`：一键自动检索 + 下载 + 派发拉起执行。

### 4. `fleet/task_executor.py` [MODIFY]
**全域作业任务执行器集成**：
- `MissionType.COPILOT_CLEAR` 自动解析或在线拉取作业；
- 接入 `CopilotFuzzyMatcher` 自动平替 + `CopilotBrain` 双轨执飞；
- 实时战场数据推送到 `TelemetryStore`。

### 5. `fleet/dashboard/static/index.html` & `app.js` [MODIFY]
**大屏任务模态框升级**：
- 级联菜单：主线 (0~17章) / 活动 / 物资分类；
- 自由关卡输入框（输入任意代号即搜）；
- 云端作业检索结果卡片与“一键自动通关”按钮。

### 6. `tests/test_copilot_cloud_hub.py` [NEW]
**云端作业引擎单元测试**：
- 覆盖全域关卡查询、作业解析、缓存与离线回退。

---

## 🧪 验证计划
1. **单测回归**：执行 `pytest tests/test_copilot_cloud_hub.py -v` 及全量测试，确保 100% 绿灯；
2. **端到端大屏验证**：
   - 在大屏测试选择高章节关卡（如 `17-1` 或 `14-21`）及日常经典关卡（如 `1-7`, `7-18`, `H12-4`）；
   - 验证联网检索作业输出及一键下发拉起。
