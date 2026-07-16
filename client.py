import socket
import time
import random


def send_order(type, price, quantity):
    # 1. Connect to the C++ Server
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 8080))

    # 2. Format message: "B 100 5"
    message = f"{type} {price} {quantity}"
    print(f"Sending: {message}")

    # 3. Send data (must be bytes)
    client.send(message.encode('utf-8'))

    # 4. Wait for Acknowledgment
    response = client.recv(1024)
    print(f"Server Replied: {response.decode('utf-8')}")

    client.close()


if __name__ == "__main__":
    # Test 1: Add a Seller
    send_order("S", 100, 10)
    time.sleep(1)

    # Test 2: Add a Buyer (they should match)
    send_order("B", 100, 5)

    # Test 3: Spam random orders
    for i in range(20):  # increased to 20 orders
        side = random.choice(["B", "S"])

        if side == "B":
            # Buyers are willing to pay HIGH prices ($100 - $110)
            price = random.randint(100, 110)
        else:
            # Sellers are willing to sell for LOW prices ($90 - $100)
            price = random.randint(90, 100)

        qty = random.randint(1, 10)
        send_order(side, price, qty)
        time.sleep(0.1)  # Faster!
