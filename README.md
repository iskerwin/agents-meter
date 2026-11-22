# agents-meter

English | [简体中文](README.zh-CN.md)

A Python library that reads, from this machine, what Claude Code, Codex and Grok have left and have used: quota windows and their resets, tokens and their estimated cost, and the sessions running. Standard library only. It is what [agents-usage](https://github.com/iskerwin/agents-usage) (a macOS menu bar app) and [rex-agents](https://github.com/iskerwin/rex-agents) (a Rex side panel) draw from.

```bash
uv add git+https://github.com/iskerwin/agents-meter
```

```python
from agents_meter.snapshot import Snapshots

snapshots = Snapshots(claude_live=True)
snap = snapshots()          # quotas, usage, tasks: a JSON-ready dict
for account in snap["accounts"]:
    print(account["name"], [(w["label"], w["left_percent"]) for w in account["windows"]])
```

| | |
|---|---|
| `Snapshots(claude_live)` | `()` makes a snapshot, querying the quotas that are due; `(force=True)` queries all, each within its rate limit. `current(refreshing)` doesn't wait for quotas. `save` and `restored` keep the last snapshot for the next start. |
| `agents_meter.quota` | The quota sources, the freshness rules, and `capture_claude_statusline`, for a Claude Code status line script |
| `agents_meter.logs` | Token records from the agents' logs, and `rollup` by day, model and project, with cost |
| `agents_meter.tasks` | The agent sessions running in terminals, with their titles |
| `agents_meter.pricing` | Public API prices per million tokens |

## Many processes, one rate limit

Claude's and Grok's quota endpoints are undocumented and rate-limited. Each source keeps its state, meaning when it was last asked, how long to wait and its last answer, in `~/.cache/agents-meter/<source>.json` (mode 0600), and it is asked only while that file is locked. So every process on the machine using agents-meter, an app and a panel in every tab alike, makes one call a minute between them, and all of them show the same answer. After an HTTP 429 from Claude the wait doubles, up to 15 minutes, or follows `Retry-After`, for every process. Meanwhile the last values stay, marked stale after 10 minutes. Tokens are never written there.

## Where the data comes from

| | Claude Code | Codex | Grok |
|---|---|---|---|
| Tokens, cost, sessions | `~/.claude/projects/**/*.jsonl` | `~/.codex*/sessions`, `archived_sessions` | `~/.grok/sessions/*/*/usage.json` |
| Quota | The statusLine snapshot, or with `claude_live` the endpoint `/usage` calls | `codex app-server`, else the newest record in the session logs | The usage endpoint the Grok CLI calls |

- Logs are read for times, models, working directories, token counts and the session titles the agents write, never for what was said.
- History reaches as far back as each agent keeps its logs; Claude Code removes old ones by default.
- Repeated log lines and the records a resumed or forked session replays are counted once.
- Without cache reads, the three are counted alike: the input tokens Codex and Grok report include the cache, and are split here first.

### Claude's quota

Claude Code's logs hold no quota. Either:

- **The statusLine snapshot**, which reads no token: a status line script passes its input to `capture_claude_statusline`, which keeps only `rate_limits` in `~/.cache/agents-meter/claude-statusline.json` (mode 0600). It goes stale after 10 minutes and is only updated when Claude Code replies.
- **`claude_live`**: the OAuth token Claude Code stored (`~/.claude/.credentials.json` or the macOS keychain, which may ask) is kept in memory and sent only to `api.anthropic.com`. Only this gives the per-model weekly windows, such as Fable's.

### Grok's quota

Read when `~/.grok/auth.json` exists (written by `grok login`). The token is kept in memory and sent only to `cli-chat-proxy.grok.com`; the file is never written. Tokens last six hours: an expired one is renewed by the Grok CLI itself through `grok models`, which starts no session. If that fails, the last values stay and are marked stale.

## Rules

- A missing value stays missing. It is never shown as 0% or 100%, and one window is never copied into another.
- A window past its reset is dropped. A stale snapshot is labelled and never picked as the most urgent.
- No agent session is started to refresh usage, no manual reset is used, and no limit is touched.

**Cost is an estimate, not a bill.** Tokens are priced at [public API rates](agents_meter/pricing.py); subscriptions don't pay that way. Models without a public price (such as `grok-4.7-build`) aren't counted, nor are long-context and fast-mode surcharges.

## Develop

```bash
uv run --group dev pytest
```

## Notice

Unofficial, and not affiliated with Anthropic, OpenAI or xAI. The Claude live quota and the Grok quota come from undocumented endpoints with the tokens stored on this machine, and may stop working at any time; check that this fits each service's terms before you use it.

The quota freshness rules follow [aiusage](https://github.com/sergestack/aiusage) (MIT); no code was copied.

## License

[MIT](LICENSE)
