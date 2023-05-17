"""
Copyright (c) 2023 Alexey Akinshchikov

This module contains the team draw generator.
The generator considers prior teams for the players and their current rank.
"""


import copy
import json
from typing import Any

import numpy as np
import pandas as pd


def make_team_draw(
        directory: str,
) -> None:
    """
    Draw the players into the teams.
    """

    def add_next_player(
            next_player_index: int,
            teams: list[list[int]],
            team_sizes: list[int],
            team_lowest_ranks: list[int],
    ) -> list[list[int]] | None:
        """
        Add the next player to the team draw.
        """

        if next_player_index >= players.shape[0]:
            if min(team_sizes) < min_team_size or max(team_sizes) > max_team_size:
                return None

            return teams

        team_priority_queue: list[int] = sorted(
            range(team_count),
            key = lambda item: (team_sizes[item], -team_lowest_ranks[item], item),
        )

        for team_index in team_priority_queue:
            group_size: int = 1
            max_counter: int = 0

            for player_index in teams[team_index]:
                counter: int = 0
                for column in columns:
                    if players.loc[next_player_index, column] and \
                       players.loc[player_index, column] == players.loc[next_player_index, column]:
                        counter += 1
                max_counter = max(max_counter, counter)

                group_size += (players.loc[player_index, 'group'] == players.loc[next_player_index, 'group'])

            if group_size > configuration['max_group_size'] or max_counter >= configuration['max_common_team']:
                continue

            next_teams: list[list[int]] = copy.deepcopy(teams)
            next_team_sizes: list[int] = copy.deepcopy(team_sizes)
            next_team_lowest_ranks: list[int] = copy.deepcopy(team_lowest_ranks)

            next_teams[team_index].append(next_player_index)
            next_team_sizes[team_index] += 1
            next_team_lowest_ranks[team_index] = next_player_index

            result: list[list[int]] | None = add_next_player(
                next_player_index = next_player_index + 1,
                teams = next_teams,
                team_sizes = next_team_sizes,
                team_lowest_ranks = next_team_lowest_ranks,
            )

            if result is not None:
                return result

        return None

    configuration_file: str = f'{directory}/configuration.json'
    players_file: str = f'{directory}/players.tsv'
    draw_file: str = f'{directory}/draw.tsv'
    team_file: str = f'{directory}/teams.txt'

    with open(file = configuration_file, mode = 'r') as file:
        configuration: dict[str, Any] = json.load(fp = file)

    players: pd.DataFrame = \
        pd.read_csv(filepath_or_buffer = players_file, sep = '\t').sort_values(by = 'rank').reset_index(drop = True)

    columns: list[str] = [column for column in players.columns if 'team' in column]

    player_count: int = players.shape[0]

    if configuration['upper_size_fix']:
        min_team_size: int = configuration['team_size']
        max_team_size: int = configuration['team_size'] + 1
        team_count: int = int(np.floor(player_count / configuration['team_size']))
    else:
        min_team_size = configuration['team_size'] - 1
        max_team_size = configuration['team_size']
        team_count = int(np.ceil(player_count / configuration['team_size']))

    team_draw: list[list[int]] = add_next_player(
        next_player_index = 0,
        teams = [[] for _ in range(team_count)],
        team_sizes = [0] * team_count,
        team_lowest_ranks = [-1] * team_count,
    )

    if team_draw is None:
        raise RuntimeError('Players can not be drawn into teams. Please, change the configuration file and try again.')

    players['draw'] = -1

    for team in range(team_count):
        players.loc[team_draw[team], 'draw'] = team

    players.to_csv(
        path_or_buf = draw_file,
        sep = '\t',
        index = False,
    )

    with open(file = team_file, mode = 'w') as file:
        for team in range(team_count):
            file.write(f'{team}\n')

            for player in team_draw[team]:
                file.write(f'{players.loc[player, "name"]}\n')

            file.write('\n')
