# ASTA P0 Breakpoint 1 攻坚完成报告: 实机端到端对战主循环

> **状态**：✅ 100% 攻坚完成并通过回归测试  
> **唯一作者与架构师**：`Emiliamio <mio2110767128@163.com>`  
> **物理存储路径**：`D:\arknights-autopilot\docs\walkthrough_breakpoint_1.md`  
> **测试健康度**：`90 / 90` 单元测试全绿通过 (`pytest tests/`，耗时 58.55s)

---

## 🎯 攻坚目标完成情况

成功联调 [`tactical/universal_combat_pilot.py`](file:///d:/arknights-autopilot/tactical/universal_combat_pilot.py) 与 [`core/adb_client.py`](file:///d:/arknights-autopilot/core/adb_client.py)，补齐实机端到端对战的核心能力断点，实现以下六大技术闭环：

1. **战前自适应握手 (`enter_and_wait_battlefield`)**：
   - 自动探测 `BattleState.PRE_BATTLE`；
   - 区分关卡详情页（蓝色开始）与编队确认页（红色开始），自动点击并轮询等待进入 `BattleState.IN_BATTLE`。
2. **2x 战斗速度自适应锁定 (`ensure_speed_2x`)**：
   - 视觉感知 2x 速度图标状态，若未开启则触发精确拟人点击 `(1645, 69)`。
3. **费用门禁与 2.5D 透视坐标投影转换 (`deploy_step`)**：
   - 结合 OCR 读取 DP 与手牌可用状态；
   - 支持屏幕像素坐标 `(x, y)` 与 2.5D 网格坐标 `(col, row)` 通过 `HomographyMapper` 自动投影换算；
   - 执行原子连续贝塞尔手势（DOWN ➔ 贝塞尔拖拽 ➔ 磁吸微停顿 ➔ 朝向 Flick ➔ UP）；
   - 登记阻挡干员至 `panic_daemon`，登记已下场干员至 `self.deployed_operators`。
4. **周期性技能轮转与全员爆发引擎 (`cycle_skills` & `trigger_all_skills`)**：
   - 巡检时钟（默认 6.0s 间隔），遍历已部署干员；
   - 执行“点击干员中心 `(tx, ty)` ➔ 极速点击技能按钮 `(tx, ty - 60)`”动作序列；
   - 支持 `trigger_all_skills()` 一键决战技全开。
5. **战局漏怪毫秒级抢占拦截 (`ThreatLevel.PANIC_LEAK`)**：
   - 实时监听战场威胁，一旦发生漏怪风险，挂起普通轮转，优先触发即兴空投拦截。
6. **多层结算跳过状态机 (`dismiss_settlement`)**：
   - 废除固定 2 次点击的死板逻辑；
   - 采用多轮（最多 12 次）在中右安全区 `(960, 540)` / `(1120, 540)` 的连续拟人点击；
   - 以 `vision.detect_battle_state(frame)` 为守卫，跳过结算动画、经验结算、掉落物资、账号升级等各层弹窗，直至状态不再为 `VICTORY`/`DEFEAT` 自动退出。
7. **全周期超时与全局急停看门狗**：
   - 深度集成 `AbortController.is_aborted()`；
   - 300s 超时主动自愈与标记。

---

## 📁 代码变更与文件清单

| 文件路径 | 变更类型 | 说明 |
| :--- | :--- | :--- |
| [`tactical/universal_combat_pilot.py`](file:///d:/arknights-autopilot/tactical/universal_combat_pilot.py) | **MODIFY** | 升级通用实战驾驶主脑，实现战前握手、费用门禁、贝塞尔下场、技能轮转、多层结算跳过与看门狗 |
| [`tests/test_universal_combat_pilot.py`](file:///d:/arknights-autopilot/tests/test_universal_combat_pilot.py) | **NEW** | 新建 9 项专项单元测试套件，覆盖所有主循环分支 |
| [`docs/implementation_plan_combat_loop.md`](file:///d:/arknights-autopilot/docs/implementation_plan_combat_loop.md) | **NEW** | 将完整设计规范与实施方案持久化至 D 盘项目文档库 |
| [`TASKS.md`](file:///d:/arknights-autopilot/TASKS.md) | **MODIFY** | 更新健康度至 90/90，勾选完成 Task 1 |
| [`HANDOVER.md`](file:///d:/arknights-autopilot/HANDOVER.md) | **MODIFY** | 更新健康度至 90/90，标记 Breakpoint 1 攻坚完成 |

---

## 🧪 自动化测试验证结果

全量测试套件执行：
```powershell
pytest tests/
```
```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\arknights-autopilot
plugins: cov-7.1.0
collected 90 items

tests\test_abort_controller.py ..                                        [  2%]
tests\test_account_manager.py .....                                      [  7%]
tests\test_adb_client.py ......                                          [ 14%]
tests\test_auto_authenticator.py ..                                      [ 16%]
tests\test_choke_point_analyzer.py ......                                [ 23%]
tests\test_combat_brain.py ....                                          [ 27%]
tests\test_copilot_adapter.py ..                                         [ 30%]
tests\test_copilot_brain.py ...                                          [ 33%]
tests\test_dashboard.py ..                                               [ 35%]
tests\test_fleet_orchestrator.py ..                                      [ 37%]
tests\test_global_navigator.py .....                                     [ 43%]
tests\test_homography_mapper.py ......                                   [ 50%]
tests\test_mission_manager.py ...                                        [ 53%]
tests\test_multi_instance_runner.py .                                    [ 54%]
tests\test_notifier.py ...                                               [ 57%]
tests\test_panic_daemon.py ...                                           [ 61%]
tests\test_roguelike_brain.py ...                                        [ 64%]
tests\test_squad_synthesizer.py ...                                      [ 67%]
tests\test_stage_database.py ..                                          [ 70%]
tests\test_threat_monitor.py .....                                       [ 75%]
tests\test_touch_humanizer.py .....                                      [ 81%]
tests\test_universal_combat_pilot.py .........                           [ 91%]
tests\test_vision_engine.py ........                                     [100%]

============================= 90 passed in 58.55s =============================
```
- 既有 81 项单元测试持续保持 100% 绿色通过，零破坏现有逻辑；
- 新增 9 项主循环测试全数通过，系统总测试用例提升至 **90 项**。
