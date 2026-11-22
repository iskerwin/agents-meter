# agents-meter

[English](README.md) | 简体中文

一个 Python 库，在本机读取 Claude Code、Codex 和 Grok 还剩多少、用了多少：额度窗口及其重置时间、token 用量及估算费用，以及正在运行的会话。只依赖标准库。[agents-usage](https://github.com/iskerwin/agents-usage)（macOS 菜单栏 App）和 [rex-agents](https://github.com/iskerwin/rex-agents)（Rex 侧边面板）的数据都来自它。

```bash
uv add git+https://github.com/iskerwin/agents-meter
```

```python
from agents_meter.snapshot import Snapshots

snapshots = Snapshots(claude_live=True)
snap = snapshots()          # 额度、用量、任务：可直接转 JSON 的 dict
for account in snap["accounts"]:
    print(account["name"], [(w["label"], w["left_percent"]) for w in account["windows"]])
```

| | |
|---|---|
| `Snapshots(claude_live)` | `()` 生成快照，只查询到期该刷新的额度；`(force=True)` 查询全部，各自仍受限流约束。`current(refreshing)` 不等待额度查询。`save` 和 `restored` 保存最后一份快照，供下次启动使用。 |
| `agents_meter.quota` | 额度来源、新鲜度规则，以及给 Claude Code 状态栏脚本用的 `capture_claude_statusline` |
| `agents_meter.logs` | 从各 agent 日志读取 token 记录，`rollup` 按天、模型和项目汇总并计算费用 |
| `agents_meter.tasks` | 终端里正在运行的 agent 会话及其标题 |
| `agents_meter.pricing` | 每百万 token 的公开 API 价格 |

## 多个进程，同一个限流

Claude 和 Grok 的额度接口没有公开文档，而且有限流。每个来源把自己的状态（上次查询时间、需要等多久、上次的结果）存在 `~/.cache/agents-meter/<source>.json`（权限 0600），只有锁住这个文件时才会发起查询。因此本机所有使用 agents-meter 的进程，无论是 App 还是每个标签页里的面板，加起来每分钟只查询一次，并且显示同样的结果。Claude 返回 HTTP 429 后，所有进程的等待时间都会翻倍，最长 15 分钟，或者遵循 `Retry-After`。等待期间保留上次的值，超过 10 分钟标为过期。token 不会写入这些文件。

## 数据来源

| | Claude Code | Codex | Grok |
|---|---|---|---|
| Token、费用、会话 | `~/.claude/projects/**/*.jsonl` | `~/.codex*/sessions`、`archived_sessions` | `~/.grok/sessions/*/*/usage.json` |
| 额度 | statusLine 快照，或开启 `claude_live` 时调用 `/usage` 所用的接口 | `codex app-server`，否则取会话日志中最新的记录 | Grok CLI 调用的用量接口 |

- 日志只读取时间、模型、工作目录、token 数和 agent 写下的会话标题，从不读取对话内容。
- 历史能追溯多远取决于各 agent 保留日志多久；Claude Code 默认会删除旧日志。
- 重复的日志行，以及恢复或分叉会话时重放的记录，只计一次。
- 不计缓存读取时，三者口径一致：Codex 和 Grok 报告的输入 token 包含缓存，这里会先拆开。

### Claude 的额度

Claude Code 的日志里没有额度信息。二选一：

- **statusLine 快照**，不读取任何 token：状态栏脚本把输入传给 `capture_claude_statusline`，它只把 `rate_limits` 保存在 `~/.cache/agents-meter/claude-statusline.json`（权限 0600）。10 分钟后过期，只在 Claude Code 回复时更新。
- **`claude_live`**：读取 Claude Code 保存的 OAuth token（`~/.claude/.credentials.json` 或 macOS 钥匙串，可能会弹窗询问），只保存在内存里，只发送到 `api.anthropic.com`。只有这种方式能拿到按模型区分的每周窗口，例如 Fable 的。

### Grok 的额度

存在 `~/.grok/auth.json`（由 `grok login` 写入）时读取。token 只保存在内存里，只发送到 `cli-chat-proxy.grok.com`，从不写这个文件。token 有效期六小时：过期后由 Grok CLI 自己通过 `grok models` 续期，这不会启动会话。续期失败时保留上次的值并标为过期。

## 规则

- 缺失的值保持缺失，不会显示成 0% 或 100%，也不会把一个窗口的值复制到另一个窗口。
- 已过重置时间的窗口会被丢弃。过期的快照会被标注，并且不会被选为最紧迫的那一项。
- 不会为了刷新用量而启动 agent 会话，不使用手动重置，不触碰任何限额。

**费用是估算，不是账单。** token 按[公开 API 价格](agents_meter/pricing.py)计价，订阅并不按这种方式付费。没有公开价格的模型（例如 `grok-4.7-build`）不计入，长上下文和 fast mode 的加价也不计入。

## 开发

```bash
uv run --group dev pytest
```

## 声明

非官方项目，与 Anthropic、OpenAI 和 xAI 无关。Claude 实时额度和 Grok 额度来自未公开的接口，使用本机保存的 token，随时可能失效；使用前请确认符合各服务的条款。

额度新鲜度规则参考了 [aiusage](https://github.com/sergestack/aiusage)（MIT），没有复制代码。

## 许可证

[MIT](LICENSE)
