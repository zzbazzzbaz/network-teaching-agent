import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const zhDate = new Intl.DateTimeFormat("zh-CN", {
  month: "numeric",
  day: "numeric",
})

const zhTime = new Intl.DateTimeFormat("zh-CN", {
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
})

export function formatDate(iso: string) {
  return zhDate.format(new Date(iso))
}

export function formatTime(iso: string) {
  return zhTime.format(new Date(iso))
}

export function formatDateTime(iso: string) {
  return `${zhDate.format(new Date(iso))} ${zhTime.format(new Date(iso))}`
}

export function relativeDay(iso: string) {
  const now = new Date()
  const date = new Date(iso)
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const startOfDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const diff = Math.round((startOfToday.getTime() - startOfDate.getTime()) / 86_400_000)
  if (diff <= 0) return "今天"
  if (diff === 1) return "昨天"
  if (diff < 7) return "本周"
  return "更早"
}

export function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}
