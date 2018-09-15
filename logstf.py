import datetime
import json
import io
import os
from math import floor

import requests
from requests_throttler import BaseThrottler

def loadJson(filepath):
  with io.open(filepath, 'r') as f:
    return json.load(f)

def saveJson(filepath, jsonObject):
  with io.open(filepath, 'w') as f:
    return json.dump(jsonObject, f)

def getLogIdFromUrl(url):
  return int(url[url.rindex('/') + 1:])

def filterLogMetadataInTimeRange(logs, timerange):
  return [log for log in logs if log[u'players'] and log[u'players'] >= 12 and log[u'players'] < 18 and log[u'date'] >= timerange.start and log[u'date'] <= timerange.end] # only include 6v6 games (which might have had subs)

class LogsClient:
  def __init__(self, logs_cache_dir):
    self.logs_cache_dir = logs_cache_dir + '/'
    self.throttler = BaseThrottler(name='base-throttler', delay=0.2)
    self.throttler.start()

  def fetchLogs(self, log_metadata):
    log_metadata_lookup = { log[u'id']: log for log in log_metadata }
    
    # fetch cached log data
    if not os.path.isdir(self.logs_cache_dir):
      os.makedirs(self.logs_cache_dir)
    
    cache_filepaths = { id: self.getLogFilepath(id) for id in log_metadata_lookup }
    existing_logs = { id: loadJson(filepath) for id, filepath in cache_filepaths.items() if os.path.isfile(filepath) }

    updated_log_ids = [id for id, log in existing_logs.items() if log[u'info'][u'date'] < log_metadata_lookup[id][u'date']]

    # fetch any new uncached logs or logs that need to be updated
    fetched_log_ids = [id for id in log_metadata_lookup if (id not in existing_logs or id in updated_log_ids)]
    fetched_logs = {}
    if len(fetched_log_ids) > 0:
      reqs = [requests.Request('GET', 'http://logs.tf/api/v1/log/' + str(id)) for id in fetched_log_ids]

      throttled_requests = self.throttler.multi_submit(reqs)

      fetched_logs = { getLogIdFromUrl(tr.request.url): tr.response.json() for tr in throttled_requests }

      # update cache
      for id, log_json in fetched_logs.items():
        saveJson(self.getLogFilepath(id), log_json)
    
    # return merged cached & new results, preferring the new results if any conflicts
    return { **existing_logs, **fetched_logs }

  def getUploaderLogMetadata(self, uploaderId):
    return self.throttler.submit(requests.Request('GET', 'http://logs.tf/api/v1/log?uploader=' + uploaderId + '&limit=10000')).response.json()

  def getLogFilepath(self, id):
    return self.logs_cache_dir + str(id) + '.json'
  
  def close(self):
    self.throttler.shutdown()

TF2_DAY_END = 16 # include any late-night games from the previous day by ending days at noon EST
SECONDS_PER_DAY = 24 * 60 * 60
class TimeBounds:
  def __init__(self, start, end):
    self.start = start
    self.end = end
  
  @staticmethod
  def forDay(year, month, day):
    start = datetime.datetime(year, month, day, TF2_DAY_END, tzinfo=datetime.timezone.utc).timestamp()
    return TimeBounds(start, start + SECONDS_PER_DAY)
  
  @staticmethod
  def forMonth(year, month):
    start = datetime.datetime(year, month, 1, TF2_DAY_END, tzinfo=datetime.timezone.utc).timestamp()
    end = datetime.datetime(year + floor(month / 12), (month % 12) + 1, 1, TF2_DAY_END, tzinfo=datetime.timezone.utc).timestamp()
    return TimeBounds(start, end)
