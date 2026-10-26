import util

# 你的程序应在 [1, TRACEROUTE_MAX_TTL]（含两端）范围内发送 TTL。
# 严格来说 IPv4 支持最大到 255 的 TTL，但实践中这太多了。
# 大多数 traceroute 实现的上限约为 30。单元测试假定你不会修改这个数值。
TRACEROUTE_MAX_TTL = 30

# Cisco 似乎已将 UDP 端口 [33434, 33464] 标准化用于 traceroute。
# 这虽然不是正式标准，但互联网上的某些路由器似乎只对发送到这些端口的
# UDP 数据包回复 time exceeded ICMP 消息。最终你可以随意选择端口，但这个
# 范围似乎能带来更有意思的结果。
TRACEROUTE_PORT_NUMBER = 33434  # Cisco traceroute 的端口号。

# 互联网上的数据包有时会被丢弃。PROBE_ATTEMPT_COUNT 是 traceroute 函数在
# 放弃并继续下一个路由器之前，对单个路由器进行探测的最大尝试次数。
PROBE_ATTEMPT_COUNT = 3

class IPv4:
    # 你只能修改这个类的 __init__() 函数
    version: int
    header_len: int  # 注意这里是字节长度，而不是数据包中的字段值。
    tos: int         # 也称为 DSCP 和 ECN 位。
    length: int      # 数据包的总长度。
    id: int
    flags: int
    frag_offset: int
    ttl: int
    proto: int
    cksum: int
    src: str
    dst: str

    def __init__(self, buffer: bytes):
        pass  # TODO

    def __str__(self) -> str:
        return f"IPv{self.version} (tos 0x{self.tos:x}, ttl {self.ttl}, " + \
            f"id {self.id}, flags 0x{self.flags:x}, " + \
            f"ofsset {self.frag_offset}, " + \
            f"proto {self.proto}, header_len {self.header_len}, " + \
            f"len {self.length}, cksum 0x{self.cksum:x}) " + \
            f"{self.src} > {self.dst}"


class ICMP:
    # 你只能修改这个类的 __init__() 函数
    type: int
    code: int
    cksum: int

    def __init__(self, buffer: bytes):
        pass  # TODO

    def __str__(self) -> str:
        return f"ICMP (type {self.type}, code {self.code}, " + \
            f"cksum 0x{self.cksum:x})"


class UDP:
    # 你只能修改这个类的 __init__() 函数
    src_port: int
    dst_port: int
    len: int
    cksum: int

    def __init__(self, buffer: bytes):
        pass  # TODO

    def __str__(self) -> str:
        return f"UDP (src_port {self.src_port}, dst_port {self.dst_port}, " + \
            f"len {self.len}, cksum 0x{self.cksum:x})"

# 如果愿意，可以随意添加辅助函数

def traceroute(sendsock: util.Socket, recvsock: util.Socket, ip: str) \
        -> list[list[str]]:
    """ 运行 traceroute 并返回发现的路径。

    对每个 TTL 的探测结果调用 util.print_result() 来显示进度。

    参数：
    sendsock -- 这是你将用来发送 traceroute 探测包的 UDP socket。
    recvsock -- 这是你将用来接收 ICMP 响应的 socket。
    ip -- 这是你将要追踪的终端主机的 IP 地址。

    返回：
    一个由列表组成的列表，表示每个被探测的 ttl 所发现的路由器。
    第 i 个列表包含 TTL 探测值为 i+1 时发现的所有路由器。第 i 个列表中
    发现的路由器可以任意顺序排列。如果没有发现任何路由器，第 i 个列表可以
    为空。如果发现了 `ip`，它应作为列表的最后一个元素包含在内。
    """

    # TODO 在此添加你的实现
    for ttl in range(1, TRACEROUTE_MAX_TTL+1):
        util.print_result([], ttl)
    return []


if __name__ == '__main__':
    args = util.parse_args()
    ip_addr = util.gethostbyname(args.host)
    print(f"traceroute to {args.host} ({ip_addr})")
    traceroute(util.Socket.make_udp(), util.Socket.make_icmp(), ip_addr)
