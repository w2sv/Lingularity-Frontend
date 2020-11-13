from typing import Optional, Type, Iterator, Sequence, List
from abc import ABC, abstractmethod
from time import sleep
import datetime

from pynput.keyboard import Controller as KeyboardController

from backend.trainers import TrainerBackend
from backend.trainers.components import VocableEntry
from backend import language_metadata
from backend.utils import date as date_utils, either

from frontend.state import State
from frontend.utils import output, view
from frontend.trainers.base.options import TrainingOptions


class TrainerFrontend(ABC):
    def __init__(self, backend_type: Type[TrainerBackend]):
        self._backend: TrainerBackend = backend_type(State.non_english_language, State.train_english)

        self._training_options: TrainingOptions = self._get_training_options()

        self._n_trained_items: int = 0
        self._latest_created_vocable_entry: Optional[VocableEntry] = None

    @abstractmethod
    def _get_training_options(self) -> TrainingOptions:
        pass

    # -----------------
    # Driver
    # -----------------
    TrainingItemSequence = List[int]

    @abstractmethod
    def __call__(self) -> Optional[TrainingItemSequence]:
        """ Invokes trainer frontend

            Returns:
                reentry point """
        pass

    def _set_terminal_title(self):
        view.set_terminal_title(f'{self._backend.language} {self._training_designation}')

    @property
    @abstractmethod
    def _training_designation(self) -> str:
        pass

    # -----------------
    # Pre Training
    # -----------------
    @abstractmethod
    def _display_training_screen_header_section(self):
        pass

    def _output_lets_go(self):
        output.centered(either(language_metadata[self._backend.language]['translations'].get('letsGo'), default="Let's go!"), '\n' * 2)

    # -----------------
    # Training
    # -----------------
    @abstractmethod
    def _run_training_loop(self):
        pass

    def _add_vocable(self) -> int:
        """ Query, create new vocable entry,
            Enter it into database
            Update State.vocabulary_available

            Returns:
                number of printed lines: int """

        INDENTATION = output.column_percentual_indentation(percentage=0.32)

        # query vocable and meaning, exit if one of the two fields empty
        vocable_and_meaning = []
        for query_message in [f'Enter {self._backend.language} word/phrase: ', 'Enter meaning(s): ']:
            if not len((field := input(f'{INDENTATION}{query_message}'))):
                output.centered("INPUT FIELD LEFT UNFILLED")
                sleep(1)
                return 3
            vocable_and_meaning.append(field)

        # create new vocable entry, enter into database
        self._latest_created_vocable_entry = VocableEntry.new(*vocable_and_meaning)
        self._backend.mongodb_client.insert_vocable_entry(self._latest_created_vocable_entry.as_dict)

        # update vocabulary_available flag in State
        if not State.vocabulary_available:
            State.vocabulary_available = True

        return 2

    def _alter_vocable_entry(self, vocable_entry: VocableEntry) -> int:
        """ Returns:
                number of printed lines: int """

        # store old properties for comparison, database identification
        old_line_repr = str(vocable_entry)
        old_vocable = vocable_entry.vocable

        # type indented old representation
        KeyboardController().type(f'{output.centering_indentation(old_line_repr)}{old_line_repr}')
        # TODO: debug print(centering_indentation) into KeyboardController().type(old_line_repr)

        # get new components, i.e. vocable + ground_truth
        new_entry_components = input('').split(' - ')

        # exit in case of invalid alteration
        if len(new_entry_components) != 2:
            output.centered('INVALID ALTERATION')
            sleep(1)
            return 3

        # strip whitespaces, alter vocable entry
        stripped_new_entry_components = map(lambda component: component.strip(' '), new_entry_components)
        vocable_entry.alter(*stripped_new_entry_components)

        # insert altered entry into database in case of alteration actually having taken place
        if str(vocable_entry) != old_line_repr:
            self._backend.mongodb_client.alter_vocable_entry(old_vocable, vocable_entry.as_dict)

        return 2

    # -----------------
    # Post Training
    # -----------------
    def _training_item_sequence(self) -> TrainingItemSequence:
        DAY_DELTA = 14

        # query language training history of respective trainer
        training_history = self._backend.mongodb_client.query_training_chronic()
        training_history = {date: trainer_dict[str(self._backend)] for date, trainer_dict in training_history.items() if trainer_dict.get(str(self._backend))}

        # get plotting dates
        dates = list(self._plotting_dates(training_dates=iter(training_history.keys()), day_delta=DAY_DELTA))
        # get training item sequences, conduct zero-padding on dates on which no training took place
        return [training_history.get(date, 0) for date in dates]

    def _training_chronic_axis_title(self, item_scores: Sequence[int]) -> str:
        if len(item_scores) == 2 and not item_scores[0]:
            return "Let's get that graph inflation goin'"

        yesterday_exceedance_difference = item_scores[-1] - item_scores[-2] + 1
        item_name = [self._pluralized_item_name, self._item_name][yesterday_exceedance_difference in [-1, 0]]

        if yesterday_exceedance_difference >= 0:
            return f"Exceeded yesterdays score by {yesterday_exceedance_difference + 1} {item_name}"
        return f"{abs(yesterday_exceedance_difference)} {item_name} left to top yesterdays score"

    @property
    @abstractmethod
    def _pluralized_item_name(self) -> str:
        pass

    @property
    @abstractmethod
    def _item_name(self) -> str:
        pass

    @staticmethod
    def _plotting_dates(training_dates: Iterator[str], day_delta: int) -> Iterator[str]:
        """ Returns:
                continuous sequences of plotting dates to be seized as x-axis ticks
                starting from earliest day with (todays date - respective date) <= day_delta,
                going up to todays date

        e.g.:

            today = '2020-10-20'
            training_dates = ('2020-07-19', '2020-08-05', '2020-08-10', '2020-08-12', '2020-08-13', '2020-08-14',
            '2020-08-15', '2020-08-16', '2020-09-18', '2020-09-19', '2020-09-20', '2020-09-21', '2020-09-22',
            '2020-09-24', '2020-09-25', '2020-09-26', '2020-09-27', '2020-09-28', '2020-09-29', '2020-09-30',
            '2020-10-06', '2020-10-12', '2020-10-13', '2020-10-14', '2020-10-15', '2020-10-16', '2020-10-17',
            '2020-10-19', '2020-10-20')

            TrainerFrontend._plotting_dates(_training_dates, day_delta=14)
            ['2020-10-06', '2020-10-07', '2020-10-08', '2020-10-09', '2020-10-10', '2020-10-11', '2020-10-12',
            '2020-10-13', '2020-10-14', '2020-10-15', '2020-10-16', '2020-10-17', '2020-10-18', '2020-10-19',
            '2020-10-20'] """

        starting_date = TrainerFrontend._get_starting_date(training_dates, day_delta)

        while starting_date <= date_utils.today:
            yield str(starting_date)
            starting_date += datetime.timedelta(days=1)

    @staticmethod
    def _get_starting_date(training_dates: Iterator[str], day_delta: int) -> datetime.date:
        """ Returns:
                earliest date comprised within training_dates for which (todays date - respective date) <= day_delta
                holds true """

        earliest_possible_date: datetime.date = (date_utils.today - datetime.timedelta(days=day_delta))

        for training_date in training_dates:
            if (converted_date := date_utils.string_2_date(training_date)) >= earliest_possible_date:
                return converted_date

        raise AttributeError
