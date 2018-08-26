class Route:

  def __init__(self, c, s, e):
    self.client = c
    self.start = s
    self.end = e
    #self.start = self.get_system(s)
    #self.end = self.get_system(e)

  def __repr__(self):
    return str(self)

  def __str__(self):
    system_ids = self.get_distance()
    return str([self.get_system(id)["name"] for id in system_ids])

  def get_system(self, s):
    result = self.client.Universe.post_universe_names(
                      ids=[s]
                      ).result()
    return result[0]

  def get_distance(self):
    return self.client.Routes.get_route_origin_destination(
            datasource="tranquility",
            flag="shortest",
            origin=self.start,
            destination=self.end
            ).result()
