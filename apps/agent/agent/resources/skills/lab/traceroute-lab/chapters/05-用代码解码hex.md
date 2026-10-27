# 第 5 章 用代码解码 hex

手工会看之后，这一章把解码写成代码，让程序替你读字段。

## 本章目标

学完这一章，你应该能：

1. 把 `bytes` 切片变成整数；
2. 用位移和掩码取出位域字段；
3. 写出 `IPv4.__init__`、`ICMP.__init__`、`UDP.__init__`；
4. 用 `header_len` 动态计算内层包的偏移；
5. 用真实抓包验证解析结果。

这一章是把第 4 章的手工解码“翻译”成代码。不要死记代码，先想清楚每个字段在第几个字节。

---

## 5.1 从 bytes 到整数

`bytes` 对象有两个常用操作：

```python
buf = bytes.fromhex("45 b8 00 38")

buf[0]        # 69（int）
buf[0:1]      # b'E'（bytes）
buf[2:4]      # b'\x00\x38'（bytes）
```

注意：

- `buf[0]` 得到的是 `int`；
- `buf[0:1]` 得到的是 `bytes`，不是 `int`；
- 不能把 `buf[0:4]` 直接当整数用。

### `int.from_bytes`

```python
int.from_bytes(b"\x00\x38", "big")   # 56
int.from_bytes(b"\x38\x00", "big")   # 14336
int.from_bytes(b"\x00\x38", "little")  # 14336
```

第二个参数是字节序。网络协议用 `"big"`（大端序）。

### 位移和掩码

取一个字节的高 4 位和低 4 位：

```python
b = 0x45

b >> 4        # 4
b & 0x0F      # 5
```

取 16 位里的高 3 位：

```python
b6 = 0x40
b7 = 0x00
b6 >> 5       # 2（DF）
```

取 `byte6` 的低 5 位，和 `byte7` 拼成 13 位：

```python
((b6 & 0x1F) << 8) | b7
```

### `struct.unpack`（可选）

你也可以用 `struct`：

```python
import struct
struct.unpack("!H", buf[2:4])[0]   # 56
```

但本教程统一用 `int.from_bytes`，因为它更直观，也不容易把格式字符串写错。

---

## 5.2 大端序

网络字节序是大端序。记住几个真实包里的例子：

| 字节 | 大端序 | 小端序 |
|---|---|---|
| `00 38` | 56 | 14336 |
| `82 9b` | 33435 | 39810 |
| `e5 b9` | 58809 | 47589 |

如果你发现解析出来的端口/长度大得离谱，先检查是不是用错了字节序。

---

## 5.3 实现 `IPv4.__init__`

打开 `traceroute.py`，找到 `class IPv4`。只改 `__init__`，不要改字段声明和 `__str__`。

```python
def __init__(self, buffer: bytes):
    self.version = buffer[0] >> 4
    self.header_len = (buffer[0] & 0x0F) * 4
    self.tos = buffer[1]
    self.length = int.from_bytes(buffer[2:4], "big")
    self.id = int.from_bytes(buffer[4:6], "big")
    self.flags = buffer[6] >> 5
    self.frag_offset = ((buffer[6] & 0x1F) << 8) | buffer[7]
    self.ttl = buffer[8]
    self.proto = buffer[9]
    self.cksum = int.from_bytes(buffer[10:12], "big")
    self.src = util.inet_ntoa(buffer[12:16])
    self.dst = util.inet_ntoa(buffer[16:20])
```

逐行解释：

| 行 | 作用 |
|---|---|
| `buffer[0] >> 4` | 取高 4 位，得到版本号 |
| `(buffer[0] & 0x0F) * 4` | 取低 4 位，乘 4 得到字节长度 |
| `buffer[1]` | TOS，真实包可能是 `0xb8`，本实验不用 |
| `buffer[2:4]` | Total Length，16 位大端 |
| `buffer[4:6]` | Identification，16 位大端 |
| `buffer[6] >> 5` | Flags，高 3 位 |
| `buffer[6]` 低 5 位左移 8 位，再加 `buffer[7]` | Fragment Offset，13 位 |
| `buffer[8]` | TTL |
| `buffer[9]` | Protocol |
| `buffer[10:12]` | Header Checksum |
| `buffer[12:16]` | Source，4 字节 → 点分十进制 |
| `buffer[16:20]` | Destination，4 字节 → 点分十进制 |

`util.inet_ntoa` 是 `socket.inet_ntoa` 的包装，把 4 字节转成 `"192.168.0.99"` 这样的字符串。

> `header_len` 存的是**字节数**（20），不是 IP 头里的 IHL 值（5）。这是 起始代码 注释特别强调的。

> `__str__` 里的 `ofsset` 是 起始代码 自带的拼写错误，不用改。改了也不会影响功能，但没必要。

真实包 A 解析出来应该是：

```text
IPv4 (tos 0xb8, ttl 249, id 64640, flags 0x2, ofsset 0, proto 1, header_len 20, len 56, cksum 0x5e53) 101.226.210.81 > 169.254.68.6
```

---

## 5.4 实现 `ICMP.__init__`

```python
def __init__(self, buffer: bytes):
    self.type = buffer[0]
    self.code = buffer[1]
    self.cksum = int.from_bytes(buffer[2:4], "big")
```

ICMP 头有 4 个字段；本实验只存前 3 个（type、code、checksum），`rest` 那 4 字节不需要存。

| 字段 | 字节 | 说明 |
|---|---|---|
| Type | `buffer[0]` | 11 = Time Exceeded，3 = Destination Unreachable，0 = Echo Reply |
| Code | `buffer[1]` | 要和 Type 一起看：11/0 = TTL expired，3/3 = Port Unreachable |
| Checksum | `buffer[2:4]` | 本实验不校验 |

真实包 A 解析出来是：

```text
ICMP (type 11, code 0, cksum 0x735d)
```

---

## 5.5 实现 `UDP.__init__`

```python
def __init__(self, buffer: bytes):
    self.src_port = int.from_bytes(buffer[0:2], "big")
    self.dst_port = int.from_bytes(buffer[2:4], "big")
    self.len = int.from_bytes(buffer[4:6], "big")
    self.cksum = int.from_bytes(buffer[6:8], "big")
```

| 字段 | 字节 | 说明 |
|---|---|---|
| Source Port | `buffer[0:2]` | 内核分配的源端口（真实包 A 是 58809） |
| Destination Port | `buffer[2:4]` | 你发送时用的目标端口（真实包 A 是 33435） |
| Length | `buffer[4:6]` | 8 + 负载长度（真实包 A 是 13） |
| Checksum | `buffer[6:8]` | 本实验不校验 |

真实包 A 解析出来是：

```text
UDP (src_port 58809, dst_port 33435, len 13, cksum 0x9973)
```

---

## 5.6 把三层串起来

解析一个完整的 ICMP 错误包，不能硬编码 `20`、`28`、`48`，因为 IP 头可能带 options。

把下面这个 `parse_packet` 加到 `traceroute.py` 里（三个类定义之后、`traceroute()` 之前）；`parse_test.py` 只放测试代码。

```python
def parse_packet(buf: bytes):
    if len(buf) < 20:
        raise ValueError("packet too short")

    outer = IPv4(buf)
    icmp_off = outer.header_len
    if len(buf) < icmp_off + 8:
        raise ValueError("packet too short")

    icmp = ICMP(buf[icmp_off:icmp_off + 8])

    # 只有 ICMP 错误包（type 3/11）才带内层 IPv4 + UDP
    if icmp.type not in (3, 11):
        return outer, icmp, None, None

    inner_off = icmp_off + 8
    if len(buf) < inner_off + 20:
        raise ValueError("packet too short")

    inner = IPv4(buf[inner_off:])
    udp_off = inner_off + inner.header_len
    if len(buf) < udp_off + 8:
        raise ValueError("packet too short")

    udp = UDP(buf[udp_off:udp_off + 8])
    return outer, icmp, inner, udp
```

偏移关系：

```text
0                    outer.header_len
|---- 外层 IPv4 ----|---- ICMP 8 字节 ----|---- 内层 IPv4 ----|---- UDP 8 字节 ----|
                    ^                    ^                   ^
                    icmp_off             inner_off           udp_off
```

注意：

- `outer = IPv4(buf)` 只读前 20 字节的固定头；`header_len` 告诉你外层头实际多长；
- `inner = IPv4(buf[inner_off:])` 从内层 IP 头开始读；
- `udp_off` 要用 `inner.header_len`，不能假设 20；
- **真实包 A 的内层 `Total Length` 是 33，但实际只带了 28 字节（20 IP + 8 UDP）**；`parse_packet` 只读 UDP 头 8 字节，不读缺失的 `hello`，所以不会越界；
- 正常情况下外层 `len(buf)` 和 `Total Length` 相等；内层 `Total Length` 可能大于实际携带的字节数。

### 长度检查

上面的 `parse_packet` 已经做了最基本的长度检查：外层 IP、ICMP、内层 IP、内层 UDP 各检查一次。更完整的截断处理属于进阶内容；本教程只保证正常包不崩。

---

## 5.7 自测：解析三个真实包

在 `/root/workspace` 新建 `parse_test.py`（只放测试代码；`parse_packet` 已经在 `traceroute.py` 里）：

```python
import traceroute as t

PKTS = {
    "time_exceeded": bytes.fromhex(
        "45b80038fc804000f9015e5365e2d251"
        "a9fe44060b00735d0000000045000021"
        "fc8040000111ac30c0a8006308080808"
        "e5b9829b000d9973"
    ),
    "port_unreachable": bytes.fromhex(
        "45b8003800000000fa01c1f808080808"
        "a9fe44060303e8230000000045000021"
        "8f374000011118fac0a8006308080808"
        "99f8829a000de535"
    ),
    "echo_reply": bytes.fromhex(
        "45b8005400000000fa01c1dc08080808"
        "a9fe4406000090b600600001e6d9de6a"
        "00000000e1d009000000000010111213"
        "1415161718191a1b1c1d1e1f20212223"
        "2425262728292a2b2c2d2e2f30313233"
        "34353637"
    ),
}

for name, buf in PKTS.items():
    print(f"=== {name}")
    outer, icmp, inner, udp = t.parse_packet(buf)
    print(outer)
    print(icmp)
    if inner is not None:
        print(inner)
        print(udp)
```

运行：

```bash
python3 parse_test.py
```

真实输出（2026-10-26 沙箱抓包）：

```text
=== time_exceeded
IPv4 (tos 0xb8, ttl 249, id 64640, flags 0x2, ofsset 0, proto 1, header_len 20, len 56, cksum 0x5e53) 101.226.210.81 > 169.254.68.6
ICMP (type 11, code 0, cksum 0x735d)
IPv4 (tos 0x0, ttl 1, id 64640, flags 0x2, ofsset 0, proto 17, header_len 20, len 33, cksum 0xac30) 192.168.0.99 > 8.8.8.8
UDP (src_port 58809, dst_port 33435, len 13, cksum 0x9973)
=== port_unreachable
IPv4 (tos 0xb8, ttl 250, id 0, flags 0x0, ofsset 0, proto 1, header_len 20, len 56, cksum 0xc1f8) 8.8.8.8 > 169.254.68.6
ICMP (type 3, code 3, cksum 0xe823)
IPv4 (tos 0x0, ttl 1, id 36663, flags 0x2, ofsset 0, proto 17, header_len 20, len 33, cksum 0x18fa) 192.168.0.99 > 8.8.8.8
UDP (src_port 39416, dst_port 33434, len 13, cksum 0xe535)
=== echo_reply
IPv4 (tos 0xb8, ttl 250, id 0, flags 0x0, ofsset 0, proto 1, header_len 20, len 84, cksum 0xc1dc) 8.8.8.8 > 169.254.68.6
ICMP (type 0, code 0, cksum 0x90b6)
```

如果对不上，回到第 4 章的字段表，一个字段一个字段核对。不要靠“看起来差不多”。

---

## 5.8 本章验收

- [ ] `IPv4` 的 12 个字段全部有值，且类型正确（int / str）；
- [ ] `header_len` 是字节数，不是 IHL；
- [ ] `ICMP` 的 type/code/checksum 正确；
- [ ] `UDP` 的四个字段正确；
- [ ] `parse_packet` 能处理带 options 的 IP 头（偏移用 `header_len` 算，不硬编码）；
- [ ] `parse_test.py` 的三组真实输出与预期一致；
- [ ] 能解释为什么真实包 A 的内层 `Total Length` 是 33，但实际只读到 28 字节。

---

## 5.9 常见误区

| 误区 | 纠正 |
|---|---|
| `buffer[0:4]` 直接当整数 | 它是 bytes；用 `int.from_bytes` |
| `header_len = buffer[0] & 0x0F` | 还要乘 4，单位才是字节 |
| `flags` 用 `buffer[6] & 0x0F` | Flags 是 3 位；用 `>> 5` |
| `frag_offset` 只读 `buffer[7]` | 它是 13 位，要拼上 `buffer[6]` 的低 5 位 |
| 用 `socket.inet_ntoa` 但没 import socket | 可以用 `util.inet_ntoa`，不用额外 import |
| 把 `length` 当成负载长度 | 它是整个 IP 包长度 |
| 硬编码内层偏移 28 / 48 | 用 `header_len` 动态算；有 options 时会错 |
| 解析前不检查长度 | 截断包会让索引越界；现在至少做简单长度检查 |
| 认为内层 `length=33` 就一定有 33 字节 | 真实包只带了 28 字节；只读需要的 UDP 头 |
| 看到 `tos 0xb8` 以为解析错了 | 真实路由器会设置 DSCP/ECN；本实验忽略 |
| 改 `__str__` 的拼写 | `ofsset` 是 起始代码 自带的；不影响功能，别改 |

---

## 下一章

第 6 章用这三个类，写一次完整的探测：设置 TTL、发 UDP、收 ICMP、解析外层源 IP，然后循环 1–30 跳。
