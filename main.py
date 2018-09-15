import datetime
import itertools
import operator

import googledocs
import logstf
import tf2stats
from consts import GameResult, Team, ClassType, SIXES_COMBAT_CLASSES

def isScrim(player_stats, team_member_ids, scrim_threshold):
  counts = { team: 0 for team in Team }
  for player in player_stats:
    if player.steam_id in team_member_ids:
      counts[player.team] += 1

  # a game with at least {scrim_threshold} players from {team_member_ids} on the same team is a scrim
  return any([count >= scrim_threshold for count in counts.values()])

def createAliasLookup(spreadsheet, worksheet_name):
  aliases = googledocs.readAllCells(spreadsheet, worksheet_name)
  
  assert len(aliases) > 0

  aliases = aliases[1:] # skip the header row
  return { id_and_name[1]: id_and_name[0] for id_and_name in aliases }

def formatNoneNumber(num):
  return str(round(num,  2)) if num != None else ''

def generateSpreadsheetRow(stats):
  core_stats = [
      sum(stats.game_result_counts.values()),
      formatNoneNumber(stats.average_dpm),
      formatNoneNumber(stats.average_hpm),
      str(round(stats.win_rate * 100, 2)) + '%' if stats.win_rate != None else ''
    ]
  per_class_dpm = [formatNoneNumber(stats.per_class_dpm[class_type]) for class_type in SIXES_COMBAT_CLASSES]

  return core_stats + per_class_dpm

def updateSpreadsheet(spreadsheet, worksheet_name, alias_lookup, aggregated_stats_per_player):
  spreadsheet_data_header = ["Player", "Games Played", "Average DPM", "Average HPM", "Win Rate"]
  per_class_header = ['Average ' + class_type.value[0].upper() + class_type.value[1:] + ' DPM' for class_type in SIXES_COMBAT_CLASSES]

  spreadsheet_data = [
    [alias_lookup[steam_id]] + generateSpreadsheetRow(stats)
    for steam_id, stats in aggregated_stats_per_player.items()
    if steam_id in alias_lookup
  ]
  sorted_spreadsheet_data = sorted(spreadsheet_data, key=(lambda row: row[0].lower()))

  NUM_CORE_STAT_COLS = 5
  data = [spreadsheet_data_header + per_class_header] + sorted_spreadsheet_data

  googledocs.writeToWorksheetOverwriting(spreadsheet, worksheet_name, data)
  googledocs.formatWorksheet(spreadsheet, worksheet_name, data, NUM_CORE_STAT_COLS)

def updateStatsForTimebound(logs_client, log_metadata, spreadsheet, alias_lookup, worksheet_name, timebound):
  print("Processing stats for " + worksheet_name)

  filtered_log_metadata = logstf.filterLogMetadataInTimeRange(log_metadata[u'logs'], timebound)
  logs = logs_client.fetchLogs(filtered_log_metadata)

  print("\tDone fetching logs")

  all_log_stats = [tf2stats.convertLogToPerPlayerStats(id, log) for id, log in logs.items()]
  non_scrim_stats = [stats for stats in all_log_stats if not isScrim(stats, YAMBO_TEAM_IDS, 4)]
  grouped_stats_per_player = itertools.groupby(sorted(itertools.chain.from_iterable(non_scrim_stats), key=tf2stats.PlayerStatsForSingleGame.STEAM_ID_GETTER), key=tf2stats.PlayerStatsForSingleGame.STEAM_ID_GETTER)
  aggregated_stats_per_player = { steam_id: tf2stats.calculateAggregatedStats(list(stats)) for steam_id, stats in grouped_stats_per_player }

  print("\tDone calculating aggregated stats")
  
  updateSpreadsheet(spreadsheet, worksheet_name, alias_lookup, aggregated_stats_per_player)

  print("\tDone updating spreadsheet")

TOKEN_FILEPATH = './google_docs_token.json'
CREDENTIALS_FILEPATH = './google_docs_credentials.json'
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
SPREADSHEET_ID = '13lTISEHbpGld1-wtu9dTYd3KCAoKkOegzIiRA4KhYeU'
YAMBO_TEAM_IDS = ["[U:1:106802962]", "[U:1:58527614]", "[U:1:95235270]", "[U:1:95386122]", "[U:1:87473885]", "[U:1:34750935]"]
QUINDALI_UPLOADER_ID = "76561198032283738"
LOGS_CACHE_DIR = '.logs'

if __name__ == '__main__':
  spreadsheet = googledocs.openSpreadsheet(TOKEN_FILEPATH, CREDENTIALS_FILEPATH, SCOPES, SPREADSHEET_ID)
  logs_client = logstf.LogsClient(LOGS_CACHE_DIR)
  log_metadata = logs_client.getUploaderLogMetadata(QUINDALI_UPLOADER_ID)
  alias_lookup = createAliasLookup(spreadsheet, 'Key')

  PUG_START_YEAR = 2018
  PUG_START_MONTH = 6
  today = datetime.datetime.today()
  current_year = today.year
  current_month = today.month

  # update all-time stats
  all_time_start_time = logstf.TimeBounds.forMonth(PUG_START_YEAR, PUG_START_MONTH).start
  all_time_end_time = logstf.TimeBounds.forMonth(current_year, current_month).end
  updateStatsForTimebound(logs_client, log_metadata, spreadsheet, alias_lookup, 'All-Time', logstf.TimeBounds(all_time_start_time, all_time_end_time))

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
      updateStatsForTimebound(logs_client, log_metadata, spreadsheet, alias_lookup, worksheet_name, logstf.TimeBounds.forMonth(year, month))
  
  logs_client.close()