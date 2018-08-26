#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from __future__ import print_function

from bravado.client import SwaggerClient
import bravado.exception

import math
from order import Order, BuyOrder, SellOrder
from cache import Cache
from route import Route

MAX_CAPITAL = 15000000
MAX_CARGO = 14610

MARKET_DATA_FILE = "market_data"
ITEM_DATA_FILE = "item_data"
SYSTEM_DATA_FILE = "system_data"

'''
TODO

- Cache system IDs to Names

- Create map of systems to determine route as a cache?

- Consider current ship location when determining best route

'''


class Transaction:

  def __init__(self, o1, o2):
    self.buy_order = o1
    self.sell_order = o2

  def revenue(self):
    return self.buy_order.price - self.sell_order.price

  def distance(self, c):
    return len(Route(c, self.buy_order.system_id, self.sell_order.system_id).get_distance())

  def __repr__(self):
    return str(self)

  def __str__(self):
    return "BUY: " + str(self.buy_order) + " SELL: " + str(self.sell_order) + " REVENUE: " + str(self.revenue())


def main():
  # create the market cache object with a TTL of 15 minutes
  market_cache = Cache(MARKET_DATA_FILE, ttl=900)

  # create the item and system cache objects
  item_cache = Cache(ITEM_DATA_FILE)
  system_cache = Cache(SYSTEM_DATA_FILE)

  # create the API client
  client = SwaggerClient.from_url('https://esi.tech.ccp.is/latest/swagger.json')

  transactions = []

  # if the cache is invalid, get data from the API
  if not market_cache.data:
    print("Cache is invalid, getting orders from API")
    i = 1
    while True:
      print("Getting Buy Order Pages for Page: " + str(i))
      buyOrders = client.Market.get_markets_region_id_orders(
                  datasource='tranquility',
                  region_id=10000016,
                  order_type='buy',
                  page=i
                  )
      buyOrderResult = buyOrders.result()
      headers = buyOrders.response().incoming_response.headers
      buyOrderPages = int(headers['X-Pages'])
      print("Found {0} buy order pages".format(buyOrderPages))

      for order in buyOrderResult:
        type_id = order['type_id']

        # new type, add to orders
        if not type_id in market_cache.data:
          market_cache.data[type_id] = {}
          market_cache.data[type_id]["buy_orders"] = [BuyOrder(type_id, order["price"], order["volume_remain"], order["system_id"])]
          market_cache.data[type_id]["sell_orders"] = []
        else:
          #print("BUY ORDER LENGTH " + str(len(market_cache.data[type_id]["buy_orders"])))
          found = False
          for x in range(0, len(market_cache.data[type_id]["buy_orders"])):
            #print("CURRENT ORDER SYSTEM: " + str(order["system_id"]))
            #print("OTHER ORDER SYSTEM: " + str(market_cache.data[type_id]["buy_orders"][x].system_id))
            if market_cache.data[type_id]["buy_orders"][x].system_id == order["system_id"] and market_cache.data[type_id]["buy_orders"][x].price == order["price"]:
              found = True
              market_cache.data[type_id]["buy_orders"][x].vol_remain += order["volume_remain"]
          if not found:
            market_cache.data[type_id]["buy_orders"].append(BuyOrder(type_id, order["price"], order["volume_remain"], order["system_id"]))

      if i >= buyOrderPages:
        break
      i += 1

    i = 1
    while True:
      print("Getting Sell Order Pages for Page: " + str(i))
      sellOrders = client.Market.get_markets_region_id_orders(
                  datasource='tranquility',
                  region_id=10000016,
                  order_type='sell',
                  page=i
                  )
      sellOrderResult = sellOrders.result()
      headers = sellOrders.response().incoming_response.headers
      sellOrderPages = int(headers['X-Pages'])
      print("Found {0} sell order pages".format(sellOrderPages))

      for order in sellOrderResult:
        type_id = order['type_id']

        if type_id in market_cache.data:
          found = False
          for x in range(0, len(market_cache.data[type_id]["sell_orders"])):
            if market_cache.data[type_id]["sell_orders"][x].system_id == order["system_id"] and market_cache.data[type_id]["sell_orders"][x].price == order["price"]:
              found = True
              market_cache.data[type_id]["sell_orders"][x].vol_remain += order["volume_remain"]
          if not found:
            market_cache.data[type_id]["sell_orders"].append(SellOrder(type_id, order["price"], order["volume_remain"], order["system_id"]))

      if i >= sellOrderPages:
        break
      i += 1

  # store transactions in an array to postprocess
  for order in market_cache.data:
    #print(market_cache.data[order])
    for buy_order in market_cache.data[order]["buy_orders"]:
      for sell_order in market_cache.data[order]["sell_orders"]:
        transaction = Transaction(buy_order, sell_order)

        # remove the transaction if it would yield negative revenue
        if transaction.revenue() <= 0:
          continue

        # if we cannot afford the order, continue
        if transaction.buy_order.price > MAX_CAPITAL:
          continue

        # if the buy order isnt enough for the sell order
#        if transaction.buy_order.vol_remain < transaction.sell_order.vol_remain:
#          continue

        transactions.append(transaction)

  print("Found {0} transactions".format(len(transactions)))

  best_transaction = None
  best_revenue_per_hop = 0
  best_items_per_run = 0

  for transaction in transactions:
    if best_transaction is None:
      best_transaction = transaction

    volume = transaction.buy_order.get_volume(client, item_cache)
    #print("Item Volume: {0}".format(volume))

    # if either the buy or sell order doesnt fill the cargo hold skip
    if transaction.buy_order.vol_remain * volume < MAX_CARGO:
      continue
    if transaction.sell_order.vol_remain * volume < MAX_CARGO:
      continue

    hops = transaction.distance(client)
    #print("Hops: {0}".format(hops))
    items_per_run = math.floor(float(MAX_CARGO) / float(volume))
    # if we cannot afford to fill the cargo hold
    if items_per_run * transaction.sell_order.price > MAX_CAPITAL:
      continue
    #print("Items per run: {0}".format(items_per_run))
    revenue_per_hop = float(transaction.revenue() * items_per_run) / float(hops)
    #print("Revenue per hop: {0}".format(revenue_per_hop))

    if revenue_per_hop > best_revenue_per_hop:
      best_transaction = transaction
      best_revenue_per_hop = revenue_per_hop
      best_items_per_run = items_per_run


  print("================================================================")
  print(best_transaction)
  route = Route(client, best_transaction.sell_order.system_id, best_transaction.buy_order.system_id)
  print(route)
  print("Item: " + route.get_system(best_transaction.buy_order.type_id)["name"])
  print("Items per run: " + str(best_items_per_run))
  print("Total investment: " + str(best_items_per_run * best_transaction.sell_order.price))
  print("Revenue per hop: " + str(best_revenue_per_hop))


if __name__ == "__main__":
  main()