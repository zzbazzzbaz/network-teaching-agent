import type { Mode } from "@/shared/api/types"

export const STARTERS: Record<Mode, string[]> = {
  learn: [
    "TCP 为什么需要三次握手？",
    "子网掩码和广播地址怎么算？",
    "HTTP/2 的多路复用解决了什么？",
  ],
  lab: [
    "我想用 tcpdump 观察一次 TCP 握手。",
    "怎么确认一个端口有没有在监听？",
    "想写一个最小的 UDP 回声服务器。",
  ],
}
