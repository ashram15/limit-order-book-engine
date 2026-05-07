#include <map>
#include <vector>
#include "Order.h"

class OrderBook
{
    // ASKS (Sellers): They want High prices, but we match the LOWEST first.
    // std::map sorts Low -> High by default.
    // we need to find lowest seller price to buy from.
    // Perfect! .begin() is the cheapest seller.
    std::map<double, vector<Order *>> asks;

    // BIDS (Buyers): They want Low prices, but we match the HIGHEST first.
    // std::map sorts Low -> High by default.
    // We need High -> Low. We use 'std::greater' to reverse the sort.
    // Now .begin() is the highest bidder (most aggressive buyer)
    // we need to find the highest buyer price to sell to, not the lowest (which is what .begin() would give us by default).
    std::map<double, vector<Order *>, greater<double>> bids;

public:
    double lastMatchPrice = 0;
    int lastMatchQty = 0;
    void addOrder(Order *order);
    void match();
};
