# 第 2 章 Python socket 编程

这一章只做一件事：用 Python 把第一个探测包发出去，并把它收回来。

## 本章目标

学完这一章，你应该能：

1. 用 Python 创建一个 UDP socket；
2. 用 `sendto` 发出一个 UDP 包，并知道哪些头部是内核帮你补的；
3. 用 `setsockopt` 设置 TTL；
4. 用 raw ICMP socket 接收路由器的回包；
5. 用 `select` 等待回包，而不是傻等；
6. 读懂 `util.py` 里每个方法的用途。

这一章不解析回包，只要求“能发出去、能收回来”。解析是第 4、5 章的事。

---

## 2.1 socket 是什么

socket 可以理解成“一台机器上的一个通信端点”。Python 里你拿到的是一个 `socket` 对象，底层通过文件描述符（fd）访问网络。

创建一个 socket 时，要告诉操作系统三件事：

| 参数 | 本实验的值 | 含义 |
|---|---|---|
| 地址族 | `AF_INET` | 使用 IPv4 |
| socket 类型 | `SOCK_DGRAM` | 使用数据报（UDP） |
| 协议 | `IPPROTO_UDP` | 明确指定 UDP |

对应的代码：

```python
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
```

> 不要用 `SOCK_STREAM`。那是 TCP，不是本实验要的 UDP。

---

## 2.2 发一个 UDP 包

UDP 是无连接的：你不需要先“建立连接”，直接把数据发出去就行。

```python
s.sendto(b"hello", ("8.8.8.8", 33434))
```

这里发生了什么？

1. 你只提供了**负载** `b"hello"`；
2. 操作系统帮你补上 UDP 头（源端口、目标端口、长度、校验和）；
3. 操作系统再帮你补上 IPv4 头（源 IP、目标 IP、TTL、协议号等）；
4. 最后交给网卡发出去。

`sendto` 的返回值是**发送的字节数**，不是错误码。比如发 `b"hello"`，返回 `5`。

目标地址是一个元组：

```python
(target_ip, target_port)
```

在本实验里，`target_ip` 是你要追踪的目标，`target_port` 一般是 `TRACEROUTE_PORT_NUMBER`（33434）。

> 源端口不用你管，内核会自动分配一个临时端口。这个源端口会出现在 ICMP 错误包的“内层 UDP 头”里；但匹配探测包时，优先看**内层目的端口**（你发送时指定的 33434 + i），因为 NAT 可能改写源地址/源端口。

---

## 2.3 设置 TTL

TTL 是 IP 头部的字段，不是 UDP 头部的字段。设置它要用 `setsockopt`：

```python
s.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, 1)
```

三个参数的含义：

| 参数 | 值 | 含义 |
|---|---|---|
| level | `IPPROTO_IP` | 要改的是 IP 层选项 |
| option | `IP_TTL` | 选项名：TTL |
| value | `1` | 新的 TTL |

**关键点：这个设置会影响这个 socket 之后发送的所有包，不是只影响下一个包。**

所以如果你要循环发 TTL=1、2、3……必须在**每次发送前**重新设置：

```python
for ttl in (5, 6, 8):
    s.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
    s.sendto(b"hello", ("8.8.8.8", 33434))
```

如果你先发再设 TTL，第一个包用的就是默认值（通常是 64），不会在第二跳过期。这是非常常见的 bug。

---

## 2.4 收 ICMP 回包：为什么需要另一个 socket

我们用 UDP socket 发探测包，但路由器回的是 **ICMP** 包，不是 UDP 包。

一个 UDP socket 只能收到发给它自己端口的 UDP 数据；它收不到 ICMP 错误。所以要另外创建一个 raw ICMP socket：

```python
r = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
```

| 参数 | 值 | 含义 |
|---|---|---|
| 地址族 | `AF_INET` | IPv4 |
| 类型 | `SOCK_RAW` | 原始 socket，能拿到 IP 层及以上的字节 |
| 协议 | `IPPROTO_ICMP` | 只收 ICMP |

### 为什么需要 root

创建 raw socket 需要 `CAP_NET_RAW` 权限。普通用户没有这个权限，所以课程说明会让你用 `sudo`：

```bash
sudo python3 traceroute.py ...
```

但在我们的沙箱里，你本来就是 `root`，**不需要 `sudo`**，直接跑：

```bash
python3 traceroute.py ...
```

如果你在本地 Linux 跑，通常需要 `sudo`；macOS 可能走 `util.py` 的非特权 fallback（`SOCK_DGRAM + IPPROTO_ICMP`），但返回的 `buf` 起点可能和 Linux raw socket 不同，先打印 hex 确认再解析。

### `recvfrom` 返回什么

```python
buf, address = r.recvfrom(4096)
```

- `buf`：收到的原始字节，**包含 IPv4 头**；
- `address`：发送方的地址，一个 `(ip, port)` 元组。

在 Linux 上，raw ICMP socket 的 `buf` 从 IPv4 头开始，不含以太网头。这一点在第 3 章会反复用到。

`4096` 是缓冲区大小。ICMP 错误包通常只有几十到几百字节，4096 足够。

---

## 2.5 等待回包：为什么用 `select`

如果你直接调用 `recvfrom()`，而这时没有包，它会**阻塞**——程序卡在那里，直到有包来。如果路由器永远不回，你的程序就永远卡住。

所以要先问操作系统：“现在有包吗？”

```python
import select

rlist, _, _ = select.select([r], [], [], 2)
if rlist:
    buf, address = r.recvfrom(4096)
else:
    print("2 秒内没有回包")
```

`select.select` 的参数：

| 参数 | 含义 |
|---|---|
| 第一个列表 | 要等的“可读” socket |
| 第二个列表 | 要等的“可写” socket（本实验不用） |
| 第三个列表 | 要等的“异常” socket（本实验不用） |
| 第四个参数 | 超时秒数 |

返回值 `rlist` 是“已经可读”的 socket 列表。如果为空，说明超时了。

`util.py` 已经把它封装成：

```python
recvsock.recv_select()  # 有包返回 True，超时返回 False
```

超时时间由 `SELECT_TIMEOUT = 2` 控制。

> 记住这个顺序：**先 `recv_select()`，返回 True 再 `recvfrom()`。**  
> 如果先 `recvfrom()`，在没有包时可能阻塞，或者在某些平台上抛异常。

---

## 2.6 读一遍 `util.py`

打开 `/root/workspace/util.py`，找到 `class Socket`。你不需要修改它，但要知道每个方法做什么：

| 方法 | 作用 | 用在哪 |
|---|---|---|
| `Socket.make_udp()` | 创建 UDP socket | 发送探测包 |
| `Socket.make_icmp()` | 创建 ICMP socket | 接收回包 |
| `sendsock.set_ttl(ttl)` | 设置后续包的 TTL | 每次发送前 |
| `sendsock.sendto(b, (ip, port))` | 发送 UDP 包 | 每次探测 |
| `recvsock.recv_select()` | 等回包，超时返回 False | 每次接收前 |
| `recvsock.recvfrom()` | 接收一个包，返回 `(bytes, address)` | `recv_select()` 为 True 后 |
| `util.print_result(routers, ttl)` | 按 traceroute 格式打印一跳 | 每个 TTL 结束时 |

还有几个常量和函数：

| 名称 | 含义 |
|---|---|
| `SELECT_TIMEOUT = 2` | `recv_select()` 的等待秒数 |
| `IPPROTO_ICMP` / `IPPROTO_UDP` | 协议号常量 |
| `ntohl` / `htonl` / `htons` / `ntohs` | 字节序转换 |
| `inet_ntoa` / `inet_aton` | IP 地址字符串 ↔ 4 字节 |
| `parse_args()` | 解析命令行参数 `host` |
| `gethostbyname(host)` | 域名 → IPv4 地址 |

`util.py` 顶部的注释写着 `# === Do Not Modify ===`。不要改它。如果你需要辅助函数，加在 `traceroute.py` 里。

---

## 2.7 第一个实验：`probe_once.py`

在 `/root/workspace` 新建 `probe_once.py`：

```python
import util

TARGET = "8.8.8.8"
TTL = 8
PORTS = (33434, 33435, 33436)

sendsock = util.Socket.make_udp()
recvsock = util.Socket.make_icmp()

# 1. 设置 TTL
sendsock.set_ttl(TTL)

# 2. 最多试 3 个端口；真实网络一次探测可能丢
for port in PORTS:
    sent = sendsock.sendto(b"hello", (TARGET, port))
    print(f"sent {sent} bytes to port {port}")

    # 3. 等回包，最多 2 秒
    if recvsock.recv_select():
        buf, addr = recvsock.recvfrom()
        print("reply from:", addr)
        print("length:", len(buf))
        print("first 32 bytes:", buf[:32].hex())
        break
else:
    print("no reply after 3 probes")
```

运行：

```bash
python3 probe_once.py
```

真实沙箱输出（2026-10-26）：

```text
sent 5 bytes to port 33434
reply from: ('101.95.219.17', 0)
length: 56
first 32 bytes: 45b80038020a0000f701928d655fdb11a9fe44060b00e6220000000045000021
```

说明：

- `sent 5 bytes`：`b"hello"` 是 5 字节；
- `reply from` 的 IP 通常是**回 ICMP 的路由器**；也可能是目标或其他 ICMP。先看 ICMP type 和内层 UDP 端口再判断；
- `length: 56`：回包总长度（外层 IP + ICMP + 内层 IP + UDP，没有 payload）；
- `first 32 bytes`：就是第 3 章要拆的 hex；
- 这个包的完整 hex 里，内层源 IP 是 `192.168.0.99`，不是你的沙箱 `169.254.68.6`；沙箱 NAT 改写了它，后面会讲。

> 这是 2026-10-26 的一次真实抓包。TTL=8 的同一位置可能有多个等价路由器，`reply from` 也可能是 `101.95.246.149`（3 probe 版本还可能看到 `101.95.247.117`、`101.95.247.157`）；这很正常。

### 情况 B：没有回包

```text
sent 5 bytes to port 33434
sent 5 bytes to port 33435
sent 5 bytes to port 33436
no reply after 3 probes
```

可能原因：

1. 这个 TTL 的路由器不回复 ICMP；
2. 沙箱出网限制；
3. 目标/网络把包丢了；
4. 你发的端口或 TTL 不对。

每个端口最多等 2 秒，3 个端口最坏就是 6 秒。

真实沙箱里，TTL=1/2 经常没有回包；TTL=5 曾有 2 个路由器同时回复（`10.200.77.129`、`10.200.77.137`），TTL=8 的 33434 也稳定拿到过回包。可以先试：

```python
TTL = 8
PORTS = (33434, 33435, 33436)
```

如果没回，换 TTL `5`、`6`、`11`、`12`。如果系统 `traceroute -n 8.8.8.8` 也全是 `*`，那才是网络环境问题。

---

## 2.8 动手：改变 TTL

把 `TTL` 从 8 改成 5、6、11、12，再跑一次。观察：

1. `reply from` 的 IP 变了吗？
2. `length` 变了吗？
3. `first 32 bytes` 的前 20 字节（外层 IPv4 头）有什么变化？

真实沙箱里：

- TTL=1/2 通常没有回包（别从这里开始判断代码错）；
- TTL=5 可能落在有多个等价路由器的位置（完整实现会发 3 个探测包，才容易看到多个 IP）；
- TTL=8/11/12 可能回来不同路由器；
- 每次运行的 IP ID、校验和、源端口都会变。

> 不要一次改成 30 然后盯着屏幕等。每次只改一个变量，观察差异。

---

## 2.9 本章验收

- [ ] 能说出 `AF_INET`、`SOCK_DGRAM`、`IPPROTO_UDP` 各自的含义；
- [ ] 能解释 `sendto` 的返回值是什么，以及哪些头部是内核补的；
- [ ] 能解释为什么设置 TTL 要在每次发送前做；
- [ ] 能解释为什么发 UDP 却要另开一个 ICMP socket；
- [ ] 能解释 `recv_select()` 和 `recvfrom()` 的先后顺序；
- [ ] `probe_once.py` 能跑通，至少拿到一次回包（或能说明为什么拿不到）；
- [ ] 知道 TTL=1/2 没回包是正常的，不会因此以为代码错。

---

## 2.10 常见误区

| 误区 | 纠正 |
|---|---|
| 用 `SOCK_STREAM` 创建 UDP socket | 应该用 `SOCK_DGRAM` |
| 忘记 `.encode()` | `sendto` 要 bytes；字符串要先 `b"..."` 或 `.encode()` |
| 先 `sendto` 再 `set_ttl` | TTL 设置必须在发送前 |
| 以为 `set_ttl` 只影响下一个包 | 它影响该 socket 之后的所有包 |
| 直接 `recvfrom()` 不等 `select` | 可能阻塞或抛异常 |
| 从 TTL=1 开始，没回包就以为代码错 | 沙箱里 TTL=1/2 经常没有回包；先试 TTL=5/6 |
| 把 `reply from` 的 IP 当成目标 | 那是回包的路由器/主机地址，不一定是目标 |
| `recvfrom(4096)` 的 4096 是包长度 | 那是缓冲区大小，不是实际包长；实际长度看返回值 |
| 在沙箱里加 `sudo` | 沙箱已经是 root；`sudo` 可能不存在 |

---

## 下一章

第 3 章把 `buf` 拆开：外层 IPv4、ICMP、内层 IPv4、内层 UDP，各占多少字节，分别说明什么。
