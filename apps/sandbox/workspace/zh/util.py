import argparse
import select
import socket
import typing
import sys
import platform

# === 请勿修改 ===

# SELECT_TIMEOUT 表示在没有收到任何数据包的情况下，select 调用会阻塞多少秒。
# 这个数值越小，我们的代码就越可能提前放弃，即使数据包正在到达，也会误判路由器
# 不会响应。数值越大，在探测无响应的路由器时，代码运行得就越慢。实践中，2 秒
# 能达到较合理的效果。测试并不依赖这个数值取多少，它只影响实际运行。
SELECT_TIMEOUT = 2

IPPROTO_ICMP = socket.IPPROTO_ICMP

IPPROTO_UDP = socket.IPPROTO_UDP


def ntohl(x):
    return socket.ntohl(x)


def htonl(x):
    return socket.htonl(x)


def htons(x):
    return socket.htons(x)


def ntohs(x):
    return socket.ntohs(x)


def inet_aton(x):
    return socket.inet_aton(x)


def inet_ntoa(x):
    return socket.inet_ntoa(x)


def inet_pton(x, y):
    return socket.inet_pton(x, y)


def inet_ntop(x, y):
    return socket.inet_ntop(x, y)


def gethostbyname(host: str):
    return socket.gethostbyname(host)


class Socket:
    __sock: socket.socket

    # 创建一个用于发送 traceroute 探测包的 UDP socket。起始代码会替你调用
    # 这个方法。
    @classmethod
    def make_udp(cls):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                             socket.IPPROTO_UDP)
        return cls(sock)

    # 创建一个用于接收 ICMP 响应的 ICMP socket。起始代码会替你调用这个方法。
    @classmethod
    def make_icmp(cls):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                 socket.IPPROTO_ICMP)
        except PermissionError:
            if platform.system() != "Darwin":
                print("PermissionError: please run as root.")
                sys.exit(1)

            # 在 MacOS 上，可以创建非特权的 ICMP socket。原生 raw socket 更
            # 可取，因为它更稳健且跨平台，但既然创建失败了，也不妨试一下。
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
                                 socket.IPPROTO_ICMP)
        return cls(sock)

    def __init__(self, sock: socket.socket):
        self.__sock = sock

    # 只在 UDP socket 上调用。把此 socket 之后发送的所有数据包的 TTL 改为
    # 给定的值。
    def set_ttl(self, ttl: int):
        return self.__sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)

    # 只在 UDP socket 上调用。向 `address` 发送一个 UDP 数据包。
    # `address` 是一个元组，包含 IPv4 地址的字符串表示和目标端口。
    # UDP 数据包的负载是 `b`。UDP 包头由 `sendto` 函数根据所提供的信息
    # 创建。
    #
    # 参见：https://docs.python.org/3/library/socket.html#socket.socket.sendto
    def sendto(self, b: bytes, address: typing.Tuple[str, int]) -> int:
        return self.__sock.sendto(b, address)

    # 只在 ICMP socket 上调用。从 socket 接收一个数据包。
    # 返回一个 `bytes` 对象，包含整个数据包（包括 IP 头）。同时返回该数据包
    # 发送者的地址。
    #
    # 参见：https://docs.python.org/3/library/socket.html#socket.socket.recvfrom
    def recvfrom(self) -> typing.Tuple[bytes, typing.Tuple[str, int]]:
        return self.__sock.recvfrom(4096)

    # 只在 ICMP socket 上调用。阻塞，直到此 socket 有可供 `recvfrom()` 接收的
    # 数据包，或者 `SELECT_TIMEOUT` 超时。如果有可供 `recvfrom()` 读取的数据包，
    # 则返回 true。
    #
    # 参见：https://docs.python.org/3/library/select.html#select.select
    def recv_select(self) -> bool:
        rlist, _, _ = select.select([self.__sock], [], [], SELECT_TIMEOUT)
        return rlist != []


def print_result(routers: list[str], ttl: int):
    if len(routers) == 0:
        print(f"{ttl: >2}: *")
        return

    for i, router in enumerate(routers):
        if i == 0:
            preamble = f"{ttl: >2}:"
        else:
            preamble = "   "

        try:
            hostname, _, _ = socket.gethostbyaddr(router)
            print(f"{preamble} {hostname} ({router})")
        except socket.herror:
            print(f"{preamble} {router}")


def parse_args():
    parser = argparse.ArgumentParser(prog='cs168 Traceroute')
    parser.add_argument('host')
    return parser.parse_args()
