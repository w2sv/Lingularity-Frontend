"""Module to generate ascii charts.
This module provides a single function `plot` that can be used to generate an
ascii chart from a sequences of numbers. The chart can be configured via several
options to tune the output.
"""

from __future__ import annotations
from typing import *
from math import isfinite
import re

from frontend.asciichartpy.config import Config
from frontend.asciichartpy.params import Params
from frontend.asciichartpy.types import _Sequences
from frontend.asciichartpy import colors


def colored(string: str, color: str) -> str:
    return color + string + colors.RESET


_PLOT_SEGMENTS = ['┼', '┤', '╶', '╴', '─', '╰', '╭', '╮', '╯', '│', '┬']
_Chart = List[List[str]]


def plot(*sequences: List[float], config=Config()) -> str:
    sequences = config.process(sequences)

    params = Params(sequences, config)
    serialized_chart = '\n'.join([''.join(row).rstrip() for row in _get_chart(sequences, config, params)])

    if config.title:
        serialized_chart = _title_header(config, params) + serialized_chart

    return serialized_chart


def _title_header(config: Config, params: Params) -> str:
    assert config.title is not None
    return ' ' * (config.offset + params.plot_width // 2 + len(config.title) // 2) + config.title + '\n'


def _get_chart(sequences: _Sequences, config: Config, params: Params) -> _Chart:
    chart = [[' '] * params.chart_width for _ in range(params.n_rows + 1)]
    _add_y_axis(chart, config, params)
    last_row_indices = _add_sequences(sequences, chart, config, params)

    if config.display_x_axis:
        _add_x_axis(chart, config, last_row_indices)

    return chart


def _add_y_axis(chart: _Chart, config: Config, params: Params):
    divisor = [1, params.n_rows][bool(params.n_rows)]

    for i in range(params.min, params.max + 1):
        label = config.format.format(config.max - ((i - params.min) * config.y_value_spread / divisor))
        chart[i - params.min][max(config.offset - len(label), 0)] = label
        chart[i - params.min][config.offset - 1] = _PLOT_SEGMENTS[[1, 0][i == 0]]


def _add_sequences(sequences: _Sequences, chart: _Chart, config: Config, params: Params) -> List[int]:
    _INIT_VALUE = -1

    def scaled(value: float):
        clamped_value = min(max(value, config.min), config.max)
        return int(round(clamped_value * config.ratio) - params.min)

    last_sequence_point_row_indices: List[int] = []
    for i, sequence in enumerate(sequences):
        color = config.colors[i % len(config.colors)]

        # add '┼' at sequence beginning
        if isfinite(sequence[0]):
            chart[params.n_rows - scaled(sequence[0])][config.offset - 1] = colored(_PLOT_SEGMENTS[0], color)

        # add symbols corresponding to singular sequences
        j = _INIT_VALUE
        y0, y1 = _INIT_VALUE, _INIT_VALUE
        while (j := j + 1) < len(sequence) - 1:

            def set_parcel(row_subtrahend: int, segment: str):
                chart[params.n_rows - row_subtrahend][j + config.offset] = colored(segment, color)

            y0 = scaled(sequence[j])
            y1 = scaled(sequence[j + 1])

            if y0 == y1:
                set_parcel(y0, _PLOT_SEGMENTS[4])

            else:
                if y0 > y1:
                    symbol_y0, symbol_y1 = _PLOT_SEGMENTS[7], _PLOT_SEGMENTS[5]
                else:
                    symbol_y0, symbol_y1 = _PLOT_SEGMENTS[8], _PLOT_SEGMENTS[6]

                set_parcel(y0, symbol_y0)
                set_parcel(y1, symbol_y1)

                for y in range(min(y0, y1) + 1, max(y0, y1)):
                    chart[params.n_rows - y][j + config.offset] = colored(_PLOT_SEGMENTS[9], color)

        if j + 1 + config.offset == params.chart_width:
            last_point = [min, max][y1 > y0](y0, y1)
            last_sequence_point_row_indices.append(last_point)

    return last_sequence_point_row_indices


def _add_x_axis(chart: _Chart, config: Config, last_sequence_point_row_indices: List[int]):
    _SEGMENT_2_X_AXIS_TOUCHING_SUBSTITUTE = {
        '┤': '┼',
        '─': '┬',
        '╰': '├',
        '╯': '┤'
    }

    ANSI_ESCAPE_PATTERN = re.compile(r'\x1b[^m]*m')

    def _extract_color(chart_parcel: str) -> str:
        if len((ansi_sequences := re.findall(ANSI_ESCAPE_PATTERN, chart_parcel))):
            return ansi_sequences[0]
        return ''

    def is_data_point(point_index: int) -> bool:
        return point_index % (config.horizontal_point_spacing + 1) == 0

    last_row = chart[-1]

    if not _extract_color(last_row[config.offset - 1]):
        last_row[config.offset - 1] = _PLOT_SEGMENTS[0]

    for i, segment in enumerate(last_row[config.offset:]):
        _is_data_point = is_data_point(i + 1)

        if segment == ' ':
            if _is_data_point:
                last_row[i + config.offset] = _PLOT_SEGMENTS[-1]
            else:
                last_row[i + config.offset] = _PLOT_SEGMENTS[4]
        elif _is_data_point:
            if color := _extract_color(segment):
                segment = re.split(ANSI_ESCAPE_PATTERN, segment)[1]

            last_row[i + config.offset] = color + _SEGMENT_2_X_AXIS_TOUCHING_SUBSTITUTE[segment] + colors.RESET

    for row_index in last_sequence_point_row_indices:
        last_column_segment = chart[-row_index - 1][-2]
        chart[-row_index - 1][-1] = _extract_color(last_column_segment) + _PLOT_SEGMENTS[4] + colors.RESET


if __name__ == '__main__':
    from random import randint

    print(plot([randint(0, 100) for _ in range(5)], config=Config(
        horizontal_point_spacing=5,
        offset=30,
        colors=[colors.RED],
        display_x_axis=True,
        height=15,
        title='SICKPLOT'
    )))