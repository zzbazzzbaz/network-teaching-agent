import { useEffect, useRef, useState } from "react"
import type { EChartsCoreOption, EChartsType } from "echarts/core"

import { BlockFallback } from "./block-fallback"

const DEBOUNCE_MS = 350
const DEFAULT_GRID = {
  left: 8,
  right: 16,
  top: 24,
  bottom: 8,
  outerBoundsMode: "same",
  outerBoundsContain: "axisLabel",
}

let setupPromise: Promise<typeof import("./echarts-setup")> | undefined

function loadECharts() {
  // 独立 chunk：echarts 只在第一次遇到图表时才下载。
  setupPromise ??= import("./echarts-setup")
  return setupPromise
}

export function EChartsBlock({ code }: { code: string }) {
  const [option, setOption] = useState<EChartsCoreOption | null>(null)
  const [failed, setFailed] = useState(false)
  const [reason, setReason] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<EChartsType | null>(null)
  const observerRef = useRef<ResizeObserver | null>(null)

  useEffect(() => {
    if (!code.trim()) return
    const timer = window.setTimeout(() => {
      try {
        const parsed = JSON.parse(code) as Record<string, unknown>
        if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.series)) {
          setReason("图表配置缺少 series，已显示源码。")
          setFailed(true)
          return
        }
        setFailed(false)
        setReason(null)
        const grid: Record<string, unknown> = {
          ...DEFAULT_GRID,
          ...(parsed.grid as Record<string, unknown> | undefined),
        }
        // 模型习惯写 containLabel；6.x 已废弃，剔除后由 outerBounds 接管，避免 warning。
        delete grid.containLabel
        setOption({ ...parsed, grid } as EChartsCoreOption)
      } catch {
        // 流式中 JSON 还没闭合，保持上一帧；已经以 } 结尾仍然解析失败，说明模型写错了。
        if (code.trim().endsWith("}")) {
          setReason("图表配置不是合法 JSON，已显示源码。")
          setFailed(true)
        }
      }
    }, DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [code])

  useEffect(() => {
    if (!option) return
    let cancelled = false
    void loadECharts()
      .then(({ default: echarts }) => {
        if (cancelled || !containerRef.current) return
        try {
          let chart = chartRef.current
          if (!chart) {
            chart = echarts.init(containerRef.current, "diagram", {
              renderer: "canvas",
            })
            chartRef.current = chart
            const observer = new ResizeObserver(() => {
              window.requestAnimationFrame(() => chartRef.current?.resize())
            })
            observer.observe(containerRef.current)
            observerRef.current = observer
          }
          chart.setOption(option, { notMerge: true })
        } catch (error) {
          console.error("ECharts 渲染失败", error)
          chartRef.current?.dispose()
          chartRef.current = null
          setReason("图表配置无法渲染，已显示源码。")
          setFailed(true)
        }
      })
      .catch((error) => {
        if (cancelled) return
        console.error("ECharts 加载失败", error)
        setReason("图表组件加载失败，请刷新页面后重试。")
        setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [option])

  useEffect(() => {
    if (!failed) return
    observerRef.current?.disconnect()
    observerRef.current = null
    chartRef.current?.dispose()
    chartRef.current = null
  }, [failed])

  useEffect(
    () => () => {
      observerRef.current?.disconnect()
      chartRef.current?.dispose()
    },
    [],
  )

  if (failed) return <BlockFallback code={code} reason={reason ?? undefined} />

  return (
    <div className="echarts-block">
      {option === null ? (
        <div className="echarts-placeholder text-[11px] text-ink-muted">图表生成中…</div>
      ) : null}
      <div ref={containerRef} className="echarts-canvas" role="img" aria-label="数据图表" />
    </div>
  )
}
