FROM ubuntu:22.04
RUN apt-get update && apt-get install -y g++
WORKDIR /app
COPY Order.h OrderBook.h OrderBook.cpp main.cpp ./
RUN g++ -std=c++11 main.cpp OrderBook.cpp -o matching-engine
EXPOSE 8080
CMD ["./matching-engine"]