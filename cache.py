import os
import time
import pickle

class Cache:

  # default ttl of 15 minutes
  def __init__(self, f, **kwargs):
    self.file = f
    if 'ttl' in kwargs:
      self.ttl = kwargs["ttl"]
    self.data = self.read_data()

  def __del__(self):
    self.write_data()

  def is_cache_valid(self):
    if not os.path.isfile(self.file):
      print("Cache file {0} not found - cache is invalid".format(self.file))
      return False
    if not hasattr(self, "ttl"):
      print("Cache file {0} has no TTL - cache is valid".format(self.file))
      return True
    file_age = int(time.time()) - os.path.getmtime(self.file)
    if (file_age > self.ttl):
      print("Cache file {0} is over TTL - cache is invalid".format(self.file))
      return False
    print("Cache file {0} is within TTL - cache is valid".format(self.file))
    return True

  def write_data(self):
    try:
      with open(self.file, 'wb') as f:
        pickle.dump(self.data, f)
    except Exception as e:
      print("Couldn't write data: " + str(e))
      

  def read_data(self):
    if self.is_cache_valid():
      try:
        with open(self.file, 'rb') as f:
          data = pickle.load(f)
        return data
      except Exception as e:
        print("Couldn't read data: " + str(e))
        return {}
    else:
      return {}
