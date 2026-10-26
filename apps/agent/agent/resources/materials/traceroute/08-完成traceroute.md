# 第 8 章 完成 traceroute.py

最后一步：判断什么时候到了目标，并把整条路径返回。

## 本章目标

学完这一章，你应该能：

1. 用 `outer.src == ip` 加 ICMP `3/3` 判断“到了目标”；
2. 解释目标为什么会回 Port Unreachable；
3. 在正确的时机停止循环；
4. 把路径末端写成 `[ip]`；
5. 用真实目标和系统 `traceroute` 完成验收。

这一章不引入进阶异常处理。终点判定用简单的方式：**外层源 IP 等于目标 IP，并确认 ICMP `type=3/code=3`**。

---

## 8.1 怎么知道到了目标

在本实验的理想模型里，目标主机收到一个发往“没人监听的 UDP 端口”的包，会回 **ICMP Port Unreachable**。

这个回包的外层源 IP 就是目标主机。所以最快的判断是：

```python
if outer.src == ip:
    # 可能到了
```

但在真实网络里，**只看 `outer.src == ip` 不够**：目标发来的 Echo Reply（`type=0`）也会让 `outer.src == ip` 成立。2026-10-26 我们在沙箱里真的抓到了 8.8.8.8 的 Echo Reply（见第 3 章包 C）。

最终版至少再加两个条件：

```python
reached = (
    outer.src == ip
    and icmp.type == 3
    and icmp.code == 3
)
```

在接收循环里，用第 5 章的 `parse_packet` 过滤并记录：

```python
reached = False

# 在接收循环里：
outer, icmp, inner, udp = parse_packet(buf)
if outer.proto != 1 or icmp.type not in (3, 11):
    continue
routers.add(outer.src)
if outer.src == ip and icmp.type == 3 and icmp.code == 3:
    reached = True
```

这三行过滤的作用：

- `outer.proto != 1`：不是 ICMP，忽略；
- `icmp.type not in (3, 11)`：不是 Time Exceeded / Port Unreachable，忽略（Echo Reply 的 `type=0` 会在这里被挡掉）；
- `icmp.type == 3 and icmp.code == 3`：确认是 Port Unreachable，才认为“到了”。

> 更严格的做法还可以检查内层 Destination 是目标、内层 UDP 目的端口是本次探测用的端口。本实验不强制；7.9 节有说明。
>
> 被过滤的包会消耗一次接收名额；本实验的 3 次探测可以接受。要更稳，可以用 `while` + 截止时间，但那是进阶内容的范围。

---

## 8.2 为什么目标会回 Port Unreachable

我们故意把探测包发到目标 `33434` 起的端口（本教程用 33434–33436）。这些端口通常没有程序监听。

目标主机的内核收到 UDP 包后（本实验的理想模型；NAT/防火墙也可能发 3/3）：

1. 查有没有程序绑定你发的那个端口（例如 33434）；
2. 没有；
3. 回一个 ICMP Destination Unreachable，Code = Port Unreachable（`type=3, code=3`）。

这个 ICMP 包的“外层源 IP”就是目标主机，所以你能从 `outer.src` 看到它。

### 为什么是 33434

Cisco 把 UDP 端口 `[33434, 33464]` 用作 traceroute 的惯例。不是正式标准，但很多实现沿用。

我们每个 TTL 用 `33434 + i`（i=0,1,2），都落在这个范围里。

### 目标一定会回吗

不一定。以下情况可能不回：

- 防火墙丢弃 ICMP；
- 目标配置为不回复；
- 目标主机不存在；
- 包在路径上丢了。

这时 traceroute 会一直跑到 30 跳，最后没有目标 IP。**这是正常结果，不是代码错。**

---

## 8.3 在循环里停止

在第 7 章的循环里，接收时按 8.1 设置 `reached`；收集完当前 TTL 的 `routers` 后：

```python
routers = sorted(routers)   # 先统一转成 list[str]

if reached:
    routers = [ip]          # 路径末端只保留目标

util.print_result(routers, ttl)
result.append(routers)

if reached:
    break
```

> 不要写 `reached = ip in routers`。那样会漏掉 `icmp.type/code` 检查：目标发来的 Echo Reply 也会让 `ip in routers` 为真，导致在错误的 TTL 提前停止。

为什么把 `routers` 改成 `[ip]`？

- 本实验要求：如果发现了目标，路径末端的子列表应该是 `[ip]`；
- 如果这个 TTL 同时收到了别的路由器（比如目标和其他路由器都回了），按本实验要求，只保留目标；
- 这样返回值更干净，自检也明确。

为什么 `break` 放在 `print_result` 和 `append` 之后？

- 你还要把最后一跳打印出来、写进返回值；
- 如果先 `break`，最后一跳就丢了。

> 注意：`break` 只能跳出当前这一层 `for`。如果你的发送/接收循环和 TTL 循环是嵌套的，要确保 `break` 跳出的是 **TTL 循环**；如果你把 `reached` 判断放进内层接收循环，`break` 只会跳出接收循环，TTL 循环还在跑。可以把停止判断放到 TTL 循环体末尾，或者用 `return result` 直接返回。

---

## 8.4 路径末端与返回值

2026-10-26 在真实沙箱里对 `8.8.8.8` 跑 3 个探测包/TTL，参考实现的返回值是：

```python
[
    [],                                                           # TTL=1
    [],                                                           # TTL=2
    ["11.82.248.76"],                                             # TTL=3
    [],                                                           # TTL=4
    ["10.200.77.129", "10.200.77.137"],                           # TTL=5
    ["101.226.210.70"],                                           # TTL=6
    [],                                                           # TTL=7
    ["101.95.246.149", "101.95.247.117", "101.95.247.157"],       # TTL=8
    ["101.95.224.141", "101.95.224.21", "101.95.224.25"],         # TTL=9
    [],                                                           # TTL=10
    ["202.97.39.21", "202.97.39.57", "202.97.83.38"],             # TTL=11
    ["202.97.25.226", "202.97.58.114", "202.97.6.50"],            # TTL=12
    ["203.22.178.197"],                                           # TTL=13
    ["203.22.178.22"],                                            # TTL=14
    [],                                                           # TTL=15
    ["8.8.8.8"],                                                  # TTL=16，到达
]
```

这是一次真实运行的结果，你的 IP、跳数和多路径数量会变。重点看结构：

- TTL 1、2、4 的子列表是空的；
- TTL 3 这次有 `11.82.248.76`（单 probe 那次 TTL 1–4 全空）；
- 第 5 个列表（TTL=5）有两个路由器；
- 第 16 个列表（TTL=16）是 `["8.8.8.8"]`，之后停止。

> 另一次带 `type/code` 过滤的实测在 TTL 15 到达，路径和 IP 也不同。真实网络会变，不要逐字比对。

这里说的“最后一跳”指**路径末端的子列表**，不是“最后一台路由器”这个对象；本实验要求只保留 `[ip]`。

如果目标是第一跳（比如目标就在同一网络），返回值可能是：

```python
[["8.8.8.8"]]
```

如果目标一直不回（纯示意，不映射真实 TTL）：

```python
# 一共 30 个子列表
[
    [],
    [],
    [],
    # ...
]
```

### 容易错的地方

| 错误 | 结果 |
|---|---|
| 只在收到回包时 append | 子列表错位，后面的 TTL 对不上 |
| 到了目标还继续循环 | 输出多出很多 `*`，返回值多出空列表 |
| 路径末端保留其他路由器 | 不符合本实验的 `[ip]` 要求 |
| `break` 只跳出探测循环 | TTL 循环还在跑，停不下来 |
| 忘了 `return result` | 函数返回 `None` |

---

## 8.5 主程序

`traceroute.py` 末尾已经有：

```python
if __name__ == '__main__':
    args = util.parse_args()
    ip_addr = util.gethostbyname(args.host)
    print(f"traceroute to {args.host} ({ip_addr})")
    traceroute(util.Socket.make_udp(), util.Socket.make_icmp(), ip_addr)
```

你不需要改它，只要保证 `traceroute()` 正常工作。

运行：

```bash
python3 traceroute.py 8.8.8.8
python3 traceroute.py 1.1.1.1
python3 traceroute.py example.com
```

`gethostbyname` 会把域名转成 IPv4 地址。如果域名解析失败，先用 IP 测试：

```bash
python3 traceroute.py 8.8.8.8
```

> `print_result` 会对每个路由器做反向域名解析。如果 DNS 很慢，可能每跳停几秒到几十秒；30 跳下来可能几分钟。这不是你的 traceroute 卡住，而是反向解析慢。可以先用 `traceroute -n` 对照（它不做反向解析），先确认 DNS 是否正常。

---

## 8.6 整理代码

现在你的 `traceroute.py` 可能有：

- `probe_ttl`（第 6 章）；
- 多探测包循环（第 7 章）；
- 终点判断（本章）。

如果所有逻辑都塞在 `traceroute()` 里，会越来越难读。建议拆成几个小函数：

```python
def send_probes(sendsock, ip, ttl, ports):
    ...

def collect_routers(recvsock, count):
    ...

def traceroute(sendsock, recvsock, ip):
    result = []
    for ttl in range(1, TRACEROUTE_MAX_TTL + 1):
        ports = [...]
        send_probes(...)
        routers = collect_routers(...)
        ...
    return result
```

拆函数的标准：

- 一个函数只做一件事；
- 函数名能说明它做什么；
- 不要为了“看起来高级”而拆得太碎；
- 不要修改 `util.py`。

如果你发现代码里有很深的嵌套：

```python
if a:
    if b:
        if c:
            do_something()
```

可以改成“提前返回”：

```python
if not a:
    return
if not b:
    return
if not c:
    return
do_something()
```

这在网络编程里很常见，能让错误处理更清楚。

---

## 8.7 完整实现骨架（对照用）

把第 6、7 章的代码拼起来，结构大致是：

```python
def traceroute(sendsock: util.Socket, recvsock: util.Socket, ip: str) \
        -> list[list[str]]:
    result: list[list[str]] = []

    for ttl in range(1, TRACEROUTE_MAX_TTL + 1):
        # 1. 准备这一跳的端口
        ports = [TRACEROUTE_PORT_NUMBER + i
                 for i in range(PROBE_ATTEMPT_COUNT)]

        # 2. 发探测包
        for port in ports:
            sendsock.set_ttl(ttl)
            sendsock.sendto(b"hello", (ip, port))

        # 3. 收回包，过滤、去重
        routers = set()
        reached = False
        for _ in range(PROBE_ATTEMPT_COUNT):
            if not recvsock.recv_select():
                break
            buf, _ = recvsock.recvfrom()

            outer, icmp, inner, udp = parse_packet(buf)
            if outer.proto != 1 or icmp.type not in (3, 11):
                continue

            routers.add(outer.src)
            if outer.src == ip and icmp.type == 3 and icmp.code == 3:
                reached = True

        # 4. 排序，判断是否到达
        routers = sorted(routers)   # 统一转成 list[str]
        if reached:
            routers = [ip]

        # 5. 打印并记录
        util.print_result(routers, ttl)
        result.append(routers)

        # 6. 到了就停
        if reached:
            break

    return result
```

这段代码把主流程串起来了，已经能跑，可以当作对照答案。建议先自己写，卡住再对照；你还可以自己调整：

- 是否再加内层 Destination / UDP 端口匹配（第 7.9 节）；
- 是否把发送/接收拆成函数；
- 变量名和注释。

> 这段代码已经能跑，但建议自己重打一遍，并解释每一行。复制前先问自己：如果我把 `break` 删掉，会发生什么？如果我把 `reached` 判断改回 `ip in routers`，会发生什么？

---

## 8.8 验收演练（按目标跑）

### 验收 1：目标可达

```bash
python3 traceroute.py 8.8.8.8
```

检查：

- [ ] 输出从 `1:` 开始，TTL 递增；
- [ ] 前几跳可能是 `*`（实测 TTL 1 通常是 `*`；TTL 2/3 有时有、有时没有，如 `11.82.248.76`）；
- [ ] 如果目标回 Port Unreachable，到某一跳出现 `8.8.8.8`；
- [ ] 出现目标后**停止**，不再打印后面的 `*`；
- [ ] 最后一跳是 `8.8.8.8`，不是别的路由器；
- [ ] 中间可以有 `*`，不影响后面的跳。

真实一次运行的片段：

```text
traceroute to 8.8.8.8 (8.8.8.8)
 1: *
 2: *
 3: 11.82.248.76
 4: *
 5: 10.200.77.129
    10.200.77.137
 6: 101.226.210.70
 7: *
 8: 101.95.246.149
    101.95.247.117
    101.95.247.157
 ...
15: *
16: dns.google (8.8.8.8)
```

> 如果 8.8.8.8 完全不回 Port Unreachable，跑满 30 跳也是合法结果；先确认系统 `traceroute -n 8.8.8.8` 能看到目标。系统工具和你的工具到达的 TTL 可能不同（实测系统在 15，Python 在 16）。

### 验收 2：近距离目标

```bash
python3 traceroute.py 1.1.1.1
```

检查：

- [ ] 前几跳和 `8.8.8.8` 可能相同（同一个出口）；
- [ ] 如果目标回 Port Unreachable，目标出现后停止；
- [ ] 输出没有重复 IP（同一子列表内）。

> 1.1.1.1 的路径可能和 8.8.8.8 不同，前几跳也可能全 `*`；以你自己的实际输出为准。系统 traceroute 实测 1.1.1.1 的前几跳也大量是 `*`，不要因为没回包就以为代码错。

### 验收 3：域名

```bash
python3 traceroute.py example.com
```

检查：

- [ ] `gethostbyname` 能解析；
- [ ] 输出里显示解析后的 IP；
- [ ] 如果目标回 Port Unreachable，到目标后停止。

### 验收 4：不可达目标

```bash
python3 traceroute.py 192.0.2.1
```

检查：

- [ ] 可能跑满 30 跳，也可能被网关/中间跳回 unreachable；只要不崩溃即可；
- [ ] 没有崩溃；
- [ ] 如果跑满 30 跳，返回值是 30 个子列表（可能很多为空）；如果提前到达，会更短；
- [ ] 能解释“为什么没有目标 IP 是正常的”。

### 验收 5：返回值

在 `traceroute()` 调用后打印返回值，或者临时写：

```python
result = traceroute(...)
print(result)
```

检查：

- [ ] 类型是 `list[list[str]]`；
- [ ] 第 i 个子列表对应 TTL=i+1；
- [ ] 最后一跳（如果到达）是 `[ip]`；
- [ ] 没有把 `None`、`set`、字符串混进去。

### 验收 6：和系统对照

```bash
traceroute -n 8.8.8.8
python3 traceroute.py 8.8.8.8
```

检查：

- [ ] 前几跳大致相同（可能有差异，正常）；
- [ ] 你的输出没有明显多出/少掉整段；
- [ ] 在目标可达且目标回 Port Unreachable 的前提下，最后一跳是目标。

> 系统 `traceroute` 是 BusyBox wrapper，默认 `-q 1`（每跳 1 个探测包）；你的实现是 3 个。输出不完全一样是正常的。

---

## 8.9 真实网络提醒

- **目标可能不回 Port Unreachable**：防火墙/配置问题；跑满 30 跳是正常结果。
- **eth0/网关是 `169.254.x.x`**：沙箱实测地址是 `169.254.68.6/30`，默认网关 `169.254.68.5`；这不是公网目标，第一台可见路由器可能是 `11.82.x.x`。
- **NAT 会改写内层源地址**：实测 ICMP 错误包的内层源是 `192.168.0.99`，不是你的沙箱 IP；不要用内层源 IP 判断“是不是我的包”。
- **路径会变**：两次运行结果不同很正常；实测系统 `traceroute` 在 TTL 15 到 `8.8.8.8`，Python 参考实现到 TTL 16。
- **`*` 不代表失败**：只代表这一跳没回；实测 TTL 1 通常是 `*`，TTL 2/3 有时有、有时没有（单 probe 那次 TTL 1–4 全 `*`）。
- **多路径是真实存在的**：实测 TTL 5/8/9/11/12 都出现了多个路由器；但每次运行不保证复现。
- **traceroute 是快照**：它显示的是“这次探测看到的路径”，不是网络的永久地图。

---

## 8.10 复盘问题

做完验收后，试着回答：

1. 为什么 TTL=N 能拿到第 N 跳的路由器？3 probe 时第一次回包可能是 TTL=3，单 probe 时可能是 TTL=5；为什么？
2. 为什么目标收到 UDP 包后回的是 ICMP，而不是 UDP？
3. 为什么 ICMP 错误包里要带内层 IPv4 + UDP？
4. 为什么同一个 TTL 要发 3 个探测包？
5. 为什么最后一跳是 `[ip]`，而不是“所有回包 IP”？
6. 如果目标不回 Port Unreachable，程序会怎样？
7. 如果把 `set_ttl` 放在 `sendto` 之后，会发生什么？
8. 如果把 `recv_select` 换成直接 `recvfrom`，可能会怎样？

如果你能不看教程回答这 8 个问题，说明你真正理解了。

---

## 8.11 最终检查清单

- [ ] 目标可达且目标回 Port Unreachable 时，输出在目标处停止；
- [ ] 到达目标时，路径末端是 `[ip]`；
- [ ] 不可达时通常跑满 30 跳（也可能提前遇到网关 unreachable），不崩溃；
- [ ] 返回值结构正确；
- [ ] 同一子列表无重复；
- [ ] 知道 TTL 1–4 可能是 `*`，不会因此以为代码错；
- [ ] 用 3 个以上目标跑过；
- [ ] 和系统 `traceroute` 对照过；
- [ ] 没有修改 `util.py`；
- [ ] 能解释第 8.10 节的 8 个问题。

---

## 8.12 常见误区

| 误区 | 纠正 |
|---|---|
| 只看 `outer.src == ip`，不加 type/code | 目标发来的 Echo Reply 会让它在错误的 TTL 提前停止；至少加 `icmp.type == 3 and icmp.code == 3` |
| 到了目标还继续跑 | `break` 要跳出 TTL 循环；注意别只跳出探测循环 |
| 路径末端保留其他路由器 | 本实验要求路径末端是 `[ip]` |
| 先 `break` 再 `append` | 路径末端会丢；先打印/append，再 break |
| 目标不回就以为代码错 | 防火墙/配置可能不回；跑满 30 跳是正常结果 |
| 从 TTL=1 开始，没回包就以为代码错 | 单 probe 实测 TTL 1–4 全 `*`；3 probe 可能在 TTL 3 就看到；先用 TTL=8 验证 |
| 把网关当成目标 | `169.254.68.5`/`169.254.68.6` 是沙箱链路地址；内层 `192.168.0.99` 是 NAT 改写，不是目标 |
| 用内层源 IP 判断是不是自己的探测 | NAT 会改写；用内层目的 IP + UDP 目的端口 |
| 两次输出不一样就以为有 bug | 路径会变；看结构，不要逐字比对 |
| 忘了 `return result` | 函数返回 `None` |
| 为了让输出“好看”改 `print_result` | `util.py` 不要改；输出格式不是自检重点 |

---

## 完成

到这里，你已经完成了本实验的核心：

- 理解 TTL 和逐跳探测；
- 用 Python socket 发包/收包；
- 手工和代码解析 IPv4/UDP/ICMP；
- 处理多路径和重复探测；
- 在目标处停止并返回路径。

如果你想继续，可以学习进阶内容，处理非法包、丢包、重复包、迟到包。但在那之前，**先备份一份能跑的 `traceroute.py`**，确保本实验的版本不会被改坏。
