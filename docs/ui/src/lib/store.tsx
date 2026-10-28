import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"

import {
  getQuestion,
  questions as seedQuestions,
  sessions as seedSessions,
  transcriptFor,
  type ChatMessage,
  type Mode,
  type Question,
  type Session,
} from "@/lib/mock"

type Phase = "idle" | "thinking" | "streaming"

type StoreValue = {
  sessions: Session[]
  getSession: (id: string) => Session | undefined
  messagesFor: (id: string) => ChatMessage[]
  phaseFor: (id: string) => Phase
  createSession: (mode: Mode) => Session
  renameSession: (id: string, title: string) => void
  deleteSession: (id: string) => void
  sendMessage: (session: Session, text: string) => void
  stop: (id: string) => void
  submitCheckpoint: (
    session: Session,
    messageId: string,
    checkpointId: string,
    questionId: string,
    value: string,
  ) => void
  sandboxState: "running" | "paused" | "stopped"
  setSandboxState: (state: "running" | "paused" | "stopped") => void
  questionList: Question[]
  addQuestion: (question: Question) => void
  updateQuestion: (question: Question) => void
  deleteQuestion: (id: string) => void
}

const StoreContext = createContext<StoreValue | null>(null)

const uid = () => Math.random().toString(36).slice(2, 9)

const seedMessages = Object.fromEntries(
  seedSessions.map((session) => [session.id, transcriptFor(session)]),
)

function learnReply(text: string) {
  const topic = text.replace(/[？?。！!，,]/g, "").slice(0, 16)
  return `先别急着找定义。你把「${topic}」放在一条具体的链路上看：是哪一层在处理它，这一层又能看到什么？

说一个你预期会发生的现象，我们再对照协议的行为。`
}

function labReply() {
  return `可以。先做最小的一步：在沙盒里把命令跑一遍，然后把完整输出贴回来。

先不要加参数去“调通”，我们要先看清楚现在的行为。`
}

const checkpointFeedback: Record<string, { right: string; wrong: string }> = {
  "q-checkpoint": {
    right: `对。客户端没收到 SYN + ACK，就还停在 **SYN_SENT**，按超时重传 SYN；服务端那边已经把连接放进半开队列了。

再往下推一步：如果服务端一直等不到第三次 ACK，它会怎么处理这个半开连接？`,
    wrong: `先回到那一刻：客户端发出 SYN 之后，收到 SYN + ACK 了吗？没有的话，它凭什么进入 ESTABLISHED？

把报文顺序再看一遍，然后告诉我，客户端此时唯一能做的事是什么。`,
  },
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>(seedSessions)
  const [messages, setMessages] =
    useState<Record<string, ChatMessage[]>>(seedMessages)
  const [phase, setPhase] = useState<Record<string, Phase>>({})
  const [sandboxState, setSandboxState] = useState<
    "running" | "paused" | "stopped"
  >("running")
  const [questionList, setQuestionList] = useState<Question[]>(seedQuestions)

  const timers = useRef<Record<string, number[]>>({})

  const clearTimers = useCallback((id: string) => {
    for (const timer of timers.current[id] ?? []) {
      window.clearInterval(timer)
      window.clearTimeout(timer)
    }
    timers.current[id] = []
  }, [])

  const getSession = useCallback(
    (id: string) => sessions.find((session) => session.id === id),
    [sessions],
  )

  const messagesFor = useCallback(
    (id: string) => messages[id] ?? [],
    [messages],
  )

  const phaseFor = useCallback((id: string) => phase[id] ?? "idle", [phase])

  const createSession = useCallback((mode: Mode) => {
    const session: Session = {
      id: `s-local-${uid()}`,
      mode,
      agentId: mode === "learn" ? "teach_agent" : "exp_agent",
      title: mode === "learn" ? "新的学习会话" : "新的实验会话",
      snippet: "还没有消息",
      updatedAt: new Date().toISOString(),
      messageCount: 0,
    }
    setSessions((prev) => [session, ...prev])
    setMessages((prev) => ({ ...prev, [session.id]: [] }))
    return session
  }, [])

  const renameSession = useCallback((id: string, title: string) => {
    setSessions((prev) =>
      prev.map((session) =>
        session.id === id ? { ...session, title: title.trim() || session.title } : session,
      ),
    )
  }, [])

  const deleteSession = useCallback(
    (id: string) => {
      clearTimers(id)
      setSessions((prev) => prev.filter((session) => session.id !== id))
      setMessages((prev) => {
        const next = { ...prev }
        delete next[id]
        return next
      })
    },
    [clearTimers],
  )

  const appendMessage = useCallback((sessionId: string, message: ChatMessage) => {
    setMessages((prev) => ({
      ...prev,
      [sessionId]: [...(prev[sessionId] ?? []), message],
    }))
  }, [])

  const stop = useCallback(
    (id: string) => {
      clearTimers(id)
      setPhase((prev) => ({ ...prev, [id]: "idle" }))
      setMessages((prev) => ({
        ...prev,
        [id]: (prev[id] ?? []).map((message) =>
          message.streaming ? { ...message, streaming: false } : message,
        ),
      }))
    },
    [clearTimers],
  )

  const sendMessage = useCallback(
    (session: Session, raw: string) => {
      const text = raw.trim()
      if (!text) return

      clearTimers(session.id)
      setPhase((prev) => ({ ...prev, [session.id]: "thinking" }))

      const userMessage: ChatMessage = {
        id: uid(),
        role: "user",
        createdAt: new Date().toISOString(),
        parts: [{ kind: "text", text }],
      }
      appendMessage(session.id, userMessage)

      setSessions((prev) =>
        prev.map((item) =>
          item.id === session.id
            ? {
                ...item,
                title:
                  item.title === "新的学习会话" || item.title === "新的实验会话"
                    ? text.slice(0, 22)
                    : item.title,
                snippet: text.slice(0, 60),
                updatedAt: new Date().toISOString(),
                messageCount: (messages[session.id]?.length ?? 0) + 1,
              }
            : item,
        ),
      )

      const reply =
        session.mode === "learn" ? learnReply(text) : labReply()

      const timeout = window.setTimeout(() => {
        const assistantId = uid()
        setPhase((prev) => ({ ...prev, [session.id]: "streaming" }))
        appendMessage(session.id, {
          id: assistantId,
          role: "assistant",
          createdAt: new Date().toISOString(),
          streaming: true,
          parts: [{ kind: "text", text: "" }],
        })

        let index = 0
        const interval = window.setInterval(() => {
          index = Math.min(reply.length, index + 3)
          setMessages((prev) => ({
            ...prev,
            [session.id]: (prev[session.id] ?? []).map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    parts: [{ kind: "text", text: reply.slice(0, index) }],
                    streaming: index < reply.length,
                  }
                : message,
            ),
          }))
          if (index >= reply.length) {
            window.clearInterval(interval)
            setPhase((prev) => ({ ...prev, [session.id]: "idle" }))
          }
        }, 22)

        timers.current[session.id] = [interval]
      }, 750)

      timers.current[session.id] = [timeout]
    },
    [appendMessage, clearTimers, messages],
  )

  const submitCheckpoint = useCallback(
    (
      session: Session,
      messageId: string,
      checkpointId: string,
      questionId: string,
      value: string,
    ) => {
      const question = getQuestion(questionId)
      const correct = question?.correctOption
        ? value.startsWith(question.correctOption)
        : true

      setMessages((prev) => ({
        ...prev,
        [session.id]: (prev[session.id] ?? []).map((message) =>
          message.id === messageId
            ? {
                ...message,
                parts: message.parts.map((part) =>
                  part.kind === "checkpoint" && part.id === checkpointId
                    ? {
                        ...part,
                        checkpoint: {
                          ...part.checkpoint,
                          submitted: value,
                          correct,
                          submittedAt: new Date().toISOString(),
                        },
                      }
                    : part,
                ),
              }
            : message,
        ),
      }))

      setPhase((prev) => ({ ...prev, [session.id]: "thinking" }))
      const feedback =
        checkpointFeedback[questionId]?.[correct ? "right" : "wrong"] ??
        "记下了。我们继续。"

      const timeout = window.setTimeout(() => {
        setPhase((prev) => ({ ...prev, [session.id]: "idle" }))
        appendMessage(session.id, {
          id: uid(),
          role: "assistant",
          createdAt: new Date().toISOString(),
          parts: [{ kind: "text", text: feedback }],
        })
      }, 800)

      clearTimers(session.id)
      timers.current[session.id] = [timeout]
    },
    [appendMessage, clearTimers],
  )

  const value = useMemo<StoreValue>(
    () => ({
      sessions,
      getSession,
      messagesFor,
      phaseFor,
      createSession,
      renameSession,
      deleteSession,
      sendMessage,
      stop,
      submitCheckpoint,
      sandboxState,
      setSandboxState,
      questionList,
      addQuestion: (question) => setQuestionList((prev) => [question, ...prev]),
      updateQuestion: (question) =>
        setQuestionList((prev) =>
          prev.map((item) => (item.id === question.id ? question : item)),
        ),
      deleteQuestion: (id) =>
        setQuestionList((prev) => prev.filter((item) => item.id !== id)),
    }),
    [
      sessions,
      getSession,
      messagesFor,
      phaseFor,
      createSession,
      renameSession,
      deleteSession,
      sendMessage,
      stop,
      submitCheckpoint,
      sandboxState,
      questionList,
    ],
  )

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}

export function useStore() {
  const store = useContext(StoreContext)
  if (!store) throw new Error("useStore must be used inside StoreProvider")
  return store
}
