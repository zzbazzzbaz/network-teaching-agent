/* ------------------------------------------------------------------
   全部为演示数据。没有网络请求，没有真实 agent / 沙盒。
   ------------------------------------------------------------------ */

export type Mode = "learn" | "lab"

export type AgentId = "teach_agent" | "exp_agent"

export type Session = {
  id: string
  mode: Mode
  agentId: AgentId
  title: string
  snippet: string
  updatedAt: string
  messageCount: number
}

export type KnowledgePoint = {
  id: string
  title: string
  parentId: string | null
  level: number
}

export type Question = {
  id: string
  origin: "public" | "mine"
  type: "single_choice" | "short_answer"
  stem: string
  options?: string[]
  correctOption?: string
  referenceAnswer?: string
  kpId: string
  secondaryKpIds?: string[]
  lastAttemptAt?: string
}

export type MemoryEntry = {
  path: string
  name: string
  kind: "file" | "directory"
  size: number
  modifiedAt: string | null
}

export type MemoryFile = {
  path: string
  content: string
  size: number
  modifiedAt: string
}

export type ToolKind =
  | "search"
  | "question"
  | "terminal"
  | "sandbox"
  | "file"

export type ToolPart = {
  kind: "tool"
  id: string
  tool: ToolKind
  name: string
  status: "success" | "running" | "error"
  summary: string
  command?: string
  output?: string
  exitCode?: number
  duration?: string
  meta?: string[]
}

export type Checkpoint = {
  questionId: string
  prompt: string
  options: string[]
  submitted?: string
  correct?: boolean
  submittedAt?: string
}

export type Part =
  | { kind: "text"; text: string }
  | { kind: "tool"; tool: ToolPart }
  | { kind: "checkpoint"; id: string; checkpoint: Checkpoint }

export type ChatMessage = {
  id: string
  role: "user" | "assistant"
  createdAt: string
  streaming?: boolean
  parts: Part[]
}

const now = new Date()
const iso = (minutesAgo: number) =>
  new Date(now.getTime() - minutesAgo * 60_000).toISOString()

const hoursAgo = (h: number) => iso(h * 60)
const daysAgo = (d: number, hour = 20, minute = 10) => {
  const date = new Date(now)
  date.setDate(date.getDate() - d)
  date.setHours(hour, minute, 0, 0)
  return date.toISOString()
}

export const user = {
  id: "u-2023010421",
  name: "林知远",
  studentId: "2023010421",
  major: "计算机科学与技术",
  initials: "林",
}

export const sandbox = {
  id: "ags-sbx-7f3c2a91",
  name: "network-lab",
  state: "running" as "running" | "paused" | "stopped",
  createdAt: daysAgo(9, 9, 24),
  lastActiveAt: iso(12),
  vscodeUrl: "https://code.example.edu/s/7f3c2a91",
  terminalUrl: "https://ttyd.example.edu/s/7f3c2a91",
}

export const knowledgePoints: KnowledgePoint[] = [
  { id: "1", title: "概述", parentId: null, level: 1 },
  { id: "2", title: "物理层", parentId: null, level: 1 },
  { id: "3", title: "数据链路层", parentId: null, level: 1 },
  { id: "4", title: "网络层", parentId: null, level: 1 },
  { id: "4.4", title: "子网划分与 CIDR", parentId: "4", level: 2 },
  { id: "5", title: "传输层", parentId: null, level: 1 },
  { id: "5.8", title: "TCP", parentId: "5", level: 2 },
  { id: "5.8.1", title: "报文段结构", parentId: "5.8", level: 3 },
  { id: "5.8.2", title: "三次握手", parentId: "5.8", level: 3 },
  { id: "5.8.3", title: "可靠传输", parentId: "5.8", level: 3 },
  { id: "5.8.4", title: "流量控制", parentId: "5.8", level: 3 },
  { id: "5.8.5", title: "拥塞控制", parentId: "5.8", level: 3 },
  { id: "6", title: "应用层", parentId: null, level: 1 },
  { id: "6.1", title: "DNS", parentId: "6", level: 2 },
  { id: "6.2", title: "HTTP", parentId: "6", level: 2 },
  { id: "6.4", title: "HTTP/2", parentId: "6", level: 2 },
]

export function kpTitle(id: string) {
  return knowledgePoints.find((k) => k.id === id)?.title ?? id
}

export const questions: Question[] = [
  {
    id: "q-tcp-second",
    origin: "public",
    type: "single_choice",
    stem: "TCP 三次握手中，第二次握手报文（服务端 → 客户端）携带的标志位是？",
    options: ["A. SYN", "B. ACK", "C. SYN + ACK", "D. FIN + ACK"],
    correctOption: "C",
    kpId: "5.8.2",
  },
  {
    id: "q-subnet-broadcast",
    origin: "public",
    type: "single_choice",
    stem: "主机地址 192.168.1.10/26 所在子网的广播地址是？",
    options: [
      "A. 192.168.1.63",
      "B. 192.168.1.64",
      "C. 192.168.1.127",
      "D. 192.168.1.255",
    ],
    correctOption: "A",
    kpId: "4.4",
  },
  {
    id: "q-why-three",
    origin: "public",
    type: "short_answer",
    stem: "为什么 TCP 建立连接需要三次握手，而不是两次？",
    referenceAnswer:
      "两次握手只能让发起方确认“我能发、你能收”，服务端无法确认客户端已经收到自己的 SYN + ACK。若服务端的确认报文丢失，服务端会单方面认为连接已建立并分配资源，而客户端仍在等待，造成半开连接和资源浪费。第三次 ACK 让双方都确认对方收到了自己的初始序号，并同步了双向可达状态。",
    kpId: "5.8.2",
  },
  {
    id: "q-checkpoint",
    origin: "mine",
    type: "single_choice",
    stem: "第二次握手（SYN + ACK）丢失后，客户端会怎样？",
    options: [
      "A. 立即回到 CLOSED，重新开始",
      "B. 停留在 SYN_SENT，超时后重传 SYN",
      "C. 进入 ESTABLISHED，开始发送数据",
      "D. 发送 RST 中止连接",
    ],
    correctOption: "B",
    kpId: "5.8.2",
    lastAttemptAt: iso(18),
  },
  {
    id: "q-udp-why",
    origin: "mine",
    type: "short_answer",
    stem: "为什么 UDP 不需要握手？",
    referenceAnswer:
      "UDP 不提供连接状态、可靠传输和有序交付，它只是把数据报交给网络层，因此没有需要协商的初始序号、窗口和连接状态。代价是应用层必须自己处理丢失、重复和乱序。",
    kpId: "5.8.1",
    secondaryKpIds: ["5.8.3"],
    lastAttemptAt: daysAgo(3, 16, 2),
  },
  {
    id: "q-http2-hol",
    origin: "public",
    type: "single_choice",
    stem: "HTTP/2 主要通过什么机制缓解 HTTP/1.1 的队头阻塞？",
    options: [
      "A. 在一条 TCP 连接上多路复用多个流",
      "B. 为每个资源建立独立 TCP 连接",
      "C. 把请求合并成一个更大的请求",
      "D. 使用 UDP 替代 TCP",
    ],
    correctOption: "A",
    kpId: "6.4",
  },
  {
    id: "q-slow-start",
    origin: "public",
    type: "short_answer",
    stem: "慢启动阶段拥塞窗口如何增长？它“慢”在哪里？",
    referenceAnswer:
      "慢启动每个 RTT 将拥塞窗口翻倍（按 ACK 逐个增加），呈指数增长。所谓“慢”是指起点只有一个 MSS，而不是指增长速度慢；与一次性发送整个接收窗口相比，它从很小的窗口开始试探网络容量。",
    kpId: "5.8.5",
  },
]

export function getQuestion(id: string) {
  return questions.find((q) => q.id === id)
}

export const sessions: Session[] = [
  {
    id: "s-tcp-handshake",
    mode: "learn",
    agentId: "teach_agent",
    title: "TCP 三次握手",
    snippet: "第二次握手丢失后，客户端为什么还停在 SYN_SENT？",
    updatedAt: iso(16),
    messageCount: 12,
  },
  {
    id: "s-subnet",
    mode: "learn",
    agentId: "teach_agent",
    title: "子网划分与 CIDR",
    snippet: "把 /26 的块大小算出来之后，广播地址就好找了。",
    updatedAt: hoursAgo(5),
    messageCount: 18,
  },
  {
    id: "s-http2",
    mode: "learn",
    agentId: "teach_agent",
    title: "HTTP/2 的多路复用",
    snippet: "队头阻塞被搬到了 TCP 层，所以 HTTP/3 才换成了 QUIC。",
    updatedAt: daysAgo(1, 21, 42),
    messageCount: 9,
  },
  {
    id: "s-window",
    mode: "learn",
    agentId: "teach_agent",
    title: "滑动窗口到底在限制什么",
    snippet: "接收窗口是接收方的承诺，拥塞窗口是发送方的试探。",
    updatedAt: daysAgo(2, 15, 8),
    messageCount: 14,
  },
  {
    id: "s-switch-router",
    mode: "learn",
    agentId: "teach_agent",
    title: "交换机和路由器的分工",
    snippet: "一个看 MAC，一个看 IP；一个不拆广播域，一个拆。",
    updatedAt: daysAgo(4, 10, 26),
    messageCount: 7,
  },
  {
    id: "s-congestion",
    mode: "learn",
    agentId: "teach_agent",
    title: "拥塞控制：慢启动慢在哪",
    snippet: "窗口从 1 个 MSS 开始，每个 RTT 翻倍。",
    updatedAt: daysAgo(7, 19, 55),
    messageCount: 11,
  },
  {
    id: "s-tcpdump",
    mode: "lab",
    agentId: "exp_agent",
    title: "tcpdump 抓一次三次握手",
    snippet: "6 个包，正好覆盖三次握手的两来一往。",
    updatedAt: iso(8),
    messageCount: 10,
  },
  {
    id: "s-udp-echo",
    mode: "lab",
    agentId: "exp_agent",
    title: "写一个 UDP 回声服务器",
    snippet: "先跑通再谈丢包，socket 的阻塞模式先别动。",
    updatedAt: daysAgo(1, 16, 20),
    messageCount: 16,
  },
  {
    id: "s-iperf",
    mode: "lab",
    agentId: "exp_agent",
    title: "用 iperf3 看带宽与丢包",
    snippet: "带宽上不去，不一定是链路问题，先看窗口和重传。",
    updatedAt: daysAgo(3, 11, 12),
    messageCount: 8,
  },
  {
    id: "s-dns",
    mode: "lab",
    agentId: "exp_agent",
    title: "从 dig 看递归与迭代",
    snippet: "递归是替你做，迭代是告诉你去问谁。",
    updatedAt: daysAgo(6, 14, 45),
    messageCount: 13,
  },
]

export function sessionsByMode(mode: Mode) {
  return sessions
    .filter((s) => s.mode === mode)
    .toSorted((a, b) => +new Date(b.updatedAt) - +new Date(a.updatedAt))
}

export function sessionById(id: string) {
  return sessions.find((s) => s.id === id)
}

export const memoryEntries: MemoryEntry[] = [
  { path: "/memory/", name: "memory", kind: "directory", size: 0, modifiedAt: null },
  {
    path: "/memory/AGENTS.md",
    name: "AGENTS.md",
    kind: "file",
    size: 1180,
    modifiedAt: daysAgo(12, 9, 0),
  },
  {
    path: "/memory/profile.md",
    name: "profile.md",
    kind: "file",
    size: 1642,
    modifiedAt: hoursAgo(20),
  },
  { path: "/memory/lab/", name: "lab", kind: "directory", size: 0, modifiedAt: null },
  {
    path: "/memory/lab/tcpdump.md",
    name: "tcpdump.md",
    kind: "file",
    size: 932,
    modifiedAt: iso(30),
  },
  {
    path: "/memory/lab/udp-echo.md",
    name: "udp-echo.md",
    kind: "file",
    size: 754,
    modifiedAt: daysAgo(1, 16, 32),
  },
  {
    path: "/memory/teaching/",
    name: "teaching",
    kind: "directory",
    size: 0,
    modifiedAt: null,
  },
  {
    path: "/memory/teaching/tcp-handshake.md",
    name: "tcp-handshake.md",
    kind: "file",
    size: 2076,
    modifiedAt: iso(20),
  },
  {
    path: "/memory/teaching/misconceptions.md",
    name: "misconceptions.md",
    kind: "file",
    size: 1390,
    modifiedAt: daysAgo(2, 18, 40),
  },
]

export const memoryFiles: Record<string, MemoryFile> = {
  "/memory/AGENTS.md": {
    path: "/memory/AGENTS.md",
    size: 1180,
    modifiedAt: daysAgo(12, 9, 0),
    content: `# 教学约定

- 学生：林知远，计算机科学与技术，大三。
- 目标是理解原理，不是背结论；先让学生自己说，再补充。
- 每次最多追问一个问题，不要连续抛三个问题。
- 涉及计算时，先让学生写出块大小或窗口变化，再给答案。
- 实验步骤必须能在当前沙盒里复现，不要引用未安装的工具。`,
  },
  "/memory/profile.md": {
    path: "/memory/profile.md",
    size: 1642,
    modifiedAt: hoursAgo(20),
    content: `# 学习画像

## 基础
- 学过数据结构与操作系统，C 和 Python 都能写。
- 网络部分只上过理论课，没有抓过真实报文。

## 偏好
- 喜欢先看一个具体现象，再回到定义。
- 对纯文字推导耐心有限，图示和报文时序更有效。
- 不喜欢被直接给答案，但卡住超过两轮会明显焦虑。

## 容易混淆的点
- 接收窗口（rwnd）与拥塞窗口（cwnd）的区别。
- 三次握手中每一步之后双方各自处于什么状态。
- 广播地址与网络地址的边界。

## 最近进展
- 2026-10-27：能独立算出 /26 的块大小和广播地址。
- 2026-10-28：开始理解第二次握手丢失后的重传行为，仍需巩固。`,
  },
  "/memory/teaching/tcp-handshake.md": {
    path: "/memory/teaching/tcp-handshake.md",
    size: 2076,
    modifiedAt: iso(20),
    content: `# TCP 三次握手 · 讲解记录

## 学生最初的解释
> 两次就够了吧，双方不都知道对方能收能发了吗？

这个说法只覆盖了“发起方视角”。服务端发出 SYN + ACK 之后，并不知道客户端有没有收到。

## 有效的类比
把三次握手看成双方各自确认两件事：

1. 我的发送能力被你看到（你回 ACK）。
2. 你的发送能力被我看到（我收到你的 SYN）。

第二次握手丢失时，服务端已经分配了连接资源，客户端却还在 SYN_SENT，形成半开连接。

## 下次可以继续追问
- 如果第三次 ACK 丢失，服务端会等多久？
- 为什么初始序号要随机化？`,
  },
  "/memory/teaching/misconceptions.md": {
    path: "/memory/teaching/misconceptions.md",
    size: 1390,
    modifiedAt: daysAgo(2, 18, 40),
    content: `# 常见误解

## 1. 三次握手是为了“三次确认”
不是。每次握手承担的信息不同，重点在同步初始序号和确认双向可达。

## 2. 慢启动增长很慢
慢在起点（1 个 MSS），实际是按 RTT 指数增长。

## 3. 接收窗口等于发送窗口
rwnd 由接收方通告，cwnd 由发送方维护，实际可发送量取两者较小值。

## 4. 交换机不隔离广播
二层交换机默认转发广播帧；只有 VLAN 才能划分广播域。`,
  },
  "/memory/lab/tcpdump.md": {
    path: "/memory/lab/tcpdump.md",
    size: 932,
    modifiedAt: iso(30),
    content: `# 实验：tcpdump 观察三次握手

## 环境
- 沙盒：ags-sbx-7f3c2a91
- 网卡：eth0
- 过滤表达式：tcp[tcpflags] & (tcp-syn|tcp-ack) != 0

## 观察结果
6 个包覆盖完整握手：SYN、SYN + ACK、ACK，随后是两次数据交互与 FIN。

## 待确认
- 客户端重传 SYN 的间隔是否随次数增加？
- 用 -S 打印绝对序号后，为什么初始序号看起来仍然很大？`,
  },
  "/memory/lab/udp-echo.md": {
    path: "/memory/lab/udp-echo.md",
    size: 754,
    modifiedAt: daysAgo(1, 16, 32),
    content: `# 实验：UDP 回声服务器

## 已跑通
- Python 3.12，socket.SOCK_DGRAM
- 服务端绑定 0.0.0.0:9001
- 客户端发送 "ping"，收到 "ping"

## 下一步
- 模拟 10% 丢包，观察客户端超时行为。
- 对比 TCP 版本，记录连接建立耗时。`,
  },
}

export const learnTranscript: ChatMessage[] = [
  {
    id: "m1",
    role: "user",
    createdAt: iso(64),
    parts: [
      {
        kind: "text",
        text: "我还是没想明白，TCP 建连接为什么非得三次握手？两次不够吗？",
      },
    ],
  },
  {
    id: "m2",
    role: "assistant",
    createdAt: iso(63),
    parts: [
      {
        kind: "text",
        text: `先把“握手”放回它要解决的问题里：双方都要确认两件事——**我能发到你**、**你能发到我**，并且要知道对方也确认了。

两次握手只能让发起方确认双向可达。服务端发出 SYN + ACK 之后，并不知道客户端有没有收到。如果这个报文丢了，服务端已经分配资源、认为连接建立，客户端却还在等——这就是半开连接。

你可以先看报文顺序：

\`\`\`
client                          server
  |------ SYN seq=x ----------->|
  |<----- SYN+ACK seq=y -------|
  |------ ACK ack=y+1 -------->|
\`\`\`

第三次 ACK 看起来“多余”，但它让服务端确认：客户端收到了我的初始序号，并且仍然愿意继续。`,
      },
    ],
  },
  {
    id: "m3",
    role: "assistant",
    createdAt: iso(62),
    parts: [
      {
        kind: "tool",
        tool: {
          kind: "tool",
          id: "t1",
          tool: "search",
          name: "search_questions",
          status: "success",
          summary: "题库中找到 2 道相关题",
          duration: "0.4s",
          meta: ["公共题库", "知识点 5.8.2"],
        },
      },
    ],
  },
  {
    id: "m4",
    role: "assistant",
    createdAt: iso(61),
    parts: [
      {
        kind: "text",
        text: "在继续之前，我想确认一下你是不是真的抓住了“丢失”这个角度。先别翻书，凭直觉选一个：",
      },
      {
        kind: "checkpoint",
        id: "cp-open",
        checkpoint: {
          questionId: "q-checkpoint",
          prompt: "第二次握手（SYN + ACK）丢失后，客户端会怎样？",
          options: [
            "A. 立即回到 CLOSED，重新开始",
            "B. 停留在 SYN_SENT，超时后重传 SYN",
            "C. 进入 ESTABLISHED，开始发送数据",
            "D. 发送 RST 中止连接",
          ],
        },
      },
    ],
  },
]

export const subnetTranscript: ChatMessage[] = [
  {
    id: "s1",
    role: "user",
    createdAt: hoursAgo(5.4),
    parts: [{ kind: "text", text: "192.168.1.10/26 的广播地址怎么算？我总是把块大小记错。" }],
  },
  {
    id: "s2",
    role: "assistant",
    createdAt: hoursAgo(5.3),
    parts: [
      {
        kind: "text",
        text: `先别记公式，只看掩码借走了多少位。/26 表示前 26 位是网络位，主机位剩下 6 位。

所以每个子网有 \`2^6 = 64\` 个地址，块大小就是 64。以 0 为起点切块：

- 192.168.1.0 – 192.168.1.63
- 192.168.1.64 – 192.168.1.127

10 落在第一块里：网络地址是 .0，广播地址是 .63，可用主机是 .1 – .62。`,
      },
    ],
  },
  {
    id: "s3",
    role: "assistant",
    createdAt: hoursAgo(5.25),
    parts: [
      {
        kind: "text",
        text: "给你一道同类题，确认你真的会切块，而不是背了答案：",
      },
      {
        kind: "checkpoint",
        id: "cp-answered",
        checkpoint: {
          questionId: "q-subnet-broadcast",
          prompt: "主机地址 192.168.1.10/26 所在子网的广播地址是？",
          options: [
            "A. 192.168.1.63",
            "B. 192.168.1.64",
            "C. 192.168.1.127",
            "D. 192.168.1.255",
          ],
          submitted: "A",
          correct: true,
          submittedAt: hoursAgo(5.2),
        },
      },
      {
        kind: "text",
        text: "对了。你刚才用的其实是“块大小 + 边界”的办法，比套公式稳。下一题换个掩码：/27 的块大小是多少？",
      },
    ],
  },
  {
    id: "s4",
    role: "assistant",
    createdAt: hoursAgo(5.1),
    parts: [
      {
        kind: "tool",
        tool: {
          kind: "tool",
          id: "t-subnet",
          tool: "question",
          name: "save_question",
          status: "success",
          summary: "已把「/26 广播地址」保存到我的题库",
          duration: "0.2s",
          meta: ["私有题", "知识点 4.4"],
        },
      },
    ],
  },
]

export const labTranscript: ChatMessage[] = [
  {
    id: "l1",
    role: "user",
    createdAt: iso(34),
    parts: [
      {
        kind: "text",
        text: "我想亲眼看到三次握手。用 tcpdump 应该怎么抓，才不会淹在一堆包里？",
      },
    ],
  },
  {
    id: "l2",
    role: "assistant",
    createdAt: iso(33),
    parts: [
      {
        kind: "tool",
        tool: {
          kind: "tool",
          id: "t-sandbox",
          tool: "sandbox",
          name: "ensure_sandbox",
          status: "success",
          summary: "沙盒已就绪",
          duration: "0.9s",
          meta: ["running", "ags-sbx-7f3c2a91", "账户级 workspace"],
        },
      },
      {
        kind: "text",
        text: `先确认沙盒里的网卡名，再只抓带 SYN 或 ACK 标志的包。这样输出短，顺序也清楚。

\`\`\`bash
ip -brief addr
sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & (tcp-syn|tcp-ack) != 0' -c 6
\`\`\`

第二条命令只取前 6 个符合条件的包，正好覆盖一次握手。抓完把输出贴给我，我们一起对序号。`,
      },
    ],
  },
  {
    id: "l3",
    role: "assistant",
    createdAt: iso(31),
    parts: [
      {
        kind: "tool",
        tool: {
          kind: "tool",
          id: "t-exec",
          tool: "terminal",
          name: "execute",
          status: "success",
          summary: "捕获 6 个包，用时 3.2 秒",
          command:
            "sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & (tcp-syn|tcp-ack) != 0' -c 6",
          output: `13:42:07.118402 IP 10.0.3.18.51244 > 10.0.3.1.80: Flags [S], seq 2847193021, win 64240, length 0
13:42:07.118933 IP 10.0.3.1.80 > 10.0.3.18.51244: Flags [S.], seq 991823744, ack 2847193022, win 65160, length 0
13:42:07.119214 IP 10.0.3.18.51244 > 10.0.3.1.80: Flags [.], ack 1, win 502, length 0
13:42:07.120881 IP 10.0.3.18.51244 > 10.0.3.1.80: Flags [P.], seq 1:78, ack 1, length 77
13:42:07.121402 IP 10.0.3.1.80 > 10.0.3.18.51244: Flags [P.], seq 1:512, ack 78, length 511
13:42:07.121669 IP 10.0.3.18.51244 > 10.0.3.1.80: Flags [.], ack 512, win 501, length 0`,
          exitCode: 0,
          duration: "3.2s",
          meta: ["eth0", "6 packets captured"],
        },
      },
    ],
  },
  {
    id: "l4",
    role: "assistant",
    createdAt: iso(30),
    parts: [
      {
        kind: "text",
        text: `看前三行就够了：

1. \`[S]\` 是客户端发的 SYN，序号 2847193021。
2. \`[S.]\` 是服务端回的 SYN + ACK，ack 正好是对方序号 + 1。
3. \`[.]\` 是第三次 ACK，此时两边才都进入 ESTABLISHED。

后面三行已经在传数据了，不是握手的一部分。

现在试试：把 \`-c 6\` 改成 \`-c 3\`，再从客户端重新发起一次连接。你预期能看到哪三个包？`,
      },
    ],
  },
]

export function transcriptFor(session: Session): ChatMessage[] {
  if (session.id === "s-tcp-handshake") return learnTranscript
  if (session.id === "s-subnet") return subnetTranscript
  if (session.id === "s-tcpdump") return labTranscript

  return [
    {
      id: `${session.id}-u`,
      role: "user",
      createdAt: new Date(+new Date(session.updatedAt) - 6 * 60_000).toISOString(),
      parts: [{ kind: "text", text: `我们继续聊聊「${session.title}」吧。` }],
    },
    {
      id: `${session.id}-a`,
      role: "assistant",
      createdAt: session.updatedAt,
      parts: [
        {
          kind: "text",
          text: `${session.snippet}\n\n这是演示数据中的历史记录。你可以继续追问，也可以切换到另一条会话看看布局。`,
        },
      ],
    },
  ]
}

export const starters = {
  learn: [
    "TCP 为什么需要三次握手？",
    "子网掩码和广播地址怎么算？",
    "HTTP/2 的多路复用解决了什么？",
    "接收窗口和拥塞窗口有什么区别？",
  ],
  lab: [
    "用 tcpdump 观察一次完整握手",
    "写一个 UDP 回声服务器",
    "用 dig 看递归查询和迭代查询",
    "用 iperf3 测一次带宽",
  ],
}

export const lastVisited = {
  learn: sessions.find((s) => s.id === "s-subnet")!,
  lab: sessions.find((s) => s.id === "s-tcpdump")!,
}
