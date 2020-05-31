import sys
import os
import time
from typing import List
from itertools import groupby, chain
from bisect import insort
from operator import ge, le

import numpy as np

from src.trainers.trainer import Trainer
from src.webpage_interaction import ContentRetriever
from src.types.token_maps import Stem2SentenceIndices


# TODO: asynchronous stem map computation, dynamic mode specific occurrence frequency limits
#  enhancement of mode selection screen


class SentenceTranslationTrainer(Trainer):
	DEFAULT_NAMES = ('Tom', 'Mary')
	LANGUAGE_CORRESPONDING_NAMES = {'Italian': ['Alessandro', 'Christina'],
				  'French': ['Antoine', 'Amelie'],
				  'Spanish': ['Emilio', 'Luciana'],
				  'Hungarian': ['László', 'Zsóka'],
				  'German': ['Günther', 'Irmgard']}

	def __init__(self):
		super().__init__()
		self.webpage_interactor = ContentRetriever()

	def run(self):
		self.language = self.select_language()
		if self._language not in os.listdir(self.BASE_DATA_PATH):
			zip_file_link = self.webpage_interactor.download_zipfile(self._language)
			self.webpage_interactor.unzip_file(zip_file_link)
		self.sentence_data = self.parse_sentence_data()
		mode_selection = self.select_mode()
		if mode_selection != 'random':
			self.filter_sentences_mode_correspondingly(mode_selection)
		self.pre_training_display()
		self.train()

	# ---------------
	# INITIALIZATION
	# ---------------
	def select_language(self) -> str:
		if self.webpage_interactor.languages_2_ziplinks is None:
			print('Trying to connect to webpage...')
			self.webpage_interactor.get_language_ziplink_dict()
		sucessfully_retrieved = len(self.webpage_interactor.languages_2_ziplinks) != 0
		eligible_languages = list(self.webpage_interactor.languages_2_ziplinks.keys()) if sucessfully_retrieved else os.listdir(self.BASE_DATA_PATH)
		if 'English' not in eligible_languages:
			insort(eligible_languages, 'English')

		self.clear_screen()
		if len(eligible_languages) == 1:  # solely artificially appended english
			print('Please establish an internet connection in order to download sentence data.')
			print('Terminating program.')
			time.sleep(3)
			sys.exit(0)

		elif not sucessfully_retrieved:
			print("Couldn't establish a connection")

		starting_letter_grouped = groupby(eligible_languages, lambda x: x[0])
		print('Eligible languages: '.upper())
		for _, values in starting_letter_grouped:
			print(', '.join(list(values)))

		selection = self.resolve_input(input('\nSelect language: \n').title(), eligible_languages)
		if selection is None:
			return self.recurse_on_invalid_input(self.select_language)

		elif selection == 'English':
			eligible_languages.remove('English')
			reference_language_validity = False

			while not reference_language_validity:
				reference_language = self.resolve_input(input('Enter desired reference language: \n').title(), eligible_languages)
				if reference_language is None:
					print("Couldn't resolve input")
					time.sleep(1)
				else:
					selection = reference_language
					self.train_english, reference_language_validity = [True]*2
		return selection

	# -----------------
	# .MODE
	# -----------------
	def select_mode(self) -> str:
		modes = ('vocabulary acquisition', 'lowkey', 'random')
		explanations = (
			'show me sentences possessing an increased probability of containing rather infrequently used vocabulary',
			'show me sentences comprising exclusively commonly used vocabulary',
			'just hit me with dem sentences brah')

		self.clear_screen()

		print('MODES\n')
		for i in range(3):
			print(f'{modes[i].title()}: ')
			print('\t', explanations[i])
		print('\nSelect mode:\t')
		mode_selection = self.resolve_input(input().lower(), modes)
		if mode_selection is None:
			return self.recurse_on_invalid_input(self.select_mode)
		return mode_selection

	def filter_sentences_mode_correspondingly(self, mode: str):
		stems_2_indices = Stem2SentenceIndices.from_sentence_data(self.sentence_data, self.stemmer)

		def get_limit_corresponding_sentence_indices(occurrence_limit: int, filter_mode: str) -> List[int]:
			assert filter_mode in ['max', 'min']
			operator = ge if filter_mode == 'min' else le
			return list(chain.from_iterable((indices for indices in stems_2_indices.values() if operator(len(indices), occurrence_limit))))

		if mode == 'vocabulary acquisition':
			indices = get_limit_corresponding_sentence_indices(20, 'max')
		elif mode == 'lowkey':
			indices = get_limit_corresponding_sentence_indices(50, 'min')
		print('Getting corresponding sentences...')
		self.sentence_data = self.sentence_data[indices]

	def pre_training_display(self):
		self.clear_screen()
		instruction_text = f"""Database comprises {len(self.sentence_data):,d} sentences.\nPress Enter to advance to next sentence\nEnter 'vocabulary' to append new entry to language specific vocabulary file, 'exit' to terminate program.\n"""
		print(instruction_text)

		lets_go_translation = self.get_lets_go_translation()
		print(lets_go_translation, '\n') if lets_go_translation is not None else print("Let's go!", '\n')

	# -----------------
	# TRAINING LOOP
	# -----------------
	def train(self):
		indices = np.arange(len(self.sentence_data))
		np.random.shuffle(indices)
		self.sentence_data = self.sentence_data[indices]
		persevere = False

		while True:
			if not persevere:
				try:
					reference_sentence, translation = self.sentence_data[self.n_trained_items]
				except (ValueError, IndexError):
					continue
				if any(name in reference_sentence for name in self.DEFAULT_NAMES):
					reference_sentence, translation = self.convert_names([reference_sentence, translation])

				print(reference_sentence, '\t')
			else:
				persevere = False
			try:
				try:
					response = self.resolve_input(input("pending...").lower(), ['vocabulary', 'exit'])
					if response is not None:
						if response == 'vocabulary':
							self.append_2_vocabulary_file()
							print(" ")
							persevere = True
						elif response == 'exit':
							print('----------------')
							print("Number of faced sentences: ", self.n_trained_items)
							self.append_2_training_history()
							if self.n_trained_items > 4:
								self.plot_training_history()
							sys.exit()
				except KeyboardInterrupt:
					pass

			except SyntaxError:
				pass
			self.erase_previous_line()
			if not persevere:
				print(translation, '\n', '_______________')
				self.n_trained_items += 1

	def append_2_vocabulary_file(self):
		vocable = input(f'Enter {self.language} word/phrase: ')
		meanings = input('Enter meaning(s): ')

		with open(self.vocabulary_file_path, 'a+') as vocab_file:
			if os.path.getsize(self.vocabulary_file_path):
				vocab_file.write('\n')
			vocab_file.write(f'{vocable} - {meanings}')
		[self.erase_previous_line() for _ in range(2)]

	def convert_names(self, sentence_pair: List[str]) -> List[str]:
		if not self.LANGUAGE_CORRESPONDING_NAMES.get(self.language):
			return sentence_pair

		punctuation = sentence_pair[0][-1]
		for sentence_ind, sentence in enumerate(sentence_pair):
			sentence_tokens = sentence[:-1].split(' ')

			for name_ind, name in enumerate(self.DEFAULT_NAMES):
				try:
					ind = sentence_tokens.index(name)
					sentence_tokens[ind] = self.LANGUAGE_CORRESPONDING_NAMES[self.language][name_ind]
				except ValueError:
					pass
			sentence_pair[sentence_ind] = ' '.join(sentence_tokens) + punctuation

		return sentence_pair


if __name__ == '__main__':
	SentenceTranslationTrainer().run()
