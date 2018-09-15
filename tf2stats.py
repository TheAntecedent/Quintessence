import operator

from consts import GameResult, Team, ClassType, SIXES_COMBAT_CLASSES

class AggregatedStats:
  def __init__(self, steam_id, average_dpm, average_hpm, game_result_counts, per_class_dpm):
    self.steam_id = steam_id
    self.average_dpm = average_dpm
    self.average_hpm = average_hpm
    self.game_result_counts = game_result_counts
    self.per_class_dpm = per_class_dpm

    total_decided_games = game_result_counts[GameResult.WIN] + game_result_counts[GameResult.LOSS]
    self.win_rate = game_result_counts[GameResult.WIN] / total_decided_games if total_decided_games > 0 else None

class PlayerStatsForSingleGame:
  STEAM_ID_GETTER = lambda stats: stats.steam_id

  def __init__(self, log_id, steam_id, player_log, game_duration_in_seconds, winning_team):
    self.log_id = log_id
    self.steam_id = steam_id
    self.game_duration_in_seconds = game_duration_in_seconds

    # filter out the 'undefined' & 'unknown' classes, which can occur if a player moves from spec to playing
    valid_class_stats = [class_stats for class_stats in player_log[u'class_stats'] if class_stats[u'type'] != u'undefined' and class_stats[u'type'] != u'unknown']

    self.class_type = ClassType(max(valid_class_stats, key=operator.itemgetter(u'total_time'))[u'type']) # the class is whatever single class had the highest playtime
    self.total_playtime_in_seconds = sum([class_stats[u'total_time'] for class_stats in valid_class_stats])
    self.damage = player_log[u'dmg']
    self.heals = player_log[u'heal']
    self.team = Team(player_log[u'team'])
    self.game_result = GameResult.TIE if winning_team == None else (GameResult.WIN if winning_team == self.team else GameResult.LOSS)

def convertLogToPerPlayerStats(log_id, log):
  red_score = log[u'teams'][Team.RED.value][u'score']
  blue_score = log[u'teams'][Team.BLUE.value][u'score']
  winning_team = None if red_score == blue_score else (Team.RED if red_score > blue_score else Team.BLUE)

  return [PlayerStatsForSingleGame(log_id, steam_id, player_log, log[u'length'], winning_team) for steam_id, player_log in log[u'players'].items()]

def calculateAggregatedStats(player_stats):
  """
  Given all individual PlayerStatsForSingleGame for one player, calculates the aggregated stats
  """

  LOW_HPM = 400
  LOW_DPM = 130

  assert len(player_stats) > 0
  assert all([stats.steam_id == player_stats[0].steam_id for stats in player_stats])

  steam_id = player_stats[0].steam_id
  total_dpm, total_hpm = 0, 0
  per_class_total_dpm = { class_type: 0 for class_type in SIXES_COMBAT_CLASSES }
  per_class_games = { class_type: 0 for class_type in SIXES_COMBAT_CLASSES }
  num_damage_games, num_heal_games = 0, 0
  game_result_counts = { result: 0 for result in GameResult }

  for stats in player_stats:
    # if they played less than half the game (aka subbed in late), ignore that game's stats
    if stats.total_playtime_in_seconds < 0.5 * stats.game_duration_in_seconds:
      continue
    
    duration_in_minutes = stats.total_playtime_in_seconds / 60
    dpm = stats.damage / duration_in_minutes
    hpm = stats.heals / duration_in_minutes

    # other heuristics are low dpm and hpm from leaving the game, but the logs mistakenly tracking the remaining duration
    if dpm <= LOW_DPM and hpm <= LOW_HPM:
      continue

    game_result_counts[stats.game_result] += 1
    if stats.class_type == ClassType.MEDIC:
      total_hpm += hpm
      num_heal_games += 1
    else:
      total_dpm += dpm
      num_damage_games += 1
    
    if stats.class_type in SIXES_COMBAT_CLASSES:
      per_class_total_dpm[stats.class_type] += dpm
      per_class_games[stats.class_type] += 1

  per_class_dpm = { class_type: (per_class_total_dpm[class_type] / per_class_games[class_type] if per_class_games[class_type] > 0 else None) for class_type in SIXES_COMBAT_CLASSES }
  return AggregatedStats(steam_id, total_dpm / num_damage_games if num_damage_games > 0 else None, total_hpm / num_heal_games if num_heal_games > 0 else None, game_result_counts, per_class_dpm)