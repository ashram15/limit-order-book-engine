#include <iostream>
#include <string>
#include <sstream>
#include <cstring>      // For memset
#include <sys/socket.h> // Core socket functions
#include <netinet/in.h> // For sockaddr_in
#include <arpa/inet.h>  // For htons()
#include <unistd.h>     // For close()
#include "OrderBook.h"

// Define the port we want to listen on
#define PORT 8080
#define BUFFER_SIZE 1024

int main()
{
    // 1. Initialize OrderBook
    OrderBook book;
    int orderIdCounter = 1;

    // 2. Create Socket (The "Phone")
    // AF_INET = IPv4, SOCK_STREAM = TCP
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd == 0)
    {
        std::cerr << "Socket failed" << std::endl;
        return -1;
    }

    // 3. Bind Socket to Port (Assign phone number 8080)
    struct sockaddr_in address;
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY; // Listen on all interfaces (localhost)
    address.sin_port = htons(PORT);

    // Force attach socket to port (prevents "Address already in use" errors)
    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    if (::bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0)
    {
        std::cerr << "Bind failed" << std::endl;
        return -1;
    }

    // 4. Start Listening
    if (listen(server_fd, 3) < 0)
    {
        std::cerr << "Listen failed" << std::endl;
        return -1;
    }

    std::cout << ">>> TRADING ENGINE LISTENING ON PORT " << PORT << " <<<" << std::endl;

    // 5. Accept Connections Loop (The Server Loop)
    while (true)
    {
        int new_socket;
        int addrlen = sizeof(address);

        // This line BLOCKS (waits) until a client connects
        if ((new_socket = accept(server_fd, (struct sockaddr *)&address, (socklen_t *)&addrlen)) < 0)
        {
            std::cerr << "Accept failed" << std::endl;
            continue;
        }

        // Read data from client
        char buffer[BUFFER_SIZE] = {0};
        read(new_socket, buffer, BUFFER_SIZE);

        std::cout << "Received Command: " << buffer << std::endl;

        // 6. PARSE THE COMMAND (Protocol: "TYPE PRICE QUANTITY")
        // Example: "B 100 5"  (Buy 5 shares at $100)
        // Example: "S 102 10" (Sell 10 shares at $102)
        std::stringstream ss(buffer);
        char typeChar;
        double price;
        int quantity;

        ss >> typeChar >> price >> quantity;

        OrderType type = (typeChar == 'B') ? OrderType::BUY : OrderType::SELL;

        // Create and Add Order
        Order *newOrder = new Order(orderIdCounter++, price, quantity, type);
        book.addOrder(newOrder);

        // Run Matcher
        book.match();

        // Send Response back to Python
        std::string response;
        if (book.lastMatchPrice > 0)
        {
            response = "MATCH " + std::to_string(book.lastMatchPrice) + " " +
                       std::to_string(book.lastMatchQty) + "\n";
            book.lastMatchPrice = 0;
            book.lastMatchQty = 0;
        }
        else
        {
            response = "Order Processed\n";
        }
        send(new_socket, response.c_str(), response.length(), 0);

        // Close connection (Simple approach: One connection per order)
        close(new_socket);
    }

    return 0;
}