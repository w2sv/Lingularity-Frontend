from typing import Optional, Tuple, Type, Iterator
from abc import ABC, abstractmethod
import time
import datetime

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import MaxNLocator
from pynput.keyboard import Controller as KeyboardController

from lingularity.utils import either
from lingularity.backend.trainers import TrainerBackend
from lingularity.backend.components import VocableEntry
from lingularity.backend.metadata import language_metadata
from lingularity.backend.database import MongoDBClient
from lingularity.backend.utils import date as date_utils

from lingularity.frontend.console.utils.output import RedoPrint, centered_print
from lingularity.frontend.console.utils import matplotlib as plt_utils
from .options import TrainingOptions


class TrainerConsoleFrontend(ABC):
    SELECTION_QUERY_OUTPUT_OFFSET = '\n\t'

    def __init__(self, backend: Type[TrainerBackend], mongodb_client: MongoDBClient):
        non_english_language, train_english = self._select_training_language(mongodb_client)
        self._backend: TrainerBackend = backend(non_english_language, train_english, mongodb_client)

        self._buffer_print: RedoPrint = RedoPrint()
        self._training_options: TrainingOptions = self._get_training_options()

        self._n_trained_items: int = 0
        self._latest_created_vocable_entry: Optional[VocableEntry] = None

    @abstractmethod
    def _get_training_options(self) -> TrainingOptions:
        pass

    # -----------------
    # Driver
    # -----------------
    @abstractmethod
    def __call__(self) -> bool:
        """ Invokes trainer frontend

            Returns:
                reinitialize program flag: bool """
        pass

    # -----------------
    # Pre Training
    # -----------------
    @abstractmethod
    def _select_training_language(self, mongodb_client: Optional[MongoDBClient] = None) -> Tuple[str, bool]:
        pass

    @abstractmethod
    def _display_training_screen_header_section(self):
        pass

    def _output_lets_go(self):
        centered_print(either(language_metadata[self._backend.language]['translations'].get('letsGo'), default="Let's go!"), '\n' * 2)

    # -----------------
    # Training
    # -----------------
    @abstractmethod
    def _run_training(self):
        pass

    def _add_vocable(self) -> int:
        """ Returns:
                number of printed lines: int """

        vocable = input(f'Enter {self._backend.language} word/phrase: ')
        meanings = input('Enter meaning(s): ')

        if not all([vocable, meanings]):
            centered_print("Input field left unfilled")
            time.sleep(1)
            return 3

        self._latest_created_vocable_entry = VocableEntry.new(vocable, meanings)
        self._backend.mongodb_client.insert_vocable(self._latest_created_vocable_entry)

        return 2

    def _alter_vocable_entry(self, vocable_entry: VocableEntry) -> int:
        """ Returns:
                number of printed lines: int """

        old_line_repr = vocable_entry.line_repr
        KeyboardController().type(f'{old_line_repr}')
        new_entry_components = input('').split(' - ')

        if len(new_entry_components) != 2:
            centered_print('Invalid alteration')
            time.sleep(1)
            return 3

        old_vocable = vocable_entry.token
        vocable_entry.alter(*new_entry_components)

        if vocable_entry.line_repr != old_line_repr:
            self._backend.mongodb_client.insert_altered_vocable_entry(old_vocable, vocable_entry)

        return 2

    # -----------------
    # Post Training
    # -----------------
    def _plot_training_chronic(self):
        DAY_DELTA = 14

        plt.style.use('seaborn-darkgrid')

        # query training history
        training_history = self._backend.mongodb_client.query_training_chronic()

        # get plotting dates
        dates = list(self._get_plotting_dates(training_dates=iter(training_history.keys()), day_delta=DAY_DELTA))

        # query number of trained sentences, vocabulary entries at every stored date,
        # pad item values of asymmetrically item-value-beset dates
        trained_sentences, trained_vocabulary = map(lambda trainer_abbreviation: [training_history.get(date, {}).get(trainer_abbreviation) or 0 for date in dates], ['s', 'v'])

        # omit year, invert day & month for proper tick label display, replace todays date with 'today'
        dates = ['-'.join(date.split('-')[1:][::-1]) for date in dates[:-1]] + ['today']

        # set up figure
        fig, ax = plt.subplots()
        fig.set_size_inches(np.asarray([6.5, 6]))
        fig.canvas.draw()
        fig.canvas.set_window_title("Way to go!")

        # define plot
        ax.set_title(f'{self._backend.language} Training History')

        x_range = np.arange(len(dates))

        ax.plot(x_range, trained_sentences, marker='.', markevery=list(x_range), color='r', label='sentences')
        ax.plot(x_range, trained_vocabulary, marker='.', markevery=list(x_range), color='g', label='vocable entries')
        ax.set_xticks(x_range)
        ax.set_xticklabels(dates, minor=False, rotation=45)
        ax.set_xlabel('date')

        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_ylabel('faced items')

        ax.legend(loc=plt_utils.get_legend_location(trained_sentences, trained_vocabulary))
        plt_utils.center_windows()
        plt.show()

    @staticmethod
    def _get_plotting_dates(training_dates: Iterator[str], day_delta: int) -> Iterator[str]:
        starting_date = TrainerConsoleFrontend._get_starting_date(training_dates, day_delta)

        while starting_date <= date_utils.today:
            yield str(starting_date)
            starting_date += datetime.timedelta(days=1)

    @staticmethod
    def _get_starting_date(training_dates: Iterator[str], day_delta: int) -> datetime.date:
        earliest_possible_date: datetime.date = (date_utils.today - datetime.timedelta(days=day_delta))

        for training_date in training_dates:
            if (converted_date := date_utils.string_2_date(training_date)) >= earliest_possible_date:
                return converted_date

        raise AttributeError

    # -----------------
    # Dunder(s)
    # -----------------
    def __str__(self):
        return self.__class__.__name__[0].lower()
