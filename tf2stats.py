import itertools
import operator

from consts import GameResult, Team, ClassType, SIXES_COMBAT_CLASSES

class RawPlayerStats:
  def __init__(self, game_stats, raw_player_log):
    self.game_stats = game_stats
    self.raw_player_log = raw_player_log

class PlayerStatDefinition:
  def __init__(self, name, extractor_func):
    self.name = name
    self.extractor_func = extractor_func
  
  def createStats(self, raw_player_stats):
    return PlayerStat(self.name, self.extractor_func(raw_player_stats))
  
  @staticmethod
  def createSimpleStatDefinition(name, raw_player_log_field):
    return PlayerStatDefinition(name, lambda raw_player_stats: raw_player_stats.raw_player_log[raw_player_log_field])

class PlayerStat:
  def __init__(self, name, data):
    self.name = name
    self.data = data

class DetailedPlayerStat(PlayerStat):
  def __init__(self, name, data, player_id, log_id):
    super().__init__(name, data)
    self.player_id = player_id
    self.log_id = log_id

class MaxStat:
  def __init__(self, all_individual_stats, name, stat_getter):
    self.name = name

    max_scoring_stat = 0
    winners = []
    for stats_in_single_log in all_individual_stats:
      stat = stat_getter(stats_in_single_log)
      if stat > max_scoring_stat:
        max_scoring_stat = stat
        winners = [DetailedPlayerStat(name, stat, stats_in_single_log.steam_id, stats_in_single_log.log_id)]
      elif stat == max_scoring_stat:
        winners.append(DetailedPlayerStat(name, stat, stats_in_single_log.steam_id, stats_in_single_log.log_id))
    
    self.winners = winners

class AggregatedStats:
  def __init__(self, all_game_stats, tracked_player_steam_ids):
    all_individual_stats_raw = list(sorted(itertools.chain.from_iterable([game_stats.player_stats for game_stats in all_game_stats]), key=PlayerSingleGameStats.STEAM_ID_GETTER))
    all_individual_stats = [stats for stats in all_individual_stats_raw if stats.steam_id in tracked_player_steam_ids]

    self.stats = [
      MaxStat(all_individual_stats, 'Max DPM', lambda stats: stats.average_dpm),
      MaxStat(all_individual_stats, 'Max HPM', lambda stats: stats.average_hpm),
      MaxStat(all_individual_stats, 'Max Kills', lambda stats: stats.kills),
      MaxStat(all_individual_stats, 'Max Airshots', lambda stats: stats.airshots),
      MaxStat(all_individual_stats, 'Max Captures', lambda stats: stats.captures),
    ]
    
    grouped_stats_per_player = itertools.groupby(all_individual_stats, key=PlayerSingleGameStats.STEAM_ID_GETTER)
    self.player_stats = { steam_id: PlayerAggregatedStats.createPlayerAggregatedStats(list(stats)) for steam_id, stats in grouped_stats_per_player }
  
  def hasStats(self):
    return len(self.player_stats) > 0

class PlayerAggregatedStats:
  def __init__(self, steam_id, average_dpm, average_heals_received_per_minute, average_hpm, game_result_counts, per_class_dpm):
    self.steam_id = steam_id
    self.average_dpm = average_dpm
    self.average_hpm = average_hpm
    self.game_result_counts = game_result_counts
    self.per_class_dpm = per_class_dpm
    self.average_heals_received_per_minute = average_heals_received_per_minute

    total_decided_games = game_result_counts[GameResult.WIN] + game_result_counts[GameResult.LOSS]
    self.win_rate = game_result_counts[GameResult.WIN] / total_decided_games if total_decided_games > 0 else None
  
  @staticmethod
  def createPlayerAggregatedStats(player_stats):
    """
    Given all PlayerStatsForSingleGame for a player, calculates the aggregated stats
    """
    LOW_HPM = 400
    LOW_DPM = 130

    assert len(player_stats) > 0
    assert all([stats.steam_id == player_stats[0].steam_id for stats in player_stats])

    steam_id = player_stats[0].steam_id
    total_dpm, total_hpm, total_heals_received_per_minute = 0, 0, 0
    per_class_total_dpm = { class_type: 0 for class_type in SIXES_COMBAT_CLASSES }
    per_class_games = { class_type: 0 for class_type in SIXES_COMBAT_CLASSES }
    num_combat_class_games, num_medic_games = 0, 0
    game_result_counts = { result: 0 for result in GameResult }

    for stats in player_stats:
      # if they played less than half the game (aka subbed in late), ignore that game's stats
      if stats.total_playtime_in_seconds < 0.5 * stats.game_duration_in_seconds:
        continue

      # other heuristics are low dpm and hpm from leaving the game, but the logs mistakenly tracked the remaining duration
      if stats.average_dpm <= LOW_DPM and stats.average_hpm <= LOW_HPM:
        continue

      game_result_counts[stats.game_result] += 1
      if stats.class_type == ClassType.MEDIC:
        total_hpm += stats.average_hpm
        num_medic_games += 1
      else:
        total_dpm += stats.average_dpm
        total_heals_received_per_minute += stats.average_heals_received_per_minute
        num_combat_class_games += 1
      
      if stats.class_type in SIXES_COMBAT_CLASSES:
        per_class_total_dpm[stats.class_type] += stats.average_dpm
        per_class_games[stats.class_type] += 1

    per_class_dpm = { class_type: (per_class_total_dpm[class_type] / per_class_games[class_type] if per_class_games[class_type] > 0 else None) for class_type in SIXES_COMBAT_CLASSES }
    return PlayerAggregatedStats(steam_id, total_dpm / num_combat_class_games if num_combat_class_games > 0 else None, total_heals_received_per_minute / num_combat_class_games if num_combat_class_games > 0 else None, total_hpm / num_medic_games if num_medic_games > 0 else None, game_result_counts, per_class_dpm)

class SingleGameStats:
  def __init__(self, log_id, log):
    self.log_id = log_id
    self.duration_in_seconds = log[u'length']

    red_score = log[u'teams'][Team.RED.value][u'score']
    blue_score = log[u'teams'][Team.BLUE.value][u'score']
    self.winning_team = None if red_score == blue_score else (Team.RED if red_score > blue_score else Team.BLUE)

    self.player_stats = [PlayerSingleGameStats(log_id, self, steam_id, player_log) for steam_id, player_log in log[u'players'].items()]

  def isScrim(self, team_member_ids, min_num_team_members):
    """
    A game with at least {min_num_team_members} players from {team_member_ids} on the same team is a scrim
    """
    counts = { team: 0 for team in Team }
    for player in self.player_stats:
      if player.steam_id in team_member_ids:
        counts[player.team] += 1

    return any([count >= min_num_team_members for count in counts.values()])

class PlayerSingleGameStats:
  STEAM_ID_GETTER = lambda stats: stats.steam_id

  def __init__(self, log_id, game_stats, player_steam_id, player_log):
    self.log_id = log_id
    self.steam_id = player_steam_id
    self.game_duration_in_seconds = game_stats.duration_in_seconds

    # filter out the 'undefined' & 'unknown' classes, which can occur if a player moves from spec to playing
    valid_class_stats = [class_stats for class_stats in player_log[u'class_stats'] if class_stats[u'type'] != u'undefined' and class_stats[u'type'] != u'unknown']

    self.class_type = ClassType(max(valid_class_stats, key=operator.itemgetter(u'total_time'))[u'type']) # the class is whatever single class had the highest playtime
    self.total_playtime_in_seconds = sum([class_stats[u'total_time'] for class_stats in valid_class_stats])
    self.damage = player_log[u'dmg']
    self.heals = player_log[u'heal']
    self.team = Team(player_log[u'team'])
    self.kills = player_log[u'kills']
    self.assists = player_log[u'assists']
    self.deaths = player_log[u'deaths']
    self.airshots = player_log[u'as']
    self.captures = player_log[u'cpc']
    self.heals_received = player_log[u'hr']
    self.game_result = GameResult.TIE if game_stats.winning_team == None else (GameResult.WIN if game_stats.winning_team == self.team else GameResult.LOSS)
    
    duration_in_minutes = game_stats.duration_in_seconds / 60
    self.average_dpm = self.damage / duration_in_minutes
    self.average_hpm = self.heals / duration_in_minutes
    self.average_heals_received_per_minute = self.heals_received / duration_in_minutes
