from enum import Enum

from backend.src.trainers.sentence_translation import modes
from backend.src.trainers.sentence_translation.modes import SentenceDataFilter


class SentenceFilterMode(Enum, str):
    DictionExpansion = 'diction_expansion'
    Simple = 'simple'
    Random = 'random'


MODE_2_EXPLANATION = {
    SentenceFilterMode.DictionExpansion: 'show me sentences containing rather infrequently used vocabulary',
    SentenceFilterMode.Simple: 'show me sentences comprising exclusively commonly used vocabulary',
    SentenceFilterMode.Random: 'just hit me with dem sentences'
}


def sentence_filter(mode: SentenceFilterMode) -> SentenceDataFilter:
    return getattr(modes, mode.value).filter_sentence_data