import { ArrowLeft, Check, Link2 } from "lucide-react"
import type { ReactNode } from "react"
import { Link } from "react-router-dom"

import { LayerMark, Wordmark } from "@/components/brand"
import { ToolTrace } from "@/components/chat/tool-trace"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import type { ToolPart } from "@/lib/mock"

const COLORS = [
  { name: "纸面", value: "#F2F4F3", token: "--paper", light: true },
  { name: "表面", value: "#FFFFFF", token: "--surface", light: true },
  { name: "墨", value: "#121A1C", token: "--ink" },
  { name: "次级文字", value: "#5C6E70", token: "--ink-muted" },
  { name: "分隔线", value: "#DCE3E1", token: "--line", light: true },
  { name: "链路青", value: "#0E6B60", token: "--link" },
  { name: "信号琥珀", value: "#9A5900", token: "--signal" },
  { name: "警示", value: "#B42318", token: "--danger" },
]

const TOOL_SAMPLE: ToolPart = {
  kind: "tool",
  id: "sg-tool",
  tool: "terminal",
  name: "execute",
  status: "success",
  summary: "捕获 6 个包，用时 3.2 秒",
  command:
    "sudo tcpdump -i eth0 -nn 'tcp[tcpflags] & (tcp-syn|tcp-ack) != 0' -c 6",
  output: `13:42:07.118402 IP 10.0.3.18.51244 > 10.0.3.1.80: Flags [S], seq 2847193021
13:42:07.118933 IP 10.0.3.1.80 > 10.0.3.18.51244: Flags [S.], ack 2847193022`,
  exitCode: 0,
  duration: "3.2s",
  meta: ["eth0", "6 packets captured"],
}

function Section({
  title,
  intro,
  children,
  id,
}: {
  title: string
  intro?: string
  children: ReactNode
  id: string
}) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-line py-10 lg:py-12">
      <div className="grid gap-5 lg:grid-cols-[140px_minmax(0,1fr)] lg:gap-10">
        <div>
          <h2 className="text-[13px] font-semibold text-ink">{title}</h2>
          {intro && (
            <p className="mt-2 text-[11.5px] leading-5 text-ink-muted">{intro}</p>
          )}
        </div>
        <div className="min-w-0">{children}</div>
      </div>
    </section>
  )
}

export function StyleGuidePage() {
  return (
    <div className="min-h-dvh bg-paper">
      <header className="sticky top-0 z-20 border-b border-line bg-paper/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1080px] items-center justify-between gap-4 px-5 lg:px-10">
          <Wordmark />
          <div className="flex items-center gap-2">
            <Button asChild variant="outline" size="sm" className="gap-1.5">
              <Link to="/learn">
                <ArrowLeft className="size-3.5" aria-hidden="true" />
                返回工作台
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main id="main" className="mx-auto w-full max-w-[1080px] px-5 pb-16 lg:px-10">
        <div className="pt-10 pb-8 lg:pt-14">
          <p className="text-[11.5px] text-ink-muted">UI 规范 · v1</p>
          <h1 className="mt-3 max-w-[20ch] text-[32px] leading-[1.3] font-semibold tracking-[-0.02em] text-ink lg:text-[38px]">
            链路 · 学生端界面
          </h1>
          <p className="mt-4 max-w-[56ch] text-[13.5px] leading-7 text-ink-muted">
            这一版先确定布局、信息层级和语气。组件来自 shadcn / Radix，自定义集中在令牌、间距和三个特征部件上。
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-2 text-[11px] text-ink-muted">
            <Badge variant="outline">桌面优先</Badge>
            <Badge variant="outline">移动端可完整操作</Badge>
            <Badge variant="outline">浅色单主题</Badge>
            <span>2026-10-28</span>
          </div>
        </div>

        <Section
          id="direction"
          title="方向"
          intro="网络课程的经验：长对话、报文、路径。界面应该像一张实验台记录纸，而不是一块仪表盘。"
        >
          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <h3 className="text-[13.5px] font-semibold text-ink">纸面与链路</h3>
              <p className="mt-1.5 text-[12.5px] leading-6 text-ink-muted">
                冷白纸面承托长文本，青色只出现在可操作、可连接的地方。结构用 1px 线，不用阴影堆卡片。
              </p>
            </div>
            <div>
              <h3 className="text-[13.5px] font-semibold text-ink">一个记忆点</h3>
              <p className="mt-1.5 text-[12.5px] leading-6 text-ink-muted">
                对话左侧的节点与连线表示轮次；琥珀色只给作答检查点。其余区域保持安静。
              </p>
            </div>
            <div>
              <h3 className="text-[13.5px] font-semibold text-ink">技术数据才用等宽</h3>
              <p className="mt-1.5 text-[12.5px] leading-6 text-ink-muted">
                工具名、路径、命令、时间戳使用等宽；不用等宽字体做装饰性标签。
              </p>
            </div>
            <div>
              <h3 className="text-[13.5px] font-semibold text-ink">写成动作和结果</h3>
              <p className="mt-1.5 text-[12.5px] leading-6 text-ink-muted">
                「打开终端」「查看答案」「提交作答」。错误说明下一步，不道歉。
              </p>
            </div>
          </div>
        </Section>

        <Section id="color" title="色彩" intro="8 个基础值。琥珀只用于检查点、暂停和需要注意的状态。">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {COLORS.map((color) => (
              <div key={color.token} className="rounded-md border border-line bg-surface p-2.5">
                <div
                  className="h-12 rounded-sm border border-line/60"
                  style={{ backgroundColor: color.value }}
                />
                <p className="mt-2 text-[12px] font-medium text-ink">{color.name}</p>
                <p className="mt-0.5 font-mono text-[10px] text-ink-muted">{color.value}</p>
                <p className="mt-0.5 font-mono text-[9.5px] text-ink-muted/80">
                  {color.token}
                </p>
              </div>
            ))}
          </div>
        </Section>

        <Section
          id="type"
          title="字体"
          intro="IBM Plex Sans 提供工程感，中文交给系统黑体；IBM Plex Mono 只用于技术数据。"
        >
          <div className="space-y-5 rounded-lg border border-line bg-surface p-5">
            <div>
              <p className="text-[10.5px] text-ink-muted">展示 · 32 / 600 / -0.02em</p>
              <p className="mt-1 text-[32px] leading-[1.3] font-semibold tracking-[-0.02em] text-ink">
                先想清楚，再问清楚。
              </p>
            </div>
            <div className="border-t border-line pt-4">
              <p className="text-[10.5px] text-ink-muted">标题 · 18 / 600</p>
              <p className="mt-1 text-[18px] font-semibold text-ink">第二次握手丢失之后</p>
            </div>
            <div className="border-t border-line pt-4">
              <p className="text-[10.5px] text-ink-muted">对话正文 · 15 / 1.85 / 中文系统字重 400</p>
              <p className="mt-1 max-w-[62ch] text-[15px] leading-[1.85] text-ink">
                两次握手只能让发起方确认双向可达。服务端发出 SYN + ACK 之后，并不知道客户端有没有收到。
              </p>
            </div>
            <div className="border-t border-line pt-4">
              <p className="text-[10.5px] text-ink-muted">界面文字 · 13 / 500</p>
              <p className="mt-1 text-[13px] font-medium text-ink">
                题库 · 记忆 · 沙盒运行中
              </p>
            </div>
            <div className="border-t border-line pt-4">
              <p className="text-[10.5px] text-ink-muted">技术数据 · 12 / IBM Plex Mono</p>
              <p className="mt-1 font-mono text-[12px] text-ink-soft">
                /memory/teaching/tcp-handshake.md · 13:42:07.118402
              </p>
            </div>
          </div>
        </Section>

        <Section
          id="layout"
          title="布局"
          intro="侧栏承载模式和功能入口，可收起到 72px；主区在对话与题库 / 记忆 / 沙盒之间整页切换。没有顶栏，也没有右侧面板。"
        >
          <div className="rounded-lg border border-line bg-surface p-4">
            <div className="grid gap-2 sm:grid-cols-[170px_minmax(0,1fr)]">
              <div className="flex h-56 flex-col gap-1 rounded-sm border border-line bg-paper p-2">
                <div className="flex items-center gap-1.5 px-1 pb-1">
                  <LayerMark className="size-3.5 text-link" />
                  <span className="text-[10px] font-medium text-ink">链路</span>
                </div>
                <div className="grid grid-cols-2 gap-0.5 rounded-sm bg-surface-3 p-0.5 text-center text-[9px]">
                  <span className="rounded-sm border border-line bg-surface py-0.5">
                    学习
                  </span>
                  <span className="py-0.5 text-ink-muted">实验</span>
                </div>
                <div className="mt-1 flex items-center justify-between rounded-sm bg-link-soft px-1.5 py-1 text-[9px] font-medium text-link-strong">
                  <span>题库</span>
                </div>
                <div className="flex items-center justify-between px-1.5 py-1 text-[9px] text-ink-muted">
                  <span>记忆</span>
                </div>
                <div className="flex items-center gap-1 px-1.5 py-1 text-[9px] text-ink-muted">
                  <span>＋</span>
                  新建会话
                </div>
                <div className="mt-auto border-t border-line px-1.5 pt-1.5 text-[8px] text-ink-muted">
                  会话列表
                </div>
              </div>

              <div className="flex h-56 flex-col items-center justify-center gap-3 rounded-sm border border-line bg-surface-2 px-3 text-center">
                <div className="flex flex-wrap items-center justify-center gap-1.5 text-[10px]">
                  <span className="rounded-sm border border-line bg-surface px-2 py-1 font-mono text-[9px] text-ink">
                    对话
                  </span>
                  <span className="text-ink-muted">/</span>
                  <span className="rounded-sm px-1.5 py-1 text-ink-muted">题库</span>
                  <span className="rounded-sm px-1.5 py-1 text-ink-muted">记忆</span>
                  <span className="rounded-sm px-1.5 py-1 text-ink-muted">沙盒</span>
                </div>
                <span className="font-mono text-[9px] leading-5 text-ink-muted">
                  整页切换 · 对话 max 840 · 面板 max 960
                </span>
              </div>
            </div>
            <p className="mt-3 text-[10.5px] leading-5 text-ink-muted">
              ≥ 1024px：侧栏固定 284，可收起到 72 的图标栏；主区占满，点击已激活的功能入口回到对话。
              移动端顶栏 52，侧栏变成 Sheet。
            </p>
          </div>

          <div className="mt-6 overflow-hidden rounded-lg border border-line bg-surface">
            <table className="w-full text-left text-[12px]">
              <thead className="border-b border-line bg-surface-2/60 text-[10.5px] text-ink-muted">
                <tr>
                  <th scope="col" className="px-3 py-2 font-medium">视口</th>
                  <th scope="col" className="px-3 py-2 font-medium">侧栏</th>
                  <th scope="col" className="px-3 py-2 font-medium">主区</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line text-ink-soft">
                <tr>
                  <td className="px-3 py-2 font-mono text-[11px]">≥ 1024</td>
                  <td className="px-3 py-2">284 / 收起 72</td>
                  <td className="px-3 py-2">对话 / 面板整页</td>
                </tr>
                <tr>
                  <td className="px-3 py-2 font-mono text-[11px]">&lt; 1024</td>
                  <td className="px-3 py-2">左侧 Sheet</td>
                  <td className="px-3 py-2">52 顶栏 + 整页</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Section>

        <Section id="components" title="组件" intro="按钮、表单、状态和三个领域部件。">
          <div className="space-y-7">
            <div>
              <h3 className="text-[11.5px] font-medium text-ink-muted">按钮</h3>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <Button>新建会话</Button>
                <Button variant="outline">查看答案</Button>
                <Button variant="ghost">取消</Button>
                <Button variant="destructive-outline">销毁沙盒</Button>
                <Button variant="secondary">收起</Button>
                <Button disabled>提交作答</Button>
              </div>
            </div>

            <div>
              <h3 className="text-[11.5px] font-medium text-ink-muted">表单</h3>
              <div className="mt-2 grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label htmlFor="sg-q" className="text-[12px] font-medium text-ink">
                    搜索题干
                  </label>
                  <Input id="sg-q" defaultValue="握手" />
                </div>
                <div className="space-y-1.5">
                  <label htmlFor="sg-kp" className="text-[12px] font-medium text-ink">
                    知识点
                  </label>
                  <Select defaultValue="5.8.2">
                    <SelectTrigger id="sg-kp" className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="5.8.2">三次握手</SelectItem>
                      <SelectItem value="5.8.5">拥塞控制</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5 sm:col-span-2">
                  <label htmlFor="sg-answer" className="text-[12px] font-medium text-ink">
                    参考答案
                  </label>
                  <Textarea id="sg-answer" rows={2} defaultValue="两次握手无法让服务端确认客户端收到了 SYN + ACK。" />
                </div>
              </div>
            </div>

            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-[11.5px] font-medium text-ink-muted">作答检查点</h3>
                <Button asChild variant="link" size="sm" className="h-7 text-[11.5px]">
                  <Link to="/learn/s-tcp-handshake">
                    在会话中查看
                    <Link2 className="size-3" aria-hidden="true" />
                  </Link>
                </Button>
              </div>
              <div className="mt-2 max-w-[620px] overflow-hidden rounded-lg border border-signal-line bg-signal-soft/35">
                <div className="flex items-center gap-2 border-b border-signal-line/60 px-4 py-2">
                  <span className="size-1.5 rounded-full bg-signal" aria-hidden="true" />
                  <span className="text-[11px] font-medium text-signal">作答检查点</span>
                  <span className="ml-auto font-mono text-[10px] text-signal/60">
                    ask_student
                  </span>
                </div>
                <p className="px-4 pt-3.5 text-[14px] leading-6 font-medium text-ink">
                  第二次握手（SYN + ACK）丢失后，客户端会怎样？
                </p>
                <div className="mt-2 border-t border-signal-line/40">
                  {["A. 立即回到 CLOSED", "B. 停留在 SYN_SENT，超时后重传 SYN", "C. 进入 ESTABLISHED"].map(
                    (option, index) => (
                      <div
                        key={option}
                        className={
                          index === 1
                            ? "flex items-center gap-3 border-b border-signal-line/40 bg-signal-soft/60 px-4 py-3"
                            : "flex items-center gap-3 border-b border-signal-line/40 px-4 py-3"
                        }
                      >
                        <span
                          className={
                            index === 1
                              ? "flex size-4 items-center justify-center rounded-full bg-signal"
                              : "size-4 rounded-full border border-signal/45"
                          }
                          aria-hidden="true"
                        >
                          {index === 1 && <span className="size-1.5 rounded-full bg-white" />}
                        </span>
                        <span className="text-[13px] text-ink">{option}</span>
                      </div>
                    ),
                  )}
                </div>
                <div className="flex items-center gap-3 px-4 py-3">
                  <span className="flex-1 text-[11px] text-ink-muted">提交后对话继续。</span>
                  <Button className="h-10 bg-signal text-white hover:bg-[#7d4700]">
                    提交作答
                  </Button>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-[11.5px] font-medium text-ink-muted">工具执行</h3>
              <div className="mt-2">
                <ToolTrace tool={TOOL_SAMPLE} />
              </div>
            </div>

            <div>
              <h3 className="text-[11.5px] font-medium text-ink-muted">状态</h3>
              <div className="mt-2 flex flex-wrap gap-4 text-[12px] text-ink-soft">
                <span className="flex items-center gap-2">
                  <span className="size-2 rounded-full bg-link" aria-hidden="true" />
                  运行中
                </span>
                <span className="flex items-center gap-2">
                  <span className="size-2 rounded-full bg-signal" aria-hidden="true" />
                  已暂停
                </span>
                <span className="flex items-center gap-2">
                  <span className="size-2 rounded-full bg-line-strong" aria-hidden="true" />
                  已销毁
                </span>
                <span className="flex items-center gap-2">
                  <span className="size-1.5 rounded-full bg-link link-pulse" aria-hidden="true" />
                  正在回答
                </span>
              </div>
            </div>
          </div>
        </Section>

        <Section
          id="mobile"
          title="移动端"
          intro="不是缩小的桌面端：侧栏变成 Sheet，功能入口整页替换对话。"
        >
          <div className="grid gap-6 sm:grid-cols-[220px_minmax(0,1fr)]">
            <div className="mx-auto w-[210px] rounded-[20px] border border-line-strong bg-surface p-2">
              <div className="flex h-6 items-center justify-between px-1.5 text-[8px] text-ink-muted">
                <span>9:41</span>
                <span className="font-mono">5G</span>
              </div>
              <div className="flex h-7 items-center gap-1.5 border-b border-line px-1.5">
                <span className="text-[9px] text-ink-muted">☰</span>
                <span className="truncate text-[10px] font-medium">TCP 三次握手</span>
                <span className="ml-auto text-[9px] text-link">←</span>
              </div>
              <div className="px-2 py-2">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-semibold">题库</span>
                  <span className="rounded-sm bg-link px-1 py-0.5 text-[6px] text-white">
                    新建
                  </span>
                </div>
                <div className="mt-1.5 h-5 rounded-sm border border-line-strong" />
                <div className="mt-2 flex gap-1">
                  <span className="rounded-sm bg-surface-3 px-1 py-0.5 text-[7px]">全部</span>
                  <span className="rounded-sm px-1 py-0.5 text-[7px] text-ink-muted">公共</span>
                  <span className="rounded-sm px-1 py-0.5 text-[7px] text-ink-muted">我的</span>
                </div>
                <div className="mt-2 space-y-1.5">
                  <div className="rounded-sm border border-line p-1.5">
                    <div className="h-1.5 w-8 rounded-full bg-line" />
                    <div className="mt-1 h-1.5 w-11/12 rounded-full bg-line" />
                    <div className="mt-1 h-1.5 w-3/4 rounded-full bg-line" />
                  </div>
                  <div className="rounded-sm border border-line p-1.5">
                    <div className="h-1.5 w-8 rounded-full bg-line" />
                    <div className="mt-1 h-1.5 w-10/12 rounded-full bg-line" />
                    <div className="mt-1 h-1.5 w-2/3 rounded-full bg-line" />
                  </div>
                </div>
              </div>
            </div>

            <ul className="space-y-2.5 text-[12.5px] leading-6 text-ink-soft">
              <li>侧栏变成 Sheet；题库 / 记忆 / 沙盒整页替换对话，不再叠右侧面板。</li>
              <li>顶栏 52px：菜单 + 当前会话；面板打开时右侧出现返回图标。</li>
              <li>题库详情是 Dialog；记忆在手机上先列表后文件，用卡内返回。</li>
              <li>输入框 16px，避免 iOS 聚焦缩放；Composer 处理底部安全区。</li>
              <li>主要操作 44px；密集工具条保持 32–40px，行本身可点。</li>
              <li>作答检查点在窄屏上占满宽度，选项行高 44–48px。</li>
              <li>中文输入法 composing 时 Enter 不发送。</li>
            </ul>
          </div>
        </Section>

        <Section
          id="a11y"
          title="底线"
          intro="这些不是加分项，是默认值。"
        >
          <div className="grid gap-x-8 gap-y-3 sm:grid-cols-2">
            {[
              "所有交互元素有可见的 :focus-visible 焦点环。",
              "图标按钮必须有 aria-label；装饰图标 aria-hidden。",
              "Markdown 禁止 raw HTML；外链带 noopener noreferrer。",
              "答案在用户点「查看答案」之前不渲染。",
              "尊重 prefers-reduced-motion，动画只做透明度与位移。",
              "破坏性操作二次确认；删除会话不连带题库和沙盒文件。",
              "工具输出默认截断，完整 JSON 不直接铺开。",
              "URL 记录模式、会话、面板、题目和文件路径；题库筛选是局部状态。",
            ].map((item) => (
              <p key={item} className="flex gap-2 text-[12.5px] leading-6 text-ink-soft">
                <Check className="mt-1 size-3.5 shrink-0 text-link" aria-hidden="true" />
                {item}
              </p>
            ))}
          </div>
        </Section>

        <Section id="open" title="待确认" intro="这一版先按下面的默认值做，后面可以改。">
          <dl className="space-y-3 text-[12.5px] leading-6">
            <div>
              <dt className="font-medium text-ink">工作台入口</dt>
              <dd className="text-ink-muted">
                登录后默认进入学习工作台的最新会话；学习 / 实验只在侧栏切换，模式选择页不保留。
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">移动端深度</dt>
              <dd className="text-ink-muted">
                当前按「可完整操作」实现：发消息、作答、查题库、看记忆、启停沙盒都在手机上可用。
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">深色模式</dt>
              <dd className="text-ink-muted">
                本期不做。令牌已经按语义分层，后续可以只替换值。
              </dd>
            </div>
            <div>
              <dt className="font-medium text-ink">深链</dt>
              <dd className="text-ink-muted">
                题库详情与记忆文件都进入 URL；刷新和分享都能还原。
              </dd>
            </div>
          </dl>
        </Section>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-line py-6 text-[11px] text-ink-muted">
          <span>演示原型 · 全部数据为虚构</span>
          <div className="flex gap-4">
            <Link to="/learn" className="underline decoration-line-strong underline-offset-4 hover:text-ink">
              学习模式
            </Link>
            <Link to="/lab" className="underline decoration-line-strong underline-offset-4 hover:text-ink">
              实验模式
            </Link>
          </div>
        </footer>
      </main>
    </div>
  )
}
