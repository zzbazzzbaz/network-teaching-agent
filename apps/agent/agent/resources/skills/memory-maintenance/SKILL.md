---
name: memory-maintenance
description: 维护学生的跨会话记忆。首次使用、章节完成、quiz 结束、学生明确自述偏好/背景，或要求忘记时，按固定结构读写 /memory/AGENTS.md、profile.md、learning.md、sessions/YYYY-MM.md。需要创建、更新、压缩或修复学生记忆时使用。
metadata:
  scope: user-memory
  version: v1
---

# 学生记忆维护

这个 skill 负责维护用户级、跨 thread 的学生记忆。记忆不是聊天记录，而是让下一次教学能接着上次继续的“教学状态”。

## 1. 何时使用

使用：

- 第一次为该学生创建记忆；
- 完成一章、一个阶段或一次检查点；
- `ask_student` 的检查题结束；
- 学生明确说出偏好、背景、目标；
- 学生说“忘掉这个/不要记”；
- 记忆文件损坏、过长、结构混乱，需要修复或压缩。

不要使用：

- 普通问答、临时调试、一次性问题；
- 学生没有提供新信息时；
- 想记录完整对话或完整代码时。

## 2. 记忆地图

```text
/memory/
├── AGENTS.md              # 唯一常驻注入：学生卡片 / dashboard
├── profile.md             # 稳定画像：背景、偏好、目标
├── learning.md            # 动态学习状态：进度、掌握、误解、有效策略
└── sessions/
    └── YYYY-MM.md         # 按月追加的会话摘要
```

职责：

| 文件 | 内容 | 是否常驻 |
|---|---|---|
| `AGENTS.md` | 每轮都要知道的摘要 | 是，自动注入 |
| `profile.md` | 稳定背景、偏好、目标 | 否，按需读 |
| `learning.md` | 进度、概念掌握、误解、策略 | 否，按需读 |
| `sessions/YYYY-MM.md` | 按月会话摘要 | 否，按需读 |

## 3. 硬规则

1. `/memory` 是虚拟路径，只能用 `read_file` / `edit_file` / `write_file`，不能用 shell 的 `cat`/`echo`。
2. 只有 `AGENTS.md` 会自动加载；`profile.md`、`learning.md`、`sessions/` 由你按需读取。
3. `AGENTS.md` 是摘要，明细文件是事实来源。冲突时以明细文件为准，然后更新 `AGENTS.md`。
4. 只在检查点、quiz 结束、学生明确自述或要求忘记时更新；不要每轮都写。
5. 不记录完整对话、完整代码、沙箱 ID、IP、端口、公钥/私钥、token、`.env`、敏感个人信息。
6. 不使用“基础差”“不认真”“聪明”等评价性标签。
7. `AGENTS.md` 控制在 500 tokens / 2KB 以内；`learning.md` 控制在 8KB 以内。
8. 同一个 thread 内 `AGENTS.md` 不会重新加载；更新后下一次新 thread 才生效。当前 thread 需要细节时，直接读 `learning.md`。

## 4. 文件模板

以下模板中的具体数值、章节和例子都是示例。创建新学生的记忆时不要原样复制；未知字段留空或写“未知”。

### 4.1 `AGENTS.md`

```markdown
# 学生卡片

## 摘要
- 称呼：
- 语言：中文
- 背景：Python 入门；计网零基础；位运算较弱
- 偏好：先提问后解释；喜欢画图；不要直接给完整代码
- 当前：第 6 章；已完成 1–5
- 下一步：学生自己写 probe_ttl，先用 TTL=8 验证
- 当前易错点：header_len 忘记乘 4；没回包时跳过 append

## 记忆地图
- `profile.md`：稳定背景、偏好、目标
- `learning.md`：进度、掌握、误解、有效策略
- `sessions/YYYY-MM.md`：按月的会话摘要

## 维护约定
- 本文件只放摘要，不超过 500 tokens
- 细节写 `profile.md` / `learning.md`
- 不记录密码、token、敏感个人信息
```

### 4.2 `profile.md`

```markdown
# 稳定画像

## 背景
- Python：入门（自述）
- 计网：零基础（自述）
- 位运算：较弱（推断，置信中）
- 用过：traceroute / tcpdump / Wireshark（未知）

## 偏好
- 语言：中文
- 解释方式：先提问 → 再类比 → 最后代码
- 提示强度：最小提示
- 节奏：慢，一次只改一个点
- 喜欢：画图、真实输出对照
- 不喜欢：直接贴完整代码

## 目标
- 完成核心 8 章
- 希望真正理解 TTL/ICMP，而不是只跑通

## 更新记录
- 2026-10-26：学生自述 Python 入门、计网零基础
```

约定：

- 自述和推断分开；推断标注置信度。
- 不确定写“未知”，不要编。
- 不使用评价性标签。

### 4.3 `learning.md`

```markdown
# 学习状态

## 进度
- 当前章：6
- 已完成：1–5
- 上次会话：2026-10-26
- 当前焦点：probe_ttl 和返回值契约
- 下一步：单 TTL 验证 → 循环 → 空列表对齐

## 概念掌握
| 概念 | 状态 | 证据 |
|---|---|---|
| TTL | solid | 能解释 TTL=1 的行为 |
| IPv4 头 | learning | 能读 src/dst，header_len 还会忘 |
| UDP/ICMP | learning | 知道 11/0 和 3/3 |
| socket | learning | 能发包，select 还会忘 |
| hex | learning | 能数偏移，字节序偶尔错 |
| probe_ttl | not_seen | 还没开始 |

## 当前误解
| 概念 | 表现 | 状态 | 次数 | 最后出现 |
|---|---|---|---|---|
| IPv4 头 | header_len 忘记乘 4 | active | 2 | 2026-10-26 |
| 返回值 | 没回包时跳过 append | active | 1 | 2026-10-26 |

## 有效策略
- 有效：画路径图；先跑 TTL=8 再讲循环；用 xxd 对照
- 无效：直接贴字段表；一次性给完整代码

## 待确认
- UDP 端口字节序是否已经稳定
- 是否理解“最后一跳只保留 [ip]”
```

约定：

- `状态` 使用 `not_seen` / `learning` / `shaky` / `solid`。
- `当前误解` 只保留 active，最多 10 条；resolved 的标记后定期清理。
- 每个概念一行，不写长段落。

### 4.4 `sessions/YYYY-MM.md`

```markdown
# 2026-10

## 2026-10-26
- 主题：第 5 章 IPv4/ICMP 解析
- 完成：三个类基本能解析；能解释内层 IP/UDP
- 卡点：UDP 端口字节序偶尔反；header_len 忘乘 4
- 检查：TTL 题答对；IPv4 字段题答错
- 下次：三个真实包自测 UDP；再进入第 6 章

<!-- APPEND BELOW -->
```

约定：

- 一次会话一个二级标题。
- 每次 5 行左右，不写完整对话。
- 末尾保留 `<!-- APPEND BELOW -->`。
- 追加时把标记替换成“新条目 + 同一个标记”。
- 只追加，不改历史。

## 5. 首次使用

第一次没有记忆文件时：

1. 不要阻塞教学；先正常回答学生。
2. 在第一个有意义的检查点，先读本 skill 的模板。
3. 创建 `AGENTS.md`、`profile.md`、`learning.md`。
4. 如有会话内容，创建当月 `sessions/YYYY-MM.md`。
5. 当前 thread 仍使用空记忆；下一次新 thread 才会加载 `AGENTS.md`。

创建时只写已知信息，未知字段留空或写“未知”。不要编造背景。

## 6. 更新流程

### 6.1 学生明确自述偏好/背景

例如“我 Python 只会一点”“我喜欢先看例子”。

1. 更新 `profile.md` 的对应字段，标注“自述”。
2. 更新 `AGENTS.md` 的摘要。
3. 不需要每次更新 `learning.md`。

### 6.2 quiz 结束

`ask_student` 返回后：

1. 更新 `learning.md` 的概念状态（`not_seen` / `learning` / `shaky` / `solid`）。
2. 如果答错，更新“当前误解”的 `次数` 和 `最后出现`。
3. 如果答对且之前是误解，把状态改为 resolved 或移除。
4. 更新 `AGENTS.md` 的“当前易错点”，最多保留 Top 3。

### 6.3 完成一章/阶段

1. 更新 `learning.md` 的进度和下一步。
2. 更新 `AGENTS.md` 的“当前”“下一步”。
3. 追加一条 `sessions/YYYY-MM.md`。
4. 如果 `learning.md` 超过 8KB，先压缩再更新。

### 6.4 会话结束

1. 追加一条 session 摘要。
2. 更新 `learning.md` 的“上次会话”“当前焦点”“下一步”。
3. 更新 `AGENTS.md` 摘要。
4. 不要复制完整对话。

### 6.5 学生要求忘记

学生说“忘掉这个/不要记”时：

1. 在 `profile.md` / `learning.md` 中删除或匿名化对应条目。
2. 同步 `AGENTS.md` 摘要。
3. 如果涉及敏感信息，不保留原文。
4. 不要问太多；尊重学生的删除请求。

## 7. 压缩与拆分

- `AGENTS.md` 超过 500 tokens：删细节，只留摘要。
- `profile.md` 超过 2KB：把目标/偏好拆到单独文件（v2）。
- `learning.md` 超过 8KB：拆成 `concepts.md` + `misconceptions.md`（v2）。
- `sessions/YYYY-MM.md` 超过 20KB：按季度/年份归档（v2）。
- active 误解超过 10 条：resolved 移走或清理。

v1 不主动创建额外文件；超过阈值时优先压缩，不擅自改目录结构。

## 8. 质量检查

更新完记忆后，快速检查：

- [ ] 只改了应该改的文件？
- [ ] `AGENTS.md` 仍然是摘要，没有变成流水账？
- [ ] 明细文件和 `AGENTS.md` 没有矛盾？
- [ ] active 误解不超过 10 条？
- [ ] 没有写入敏感信息、完整代码或完整对话？
- [ ] session 条目只追加，没有改历史？
- [ ] 当前 thread 是否需要直接读 `learning.md` 获取最新细节？

## 9. 不要做

- 不要用 shell 操作 `/memory`。
- 不要每轮都更新记忆。
- 不要为了“完整”记录所有对话。
- 不要记录学生没有说过的背景。
- 不要把 `AGENTS.md` 写成第二次事实来源。
- 不要删除整个记忆文件；需要重置时先归档或按模板重建。
