# ASTA (arknights-autopilot) — 项目规范

> 通用执行规范在 `~/.dsh/AGENTS.md`（§0 为冲突仲裁序），本文件只写**本项目的事实**，不重复抄写宪章。
> 环境事实（Python / 工具版本、技能数量）读 `D:\Antigravity\env-snapshot.json`，不在本文写死。
> 接手前先读 `HANDOVER.md`（架构与断点）与 `TASKS.md`（当前进度）。

## 唯一作者
`Emiliamio <mio2110767128@163.com>`。Git Author / Committer 只用这个身份，不加任何第三方 AI 署名或 `Co-authored-by`。

## 技术栈
- **Python 3.12**（系统 PATH 的 `python`）
- **视觉**：OpenCV 单应性变换（2.5D 网格映射）、RapidOCR（费用 / 击杀实时识别）
- **设备**：ADB 封装 `core/adb_client.py`（直连 / 端口嗅探 / 截图流 / 物理输入）
- **持久化**：SQLite（WAL 模式）
- **测试**：pytest

## 目录职责
| 目录 | 职责 |
|---|---|
| `core/` | ADB 封装、登录自愈、反检测执行底座 |
| `tactical/` | 战术推演：A* 路径、DAG 网络流、干员下场优先级、Panic Daemon 抢占救场 |
| `fleet/` | 多账号调度状态机、排班流水线、战报推送、Web 指挥大屏 |
| `data/` | 关卡 / 干员数据与作业缓存 —— **勿手改，由脚本生成** |
| `docs/` | 架构与部署文档 |
| `tests/` | 单元测试 |
| `tools/` | 辅助脚本 |

## 命令
- 测试：`pytest tests/` —— 当前 132 项（数量随开发变化，以实跑为准）
  依赖实机 ADB 的用例在模拟器离线时会优雅跳过，属预期行为，不是失败。
- 启动：`python main.py`
- 实机对战主循环：`python live_battle_runner.py`

## 约定与禁区
- **凭据**：一律读 `~/.dsh/private.env.md`，**绝不写进本仓库任何文件**（包括本文件、README、配置注释）。
  数据库账号口令只存在于本机私密文件，仓库里连"旧密码"都不要留——旧口令会让人误当成有效凭据。
- **不提交**：`.env`、`data/` 运行产物、`__pycache__`、`.pytest_cache`、日志、`build/`、`dist/`。
- **改动底线**：新增功能同步补测试；提交前 `pytest tests/` 全绿，失败自己修到过，不带病提交。
- **文档不写死数字**：测试数量、版本号、技能数量之类的易变事实，写"以实跑为准"并给命令，不抄一个静态值。
- **本仓库是公开仓库**：不要写入本机绝对私有路径、真实口令、真实姓名等私人信息。