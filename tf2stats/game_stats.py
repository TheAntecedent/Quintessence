import operator

from consts import GameResult, Team, ClassType, SIXES_COMBAT_CLASSES

from .stat_definitions import StatDefinition

class SingleGameStats:
  def __init__(self, log_id, log):
    self.log_id = log_id

    self.stats = {}
    for stat_def in GAME_STAT_DEFS:
      self.stats[stat_def.name] = stat_def.calcValue(self.log_id, self.stats, log)

    self.player_stats = [PlayerSingleGameStats(log_id, self, steam_id, player_log) for steam_id, player_log in log[u'players'].items()]

  def is_scrim(self, team_member_ids, min_num_team_members):
    """
    A game with at least {min_num_team_members} players from {team_member_ids} on the same team is a scrim
    """
    counts = { team: 0 for team in Team }
    for player in self.player_stats:
      if player.steam_id in team_member_ids:
        counts[player.stats['team'].value] += 1

    return any([count >= min_num_team_members for count in counts.values()])

class PlayerSingleGameStats:
  STEAM_ID_GETTER = lambda stats: stats.steam_id

  def __init__(self, log_id, game_stats, player_steam_id, player_log):
    self.log_id = log_id
    self.steam_id = player_steam_id
    self.game_stats = game_stats

    self.stats = { "game_" + k: v for k, v in game_stats.stats.items() }
    for stat_def in PLAYER_STAT_DEFS:
      self.stats[stat_def.name] = stat_def.calcValue(self.log_id, self.stats, player_log)

def calc_average_stat(stats, stat_name):
  duration_in_minutes = stats['game_duration'].value / 60.0
  return stats[stat_name].value / duration_in_minutes

def calc_valid_class_stats(raw_stats):
  # filter out the 'undefined' & 'unknown' classes, which can occur if a player moves from spec to playing
  return [class_stats for class_stats in raw_stats[u'class_stats'] if class_stats[u'type'] != u'undefined' and class_stats[u'type'] != u'unknown']

def calc_main_class_type(raw_stats):
  valid_class_stats = calc_valid_class_stats(raw_stats)
  return ClassType(max(valid_class_stats, key=operator.itemgetter(u'total_time'))[u'type']) # the class is whatever single class had the highest playtime

def calc_total_playtime_in_seconds(raw_stats):
  valid_class_stats = calc_valid_class_stats(raw_stats)
  return sum([class_stats[u'total_time'] for class_stats in valid_class_stats])

PLAYER_STAT_DEFS = [
  # base stats
  StatDefinition.createExtractorStatDefinition('damage', u'dmg'),
  StatDefinition.createExtractorStatDefinition('heals', u'heal'),
  StatDefinition.createExtractorStatDefinition('kills', u'kills'),
  StatDefinition.createExtractorStatDefinition('assists', u'assists'),
  StatDefinition.createExtractorStatDefinition('deaths', u'deaths'),
  StatDefinition.createExtractorStatDefinition('airshots', u'as'),
  StatDefinition.createExtractorStatDefinition('captures', u'cpc'),
  StatDefinition.createExtractorStatDefinition('heals_received', u'hr'),
  StatDefinition('team', lambda _, raw_stats: Team(raw_stats[u'team'])),
  StatDefinition('class_type', lambda _, raw_stats: calc_main_class_type(raw_stats)),
  StatDefinition('total_playtime_in_seconds', lambda _, raw_stats: calc_total_playtime_in_seconds(raw_stats)),
  # derived stats
  StatDefinition('game_result', lambda stats, _: GameResult.TIE if stats['game_winning_team'].value == None else (GameResult.WIN if stats['game_winning_team'].value == stats['team'].value else GameResult.LOSS)),
  StatDefinition('average_dpm', lambda stats, _: calc_average_stat(stats, 'damage')),
  StatDefinition('average_hpm', lambda stats, _: calc_average_stat(stats, 'heals')),
  StatDefinition('average_hrpm', lambda stats, _: calc_average_stat(stats, 'heals_received')),
]

def decide_winning_team(game_log):
    red_score = game_log[u'teams'][Team.RED.value][u'score']
    blue_score = game_log[u'teams'][Team.BLUE.value][u'score']
    return None if red_score == blue_score else (Team.RED if red_score > blue_score else Team.BLUE)

GAME_STAT_DEFS = [
  StatDefinition.createExtractorStatDefinition('duration', u'length'),
  StatDefinition('winning_team', lambda _, game_log: decide_winning_team(game_log)),
]