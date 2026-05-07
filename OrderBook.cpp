#include "OrderBook.h"
#include <iostream>
#include <algorithm>

using namespace std;

void OrderBook::addOrder(Order *order)
{
    if (order->type == OrderType::SELL)
    {
        asks[order->price].push_back(order);
    }
    else
    {
        bids[order->price].push_back(order);
    }
}

void OrderBook::match()
{
    while (true)
    {
        // 1. Check if both sides have orders
        if (asks.empty() || bids.empty())
            break;

        // 2. Get the Best Prices
        auto lowestSellIter = asks.begin(); // Best Seller
        auto highestBuyIter = bids.begin(); // Best Buyer

        double bestAsk = lowestSellIter->first;
        double bestBid = highestBuyIter->first;

        // 3. Can we trade?
        if (bestBid >= bestAsk)
        {
            // Safety check for empty vectors
            if (lowestSellIter->second.empty() || highestBuyIter->second.empty())
            {
                break;
            }

            // Get the orders (First in line)
            Order *askOrder = lowestSellIter->second.front();
            Order *bidOrder = highestBuyIter->second.front();

            // Calculate trade size
            int quantity = min(askOrder->quantity, bidOrder->quantity);

            // Execute Trade
            cout << "MATCH: " << quantity << " shares at $" << bestAsk << endl;

            lastMatchPrice = bestAsk;
            lastMatchQty = quantity;
            // Update quantities
            bidOrder->quantity -= quantity;
            askOrder->quantity -= quantity;

            // 4. CLEANUP (The Critical Fix)

            // If BUYER is filled, remove from BUYER list (highestBuyIter)
            if (bidOrder->quantity == 0)
            {
                highestBuyIter->second.erase(highestBuyIter->second.begin());
                delete bidOrder;
            }

            // If SELLER is filled, remove from SELLER list (lowestSellIter)
            if (askOrder->quantity == 0)
            {
                lowestSellIter->second.erase(lowestSellIter->second.begin());
                delete askOrder;
            }

            // 5. REMOVE EMPTY KEYS

            // If no more Buyers at this price, delete the price level from BIDS
            if (highestBuyIter->second.empty())
            {
                bids.erase(highestBuyIter);
            }

            // If no more Sellers at this price, delete the price level from ASKS
            if (lowestSellIter->second.empty())
            {
                asks.erase(lowestSellIter);
            }
        }
        else
        {
            // Prices don't cross. Market is stable.
            break;
        }
    }
}