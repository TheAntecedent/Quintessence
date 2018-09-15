import datetime
import itertools
import operator

import googledocs
import logstf
import tf2stats
from consts import GameResult, Team, ClassType, SIXES_COMBAT_CLASSES

def createAliasLookup(spreadsheet, worksheet_name, logs_client):
  aliases = googledocs.readAllCells(spreadsheet, worksheet_name)
  
  assert len(aliases) > 0

  aliases = aliases[1:] # skip the header row
  return { id_and_name[1]: id_and_name[0] for id_and_name in aliases }

def fetchConfiguration(spreadsheet, worksheet_name):
  config_def = googledocs.readAllCells(spreadsheet, worksheet_name)
  
  config_def = config_def[1:] # skip the header row
  return { row[0]: row[1] for row in config_def } # the first column is the config key and the second is the value

def formatNoneNumber(num):
  return str(round(num,  2)) if num != None else ''

def formatIndividualPlayerStat(alias, log_id, data):
  return ('=HYPERLINK("https://logs.tf/%s", "%s, %s")') % (str(log_id), alias, formatNoneNumber(data))

def generateSummaryData(alias_lookup, stats_summary):
  return [[stat.name + ':'] + [formatIndividualPlayerStat(alias_lookup[winner.player_id], winner.log_id, winner.data) for winner in stat.winners] for stat in stats_summary.stats]

def concatDataHorizontally(data1, data2):
  """
  Concats data2 to the right of data1
  """

  if len(data1) == 0:
    return data2
  if len(data2) == 0:
    return data1

  data1_height = len(data1)
  data2_height = len(data2)
  data_result_height = max(data1_height, data2_height)
  
  # data2 starts at the end of the longest row in data1 that is next to it
  data1_adjacent_height = min(data1_height, data2_height)
  data2_start_col = max([len(row) for row in data1[:data1_adjacent_height]])

  data_extended = [['' for x in range(data2_start_col)] for y in range(data_result_height - data1_height)]
  data_result = data1 + data_extended

  for y in range(data2_height):
    data_result[y] += ['' for x in range(data2_start_col - len(data_result[y]))]
    data_result[y] += data2[y]

  return data_result

def concatDataVertically(data1, data2):
  """
  Concats data2 to the bottom of data1 
  """

  return data1 + data2

def generateSpreadsheetRow(player_aggregated_stats):
  core_stats = [
      sum(player_aggregated_stats.game_result_counts.values()),
      formatNoneNumber(player_aggregated_stats.average_dpm),
      formatNoneNumber(player_aggregated_stats.average_hpm),
      str(round(player_aggregated_stats.win_rate * 100, 2)) + '%' if player_aggregated_stats.win_rate != None else ''
    ]
  per_class_dpm = [formatNoneNumber(player_aggregated_stats.per_class_dpm[class_type]) for class_type in SIXES_COMBAT_CLASSES]

  return core_stats + per_class_dpm

def updateSpreadsheet(spreadsheet, worksheet_name, alias_lookup, stats_summary):
  spreadsheet_data_header = ["Player", "Games Played", "Average DPM", "Average HPM", "Win Rate"]
  per_class_header = ['Average ' + class_type.value[0].upper() + class_type.value[1:] + ' DPM' for class_type in SIXES_COMBAT_CLASSES]

  spreadsheet_data = [
    [alias_lookup[steam_id]] + generateSpreadsheetRow(stats)
    for steam_id, stats in stats_summary.player_stats.items()
    if steam_id in alias_lookup
  ]
  sorted_spreadsheet_data = sorted(spreadsheet_data, key=(lambda row: row[0].lower()))

  player_stat_data = [spreadsheet_data_header + per_class_header] + sorted_spreadsheet_data
  NUM_CORE_PLAYER_STAT_COLS = 5
  num_player_stat_cols = max([len(row) for row in player_stat_data])

  max_stat_data = [[]] + [[''] + row for row in generateSummaryData(alias_lookup, stats_summary)] # add 1 row & column of padding
  data = concatDataHorizontally(player_stat_data, max_stat_data)

  googledocs.writeToWorksheetOverwriting(spreadsheet, worksheet_name, data)
  googledocs.formatWorksheet(spreadsheet, worksheet_name, data, num_player_stat_cols, NUM_CORE_PLAYER_STAT_COLS)

def updateStatsForTimebound(logs_client, log_metadata, ignored_team_member_ids, ignored_log_ids, spreadsheet, alias_lookup, worksheet_name, timebound):
  print("Processing stats for " + worksheet_name)

  filtered_log_metadata = [log for log in log_metadata[u'logs'] if log[u'id'] not in ignored_log_ids]
  filtered_log_metadata_in_timebound = logstf.filterLogMetadataInTimeRange(filtered_log_metadata, timebound)
  logs = logs_client.fetchLogs(filtered_log_metadata_in_timebound)

  print("\tDone fetching logs")

  all_game_stats = [tf2stats.SingleGameStats(id, log) for id, log in logs.items()]
  non_scrim_stats = [game_stats for game_stats in all_game_stats if not game_stats.isScrim(ignored_team_member_ids, 4)]
  stats_summary = tf2stats.AggregatedStats(non_scrim_stats, alias_lookup.keys())

  print("\tDone calculating aggregated stats")
  
  updateSpreadsheet(spreadsheet, worksheet_name, alias_lookup, stats_summary)

  print("\tDone updating spreadsheet")

def splitAndCleanCSV(stringData):
  return [s.strip() for s in stringData.split(',')]

TOKEN_FILEPATH = './google_docs_token.json'
CREDENTIALS_FILEPATH = './google_docs_credentials.json'
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
SPREADSHEET_ID = '13lTISEHbpGld1-wtu9dTYd3KCAoKkOegzIiRA4KhYeU'
LOGS_CACHE_DIR = '.logs'

CONFIG_KEY_UPLOADER_ID = 'uploaderId'
CONFIG_KEY_IGNORED_TEAM_IDS = 'ignoredTeamSteamIds'
CONFIG_KEY_IGNORED_LOG_IDS = 'ignoredLogIds'

if __name__ == '__main__':
  spreadsheet = googledocs.openSpreadsheet(TOKEN_FILEPATH, CREDENTIALS_FILEPATH, SCOPES, SPREADSHEET_ID)
  logs_client = logstf.LogsClient(LOGS_CACHE_DIR)
  alias_lookup = createAliasLookup(spreadsheet, 'Key', logs_client)
  config = fetchConfiguration(spreadsheet, 'Configuration')
  
  # extract config values
  uploader_id = config[CONFIG_KEY_UPLOADER_ID]
  ignored_team_member_ids = splitAndCleanCSV(config[CONFIG_KEY_IGNORED_TEAM_IDS])
  ignored_log_ids = [int(log_id) for log_id in splitAndCleanCSV(config[CONFIG_KEY_IGNORED_LOG_IDS])]

  log_metadata = logs_client.getUploaderLogMetadata(config[CONFIG_KEY_UPLOADER_ID])

  PUG_START_YEAR = 2018
  PUG_START_MONTH = 6
  today = datetime.datetime.today()
  current_year = today.year
  current_month = today.month

  # update all-time stats
  all_time_start_time = logstf.TimeBounds.forMonth(PUG_START_YEAR, PUG_START_MONTH).start
  all_time_end_time = logstf.TimeBounds.forMonth(current_year, current_month).end
  updateStatsForTimebound(logs_client, log_metadata, ignored_team_member_ids, ignored_log_ids, spreadsheet, alias_lookup, 'All-Time', logstf.TimeBounds(all_time_start_time, all_time_end_time))

  # update per-month stats
  for year in range(PUG_START_YEAR, current_year + 1):
    for month in range(1, 13):
      if year == PUG_START_YEAR and month < PUG_START_MONTH: # skip the months in the first year when there were no pugs
        continue
      if year == current_year and month > current_month:
        break
      worksheet_name = datetime.date(year, month, 1).strftime('%B') + ' ' + str(year)
      # don't bother updating earlier months since their stats won't have changed
      if googledocs.worksheetExists(spreadsheet, worksheet_name) and (year != current_year or month != current_month):
        pass # continue
      updateStatsForTimebound(logs_client, log_metadata, ignored_team_member_ids, ignored_log_ids, spreadsheet, alias_lookup, worksheet_name, logstf.TimeBounds.forMonth(year, month))
  
  logs_client.close()