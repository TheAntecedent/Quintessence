class StatDefinition:
  def __init__(self, name, extractor_func):
    self.name = name
    self.extractor_func = extractor_func
  
  def calcValue(self, log_id, existing_stats, raw_stats):
    return StatValue(self, log_id, self.extractor_func(existing_stats, raw_stats))

  def __str__(self):
    return self.name
  
  def __repr__(self):
    return str(self)
  
  @staticmethod
  def createExtractorStatDefinition(name, raw_stats_field):
    return StatDefinition(name, lambda _, raw_stats: raw_stats[raw_stats_field])

class StatValue:
  def __init__(self, stat_def, log_id, value):
    self.stat_def = stat_def
    self.value = value
    self.log_id = log_id
  
  def __str__(self):
    return f"{str(self.stat_def)}: {self.value} (log: {self.log_id})"
  
  def __repr__(self):
    return str(self)