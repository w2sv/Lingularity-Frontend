from typing import Optional, List, Type

from lingularity.backend.components import TextToSpeech
from lingularity.backend.database import MongoDBClient
from lingularity.backend.metadata import language_metadata
from lingularity.backend.trainers import TrainerBackend
from .modes import TrainingMode


class SentenceTranslationTrainerBackend(TrainerBackend):
    def __init__(self, non_english_language: str, train_english: bool, mongodb_client: MongoDBClient):
        super().__init__(non_english_language, train_english, mongodb_client)

        TextToSpeech(self.language, mongodb_client)
        self._training_mode: Optional[Type[TrainingMode]] = None

    @property
    def training_mode(self) -> Optional[Type[TrainingMode]]:
        return self._training_mode

    @training_mode.setter
    def training_mode(self, mode: Type[TrainingMode]):
        assert self._training_mode is None, "training mode shan't be reassigned"
        self._training_mode = mode

    def set_item_iterator(self):
        assert self._training_mode is not None

        # get sentence data
        sentence_data = self._get_sentence_data()

        # get mode filtered sentence data
        filtered_sentence_data = self._training_mode.filter_sentence_data(sentence_data, self._non_english_language)

        self._set_item_iterator(training_items=filtered_sentence_data)

    @staticmethod
    def get_eligible_languages(mongodb_client: Optional[MongoDBClient] = None) -> List[str]:
        return list(language_metadata.keys())
