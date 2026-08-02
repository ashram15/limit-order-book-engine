import argparse
import random
import socket
import time


def send_order(host: str, port: int, side: str, price: int, quantity: int) -> None:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((host, port))
        message = f"{side} {price} {quantity}"
        client.sendall(message.encode("utf-8"))
        client.recv(1024)
    finally:
        client.close()


def generate_order(i: int, crosses: bool) -> tuple[str, int, int]:
    if crosses:
        if i % 2 == 0:
            return "S", 100, 10
        return "B", 100, 10

    side = random.choice(["B", "S"])
    if side == "B":
        price = random.randint(100, 110)
    else:
        price = random.randint(90, 100)
    quantity = random.randint(1, 10)
    return side, price, quantity


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot throughput benchmark for the matching engine")
    parser.add_argument("--host", default="127.0.0.1", help="Engine host")
    parser.add_argument("--port", type=int, default=8080, help="Engine port")
    parser.add_argument("--orders", type=int, default=5000,
                        help="Measured orders")
    parser.add_argument("--warmup", type=int, default=200,
                        help="Warmup orders excluded from timing")
    parser.add_argument(
        "--crosses",
        action="store_true",
        help="Use alternating buy/sell orders at the same price so the engine actually matches on each pair",
    )
    args = parser.parse_args()

    total_orders = args.warmup + args.orders
    random.seed(42)

    for i in range(args.warmup):
        side, price, quantity = generate_order(i, args.crosses)
        send_order(args.host, args.port, side, price, quantity)

    start = time.perf_counter()
    for i in range(args.orders):
        side, price, quantity = generate_order(i, args.crosses)
        send_order(args.host, args.port, side, price, quantity)
    elapsed = time.perf_counter() - start

    orders_per_second = args.orders / elapsed if elapsed > 0 else float("inf")
    avg_ms = (elapsed / args.orders) * 1000 if args.orders > 0 else 0.0

    print(f"Benchmark complete")
    print(f"  warmup orders : {args.warmup}")
    print(f"  measured orders: {args.orders}")
    print(f"  total orders   : {total_orders}")
    print(f"  elapsed        : {elapsed:.4f}s")
    print(f"  throughput     : {orders_per_second:,.2f} orders/sec")
    print(f"  avg latency    : {avg_ms:.3f} ms/order")


if __name__ == "__main__":
    main()
