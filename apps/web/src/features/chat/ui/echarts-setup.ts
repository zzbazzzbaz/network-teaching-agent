import * as echarts from "echarts/core"
import { BarChart, GaugeChart, LineChart, PieChart, ScatterChart } from "echarts/charts"
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkLineComponent,
  TooltipComponent,
} from "echarts/components"
import { CanvasRenderer } from "echarts/renderers"

echarts.use([
  LineChart,
  BarChart,
  PieChart,
  GaugeChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  MarkLineComponent,
  DataZoomComponent,
  CanvasRenderer,
])

const FONT_STACK =
  '"IBM Plex Sans", "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", ui-sans-serif, system-ui, sans-serif'

function token(name: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback
}

const ink = token("--ink", "#121a1c")
const muted = token("--ink-muted", "#5c6e70")
const line = token("--line", "#dce3e1")
const surface = token("--surface", "#ffffff")

const axis = {
  axisLine: { lineStyle: { color: line } },
  axisTick: { lineStyle: { color: line } },
  axisLabel: { color: muted, fontSize: 11 },
  nameTextStyle: { color: muted, fontSize: 11 },
  splitLine: { lineStyle: { color: line, type: "dashed" as const } },
}

echarts.registerTheme("diagram", {
  color: [
    token("--link", "#0e6b60"),
    token("--signal", "#9a5900"),
    token("--ink-muted", "#5c6e70"),
    "#4a8f86",
    "#b8862b",
  ],
  backgroundColor: "transparent",
  textStyle: { color: ink, fontFamily: FONT_STACK, fontSize: 12 },
  legend: { textStyle: { color: muted, fontSize: 11 }, itemWidth: 14, itemHeight: 8 },
  tooltip: {
    backgroundColor: surface,
    borderColor: line,
    borderWidth: 1,
    textStyle: { color: ink, fontSize: 12 },
    axisPointer: { lineStyle: { color: line } },
  },
  categoryAxis: axis,
  valueAxis: axis,
  line: { symbol: "circle", symbolSize: 5, lineStyle: { width: 2 } },
})

export default echarts
