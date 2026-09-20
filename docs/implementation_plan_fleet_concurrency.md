# ASTA P1 Task 2: 多开模拟器实机舰队并发压测与调度实施方案
> **项目名称**：ASTA (arknights-autopilot)  
> **唯一作者与架构师**：`Emiliamio <mio2110767128@163.com>`  
> **状态**：方案待审阅批准 (Pending Approval)  
> **物理存储基准**：`D:\arknights-autopilot\docs\implementation_plan_fleet_concurrency.md`

---

## 📌 背景与任务目标
在完成 P0 实机端到端对战主循环后，当前核心重点推进 **P1 优先级断点**：
**多开模拟器集群实机并发联调与压测 (`fleet/fleet_orchestrator.py` 与 `fleet/multi_instance_runner.py`)**。
打通多实例端口分配（16384 与 16416）、多账号交替执行租借、账号登出切换、以及理智耗尽自动休眠队列调度，实现真正的商业级多开并发代肝。

---

## 🏛️ 当前现状与技术断点剖析

1. **多实例槽位发现与端口分配受限**：
   - 目前 `_refresh_vm_slots()` 在 MuMuManager 不可用或仅检测到单实例时，只回退了单个 VM 0 槽位，限制了多开并发调度；
   - 需扩展为依据 `max_workers` 动态构建多槽位拓扑（VM 0 ➔ 16384, VM 1 ➔ 16416, VM 2 ➔ 16448...），支持跨实例并发调度。
2. **账号登出与交替执行互斥切换 (Account Rotation)**：
   - 同一个 VM 实例被释放后，下一个工单可能属于不同客户账号；
   - 需确保同一个 VM 槽位在接管新账号时，能够可靠探测旧账号会话并触发 `_perform_logout_switch()` 安全切换，防止账号串号；
   - 账号并发租借锁与 SQLite WAL 必须在多线程高并发抢占下 100% 杜绝双重检出。
3. **理智不足自动让渡与休眠调度 (Sanity Depletion & Sleep Queue)**：
   - 当账号体力刷空（标记为 `SANITY_EMPTY`）时，当前工单需优雅完结并记录理智恢复预期时钟；
   - VM 槽位必须秒级释放给其他队列中有体力的账号（SVIP ➔ MONTHLY ➔ DAILY）；
   - 处于 `SANITY_EMPTY` 的账号在理智恢复前不得被重复检出占用算力。
4. **全链路并发压测与应急中断看门狗**：
   - 必须通过多线程并发压力测试，模拟 2~4 个实例同时拉起、交替跑单、理智耗尽休眠与 `stop_all` 广播急停，保障 100% 线程安全无死锁。

---

## 🛠️ 详细实施方案

### 一、`fleet/fleet_orchestrator.py` 增强
1. **多槽位动态拓扑自适应**：
   - 优化 `_refresh_vm_slots()`：当硬件管理器返回实例不足时，根据 `max_workers` 自动建立并保障至少 2~4 个标准 MuMu 端口槽位（16384, 16416, 16448, 16480）；
   - 为每个槽位增加 `last_used_account`、`session_active` 状态跟踪。
2. **账号切换与排他性调度机制**：
   - 在 `_run_slot_worker` 中增加会话一致性校验：若槽位当前绑定的账号与上一次执行账号不同，通知 `AutoAuthenticator` 执行登出与新凭据输入；
   - 账号检出时严格校验 `current_status != 'SANITY_EMPTY'`，无体力账号自动跳过；
3. **理智耗尽与休眠让渡机制**：
   - 当任务报告体力耗尽或任务完成时，原子更新账号状态为 `SANITY_EMPTY`，立即清理槽位占用，触发 `dispatch_pending_missions()` 自动将空闲算力分配给排队的下一个有效账号；
4. **遥测大屏状态流增强**：
   - 在 `get_fleet_telemetry()` 中输出每个槽位的实时端口、当前活跃账号、运行阶段与实时并发数。

### 二、`fleet/task_executor.py` 配合完善
- 在 `execute_mission` 中完善对 `SANITY_EMPTY` 异常流的判定；
- 任务执行完毕后规范记录消耗的理智与掉落统计。

### 三、测试套件建设 (`tests/test_fleet_stress_concurrency.py`)
- 新建专项并发压测套件：
  1. `test_multi_vm_parallel_dispatch`：验证 2 个 VM 槽位（16384 & 16416）在多线程下并发接单执行，互不阻塞；
  2. `test_account_rotation_on_same_slot`：验证同一槽位上连续执行不同账号时，会话状态的安全轮转；
  3. `test_sanity_depletion_auto_yield`：验证账号体力耗尽后自动让出槽位并调度休眠，下一优先级账号无缝接盘；
  4. `test_concurrent_emergency_stop_all`：验证在多线程并发执行期间触发 `stop_all`，所有工作线程秒级响应并安全中断。

---

## 📁 涉及变动文件清单

### [MODIFY] [`fleet/fleet_orchestrator.py`](file:///d:/arknights-autopilot/fleet/fleet_orchestrator.py)
- 增强动态多槽位发现、账号会话轮转检测、理智休眠队列让渡与遥测统计。

### [MODIFY] [`fleet/task_executor.py`](file:///d:/arknights-autopilot/fleet/task_executor.py)
- 增强多开实例上下文绑定与理智耗尽状态回传。

### [NEW] [`tests/test_fleet_stress_concurrency.py`](file:///d:/arknights-autopilot/tests/test_fleet_stress_concurrency.py)
- 新建多开舰队高并发压测测试套件。

### [NEW] [`docs/implementation_plan_fleet_concurrency.md`](file:///d:/arknights-autopilot/docs/implementation_plan_fleet_concurrency.md)
- 将完整方案持久化至 D 盘项目文档库。

---

## 🧪 验证计划 (Verification Plan)

### 自动化测试回归
1. 运行新建的并发压测套件：
   ```powershell
   pytest tests/test_fleet_stress_concurrency.py -v
   ```
2. 运行全项目 90+ 项全量单元测试回归，确保 100% 绿色全通：
   ```powershell
   pytest tests/
   ```
