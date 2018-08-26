class Order:

  def __init__(self, t, p, v, s):
    self.type_id = int(t)
    self.price = float(p)
    self.vol_remain = int(v)
    self.system_id = int(s)

  def cost(self):
    return self.price * self.vol_remain

  def get_volume(self, c, cache):
    if self.type_id in cache.data:
      return cache.data[self.type_id]
    else:
      order_volume = c.Universe.get_universe_types_type_id(
                                datasource="tranquility",
                                type_id=self.type_id
                                ).result()["packaged_volume"]
      cache.data[self.type_id] = order_volume
      return order_volume

  def __repr__(self):
    return str(self)

  def __str__(self):
    return "TYPE: {0} PRICE: {1} VOLUME: {2}".format(self.type_id, self.price, self.vol_remain)

  def __gt__(self, other):
    return self.price > other.price

  def __eq__(self, other):
    if isstance(other, Order):
      return self.type_id == other.type_id

class BuyOrder(Order):

  def __init__(self, t, p, v, s):
    Order.__init__(self, t, p, v, s)

class SellOrder(Order):

  def __init__(self, t, p, v, s):
    Order.__init__(self, t, p, v, s)
