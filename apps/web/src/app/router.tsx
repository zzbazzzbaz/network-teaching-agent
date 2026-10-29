import { useEffect } from "react"
import {
  createRootRoute,
  createRoute,
  createRouter,
  notFound,
  Outlet,
  redirect,
  useRouter,
  type ErrorComponentProps,
} from "@tanstack/react-router"

import { ApiError } from "@/shared/api/client"
import type { Mode, Session } from "@/shared/api/types"
import { getSession } from "@/shared/auth/session"
import { ensureLangGraphThread } from "@/shared/langgraph/client"
import { Button } from "@/shared/ui/button"
import { LoginPage } from "@/features/auth"
import { agentForMode, sessionQueryOptions } from "@/features/sessions"

import { queryClient } from "./query-client"
import { ModeHomePage } from "@/widgets/mode-shell/ModeHomePage"
import { ModeShell } from "@/widgets/mode-shell/ModeShell"
import {
  SessionError,
  SessionPage,
  type SessionSearch,
} from "@/widgets/mode-shell/SessionPage"

function RootLayout() {
  return <Outlet />
}

function RoutePending() {
  return (
    <div className="flex h-dvh items-center justify-center bg-surface">
      <div className="flex flex-col items-center gap-3">
        <span className="size-5 animate-spin rounded-full border-2 border-line-strong border-t-link" />
        <p className="text-[12px] text-ink-muted">正在打开会话…</p>
      </div>
    </div>
  )
}

function RouteError({ error, reset }: ErrorComponentProps) {
  const router = useRouter()
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex h-dvh flex-col items-center justify-center bg-surface px-6 text-center">
      <p className="font-mono text-[10px] tracking-[0.12em] text-danger">
        CONNECTION ERROR
      </p>
      <h1 className="mt-3 text-[20px] font-semibold text-ink">页面加载失败</h1>
      <p className="mt-2 max-w-[42ch] text-[12.5px] leading-6 text-ink-muted">
        {error instanceof Error ? error.message : "请检查服务是否已启动。"}
      </p>
      <div className="mt-5 flex items-center gap-2">
        <Button
          onClick={() => {
            reset()
            void router.invalidate()
          }}
        >
          重试
        </Button>
        <Button variant="outline" onClick={() => void router.navigate({ to: "/learn" })}>
          返回工作台
        </Button>
      </div>
    </div>
  )
}

function SessionRouteError() {
  const router = useRouter()
  return (
    <SessionError
      onRetry={() => {
        void router.invalidate()
      }}
    />
  )
}

function NotFoundPage() {
  return (
    <div className="flex h-dvh flex-col items-center justify-center bg-surface px-6 text-center">
      <p className="font-mono text-[10px] tracking-[0.12em] text-ink-muted">
        404 / NOT FOUND
      </p>
      <h1 className="mt-3 text-[20px] font-semibold text-ink">找不到这个页面</h1>
      <p className="mt-2 text-[12.5px] text-ink-muted">链接可能不完整。</p>
      <Button asChild className="mt-5">
        <a href="/learn">返回学习工作台</a>
      </Button>
    </div>
  )
}

function validateLoginSearch(search: Record<string, unknown>): {
  redirect?: string
} {
  return {
    redirect: typeof search.redirect === "string" ? search.redirect : undefined,
  }
}

function validateSessionSearch(search: Record<string, unknown>): SessionSearch {
  const panel =
    search.panel === "questions" ||
    search.panel === "memory" ||
    search.panel === "sandbox"
      ? search.panel
      : undefined
  return {
    panel,
    question: typeof search.question === "string" ? search.question : undefined,
    path: typeof search.path === "string" ? search.path : undefined,
  }
}

async function loadSession(mode: Mode, sessionId: string): Promise<{ session: Session }> {
  let session: Session
  try {
    session = await queryClient.ensureQueryData(sessionQueryOptions(sessionId))
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) throw notFound()
    throw error
  }

  if (session.agent_id !== agentForMode(mode)) {
    if (mode === "learn") {
      throw redirect({
        to: "/lab/$sessionId",
        params: { sessionId },
      })
    }
    throw redirect({
      to: "/learn/$sessionId",
      params: { sessionId },
    })
  }

  await ensureLangGraphThread(session.session_id)
  return { session }
}

const rootRoute = createRootRoute({
  component: RootLayout,
  errorComponent: RouteError,
  notFoundComponent: NotFoundPage,
  beforeLoad: ({ location }) => {
    const loggedIn = getSession() !== null
    if (!loggedIn && location.pathname !== "/login") {
      throw redirect({
        to: "/login",
        search: { redirect: location.href },
      })
    }
    if (loggedIn && location.pathname === "/login") {
      throw redirect({ to: "/learn" })
    }
  },
})

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  beforeLoad: () => {
    throw redirect({ to: "/learn" })
  },
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  validateSearch: validateLoginSearch,
  component: LoginPage,
})

const learnLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/learn",
  component: () => <ModeShell mode="learn" />,
})

const learnIndexRoute = createRoute({
  getParentRoute: () => learnLayoutRoute,
  path: "/",
  component: () => <ModeHomePage mode="learn" />,
})

const learnSessionRoute = createRoute({
  getParentRoute: () => learnLayoutRoute,
  path: "$sessionId",
  validateSearch: validateSessionSearch,
  loader: ({ params }) => loadSession("learn", params.sessionId),
  component: LearnSessionRoute,
  errorComponent: SessionRouteError,
  pendingComponent: RoutePending,
})

function LearnSessionRoute() {
  const { sessionId } = learnSessionRoute.useParams()
  return <SessionPage mode="learn" sessionId={sessionId} />
}

const labLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/lab",
  component: () => <ModeShell mode="lab" />,
})

const labIndexRoute = createRoute({
  getParentRoute: () => labLayoutRoute,
  path: "/",
  component: () => <ModeHomePage mode="lab" />,
})

const labSessionRoute = createRoute({
  getParentRoute: () => labLayoutRoute,
  path: "$sessionId",
  validateSearch: validateSessionSearch,
  loader: ({ params }) => loadSession("lab", params.sessionId),
  component: LabSessionRoute,
  errorComponent: SessionRouteError,
  pendingComponent: RoutePending,
})

function LabSessionRoute() {
  const { sessionId } = labSessionRoute.useParams()
  return <SessionPage mode="lab" sessionId={sessionId} />
}

const routeTree = rootRoute.addChildren([
  indexRoute,
  loginRoute,
  learnLayoutRoute.addChildren([learnIndexRoute, learnSessionRoute]),
  labLayoutRoute.addChildren([labIndexRoute, labSessionRoute]),
])

export const router = createRouter({
  routeTree,
  defaultPendingComponent: RoutePending,
})

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
