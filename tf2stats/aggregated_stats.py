import itertools
import operator

from consts import GameResult, Team, ClassType, SIXES_COMBAT_CLASSES

from .stat_definitions import StatValue
from .game_stats import PlayerSingleGameStats

class MaxStat:
  def __init__(self, all_individual_stats, name, stat_getter):
    self.name = name

    max_scoring_stat = 0
    winners = []
    for stats_in_single_log in all_individual_stats:
      stat = stat_getter(stats_in_single_log)
      if stat > max_scoring_stat:
        max_scoring_stat = stat
        winners = [(stats_in_single_log.steam_id, StatValue(name, stats_in_single_log.log_id, stat))]
      elif stat == max_scoring_stat:
        winners.append((stats_in_single_log.steam_id, StatValue(name, stats_in_single_log.log_id, stat)))
    
    self.winners = winners

class AggregatedStats:
  def __init__(self, all_game_stats, tracked_player_steam_ids):
    all_individual_stats_raw = list(sorted(itertools.chain.from_iterable([game_stats.player_stats for game_stats in all_game_stats]), key=PlayerSingleGameStats.STEAM_ID_GETTER))
    all_individual_stats = [stats for stats in all_individual_stats_raw if stats.steam_id in tracked_player_steam_ids]

    self.stats = [
      MaxStat(all_individual_stats, 'Max DPM', lambda stats: stats.stats['average_dpm'].value),
      MaxStat(all_individual_stats, 'Max HPM', lambda stats: stats.stats['average_hpm'].value),
      MaxStat(all_individual_stats, 'Max Kills', lambda stats: stats.stats['kills'].value),
      MaxStat(all_individual_stats, 'Max Airshots', lambda stats: stats.stats['airshots'].value),
      MaxStat(all_individual_stats, 'Max Captures', lambda stats: stats.stats['captures'].value),
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
      if stats.stats['total_playtime_in_seconds'].value < 0.5 * stats.game_stats.stats['duration'].value:
        continue

      # other heuristics are low dpm and hpm from leaving the game, but the logs mistakenly tracked the remaining duration
      if stats.stats['average_dpm'].value <= LOW_DPM and stats.stats['average_hpm'].value <= LOW_HPM:
        continue

      game_result_counts[stats.stats['game_result'].value] += 1
      if stats.stats['class_type'].value == ClassType.MEDIC:
        total_hpm += stats.stats['average_hpm'].value
        num_medic_games += 1
      else:
        total_dpm += stats.stats['average_dpm'].value
        total_heals_received_per_minute += stats.stats['average_hrpm'].value
        num_combat_class_games += 1
      
      if stats.stats['class_type'].value in SIXES_COMBAT_CLASSES:
        per_class_total_dpm[stats.stats['class_type'].value] += stats.stats['average_dpm'].value
        per_class_games[stats.stats['class_type'].value] += 1

    per_class_dpm = { class_type: (per_class_total_dpm[class_type] / per_class_games[class_type] if per_class_games[class_type] > 0 else None) for class_type in SIXES_COMBAT_CLASSES }
    return PlayerAggregatedStats(
      steam_id,
      total_dpm / num_combat_class_games if num_combat_class_games > 0 else None,
      total_heals_received_per_minute / num_combat_class_games if num_combat_class_games > 0 else None,
      total_hpm / num_medic_games if num_medic_games > 0 else None,
      game_result_counts,
      per_class_dpm
    )
