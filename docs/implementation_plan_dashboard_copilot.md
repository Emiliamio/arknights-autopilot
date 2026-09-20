# PRTS Web 大屏作业配置与工单拉起执行实施方案 (Implementation Plan)

## 📌 背景与目标
用户提出：“在大屏配置关卡作业，然后执行工单拉起怎么样？”
这是一个极具生产力与视觉体验的优秀设计。目前 ASTA 已将 **Route A (MAA Copilot 双轨仲裁中枢)** 打磨至成熟，但 Web 大屏 (`http://127.0.0.1:8848`) 此前仅支持章节巡航与肉鸽工单，未向用户暴露“可视选作业 ➔ 下发工单 ➔ 实时观战通关”的完整端到端链路。

本方案旨在实现：
1. **大屏端点赋能**：新增 `/api/copilots` 接口，自动扫描并结构化返回 `data/copilots/` 下所有作业元数据（标题、关卡代号、所需干员、步骤数）；
2. **任务引擎升级**：在 `MissionType` 中正式确立 `COPILOT_CLEAR`（Route A 作业智能通关），在 `TaskExecutor` 中深度连通 `CopilotBrain`、`CopilotFuzzyMatcher` 与 `TelemetryStore`，作战时将每一步部署实时广播至大屏；
3. **Web HUD 前端交互**：在大屏“布置战术任务”模态框中新增 `Route A 作业智能通关 (COPILOT_CLEAR)` 选项与“选择作业协议”下拉框，支持关卡与作业联动，点击“立即启动”即可全自动下发并在模拟器中拉起执行！

---

## 🏛️ 架构设计与数据流图

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        PRTS Web Cyberpunk HUD (Browser @ 8848)                         │
│   1. 打开【布置战术任务】模态框 ➔ 选择【Route A 作业智能通关】                                 │
│   2. 下拉框动态加载 /api/copilots 列表 (1-7 固源岩 / LS-6 经验 / CE-6 龙门币 / 萧然Q 等)         │
│   3. 点击【＋ 建立工单】并点击【▶ 立即执行】                                                │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTP POST /api/missions + POST /api/missions/run
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                  Dashboard Server (fleet/dashboard/server.py)                          │
│   • 录入 COPILOT_CLEAR 工单 (含 target_stage 与 copilot_plan)                           │
│   • 派发至 FleetOrchestrator 并拉起独立 TaskExecutor 线程                                │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      TaskExecutor (fleet/task_executor.py)                             │
│   1. 校验并连接目标模拟器 (ADBClient)                                                    │
│   2. 加载作业 (CopilotAdapter.load_file) 与当前账号干员库                                  │
│   3. 自动触发干员平替与费用自补偿 (CopilotFuzzyMatcher)                                     │
│   4. 点按【开始行动】进入战场                                                          │
│   5. 启动 CopilotBrain 双轨执行循环：                                                   │
│      - 实时回传 DP / 击杀数 / 动作步骤至 TelemetryStore ➔ SSE 推送至大屏视窗                │
│      - 若漏怪触发 PanicDaemon 毫秒级抢占 ➔ 大屏实时标红报警                               │
│      - 胜利后自动跳过结算弹窗 ➔ 工单标记为 COMPLETED                                    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 变更文件清单

### 1. `fleet/mission_manager.py` [MODIFY]
- 在 `MissionType` 枚举中新增 `COPILOT_CLEAR = "COPILOT_CLEAR"`，规范化任务类型定义。

### 2. `fleet/dashboard/server.py` [MODIFY]
- 新增 `_handle_api_copilots(self)`：
  - 扫描 `data/copilots/*.json`；
  - 返回各作业的 `stage_name`、`title`、`details`、`operators`、`actions_count`、`filename`；
- 在路由派发中增加 `GET /api/copilots`。

### 3. `fleet/task_executor.py` [MODIFY]
- 在 `execute_mission` 中处理 `MissionType.COPILOT_CLEAR`（以及附带 `copilot_plan` 的 `SANITY_FARM`）：
  - 自动根据配置定位作业文件路径；
  - 获取账号干员资产名册；
  - 实例化 `CopilotBrain`（自动挂载 `CopilotFuzzyMatcher` 实施平替与费用补偿）；
  - 执行对战循环并将每个 tick 的 `dp`、`kill_count`、`action_taken` 写入 `self.telemetry_store`，同步更新工单进度；
  - 战斗结算后标记 `COMPLETED`。

### 4. `fleet/dashboard/static/index.html` [MODIFY]
- 在 `missionModal` 的任务类型下拉框中新增 `<option value="COPILOT_CLEAR">Route A 作业智能通关 (COPILOT_CLEAR)</option>`；
- 新增作业选择器表单项 `#copilotPlanField`（含作业下拉列表与作业详情预览卡片）。

### 5. `fleet/dashboard/static/app.js` [MODIFY]
- 在页面初始化时调用 `/api/copilots` 加载作业列表；
- 在 `toggleMissionTypeFields()` 中处理 `COPILOT_CLEAR` 类型的表单显隐；
- 在 `submitMission()` 时打包 `copilot_plan` 至请求体；
- 接收 SSE 战场流，实时高亮当前作业步骤。

### 6. `tests/test_dashboard.py` [MODIFY]
- 扩充测试用例：覆盖 `/api/copilots` 接口响应与 `COPILOT_CLEAR` 工单流转测试。

---

## 🧪 验证计划

### 自动化测试
- 运行 `pytest tests/test_dashboard.py -v` 验证新端点与工单生成；
- 运行 `pytest tests/` 确保全部测试（123+ 项）持续 100% 绿灯。

### 大屏端到端体验验证
- 用户打开浏览器 `http://127.0.0.1:8848`；
- 点击【布置战术任务】；
- 选择【Route A 作业智能通关】；
- 看到下拉框自动列出 `1-7 固源岩`、`LS-6 经验`、`CE-6 龙门币` 等作业；
- 选择一个作业，点击【建立工单】；
- 工单出现在大屏工单列表中，点击【▶ 立即执行】即可调度拉起执行！
