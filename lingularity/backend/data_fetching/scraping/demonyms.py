from typing import Optional
import logging

from bs4 import BeautifulSoup
from textacy.similarity import levenshtein

from .utils import read_page_source


def scrape_demonym(country_name: str) -> Optional[str]:
    """
        Args:
            country_name: uppercase
        Returns:
            None in case of irretrievability, otherwise best fit demonym """

    page_url = f'http://en.wikipedia.org/wiki/{country_name}'

    soup: BeautifulSoup = read_page_source(page_url)

    if (demonym_tag := soup.find('a', href='/wiki/Demonym')) is None:
        return None

    is_demonym = lambda demonym_candidate: country_name.startswith(demonym_candidate[:2])

    demonym = None
    for element in list(demonym_tag.next_elements)[1:10]:
        if element.name is None:
            for demonym_candidate in filter(lambda c: c.istitle(), element.split(' ')):
                if not demonym:
                    demonym = demonym_candidate
                else:
                    if is_demonym(demonym_candidate) and levenshtein(country_name, demonym_candidate) > levenshtein(country_name, demonym):
                        demonym = demonym_candidate

    logging.info(f'demonym: {demonym}')
    return demonym
