#!/bin/env python36

'''
Script written for the intention to be used to randomize phrases with variable inputs.

For the extent of reading this, OBS writes print statments to a seperate log, so we don't setup logging statements as it's all handled by OBS for us.

Relalvent pages:
	- Official OBS scriping page: https://github.com/obsproject/obs-studio/wiki/Getting-Started-With-OBS-Scripting
	- Community made python scripting cheat sheet: https://github.com/upgradeQ/OBS-Studio-Python-Scripting-Cheatsheet-obspython-Examples-of-API

Author: Matthew Pogue - matthewpogue606+phraseRandomizer@gmail.com

'''

# Standard libraries
from pathlib import Path
from time import sleep
from random import shuffle, randint, choice as random_choice
from json import loads, dumps

# OBS - This isn't on pipy, so it can't be installed. Adding the comment will remove it from pylance
import obspython as obs # type: ignore

# Globals
PROJECT_NAME = 'phraseRandomizer'
SCRIPT_DIRECTORY = Path(__file__).parent.resolve()
SCRIPT_SETTINGS_FILE = SCRIPT_DIRECTORY / f'{PROJECT_NAME}.settings.json'
AVAILABLE_LANGUAGES = ['en']



# Phrase Randomizer used to generate phrases
########################################

class Phrase_Randomizer:
	''' A phrase randomizer used to generate random phrases from a master phrase list.

	Phrases can have a code to be replaced by information from any available list.

	Attributes:
		_lists_dir(Path): Directory in which to look for lists.
		_lists({str:[str]}: A dictionary of names to lists of strings to fill variables in phrases.
			i.e. if a phrase contains '{p}', a string from the list in _lists['p'] replaces '{p}' in the phrase.

		_phrases_master([str]): A public copy of the phrases. This isn't manipulated in the same way that _phrases is.
		_phrases([str]): A list of strings that is the master phrases. Phrases will be removed from this list if requested.

		_phrase_duplication(bool): Tells the class if we should remove phrases after they have been chosen.

		_min_phrase_count(int=2): The minimum number of phrases that can be in the working phrase list. Once it drops below this level, the phrases will be repopulated.
	'''

	def __init__(self, list_directory:Path) -> None:
		''' A tool for filling phrases with random information provided by list files.

		Arguments:
			list_directory: Directory to look for our lists.
		'''
		self._lists_dir = list_directory
		self._lists   = {}

		self._phrases_master = []
		self._phrases        = self._phrases_master

		self._phrase_duplication = True

		self._min_phrase_count = 2

	def _fill_phrase(self, phrase:str) -> None:
		''' Fills a single phrase with variables from all the lists.

		Arguments:
			phrase(str): Phrase to fill.
				{<list>:<num>}: where list is the name of the text file, num is the position in the list.
				i.e. "Make {p:1} high-five {p:2}" will confirm both of those names are different given there are more than two names in the list `lists/p.txt`.
				While "Every time {t} does something, {t} takes a shot" will result in completly random choices. They could be different, but there is a chance they could be the same. 1/n where n is the number of items in list `t.txt`
				Lists do not have to be single characters. i.e. "Get {human} off my swamp" will look in list `lists/human.txt`.
		'''
		# phrase = r'Every time {p} gets a kill with {i}, {p} and {p:1} have to take a shot'
		# First, lets grab the positions where our variables are
		''' We're doing some magic here, so lets explain '''
		# First, we're splitting phrase on left mustash. This leaves us with a list of elements, all of which (save the first) include a right mustash bracket (if the phrase is valid).
		positions = [chunk.split('}') for chunk in phrase.split('{')]
		# Then we're going to flatten our list. If you've never seen this method, it's great. There is no official way to do it, so have this stackoverflow link that I find ever time when looking it up https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
		positions = [_ for __ in positions for _ in __]
		# We should have a list where every odd indexed item is our fillable variables, lets grab them
		positions = positions[1::2]

		# Loading any lists that we don't have in this phrase
		for field in [field.split(':') for field in positions]:
			self._load_list(field[0])

		# Shuffling all our lists before replacing strings
		for value in self._lists.values():
			shuffle(value)

		# Starting with our first position:
		for position in positions:
			# Getting our count if it has one
			if ':' in position:
				list_name, index = position.split(':')
			else:
				list_name, index = position, None

			# Getting our index, and replacing with the given position if requested
			list_len = len(self._lists[list_name])
			if index is None:
				index = randint(0, list_len)
			phrase = phrase.replace(f'{{{position}}}', self._lists[list_name][int(index) % int(list_len)], 1)
		return phrase

	def _load_list(self, list_name:str) -> None:
		''' Loads a list from the file

		Will look in the self._lists_directory for the list_name.

		This will also check the list cache to see if we already have it loaded

		Arguments:
			list_name(str): Name of the list to look for. i.e. `people` will look for `people.txt`. Will only load list if we don't have it in cache.
		'''
		# Checking if we have this list already, returning if we don't
		if list_name in self._lists.keys():
			return

		# Attempting to open our list.
		try:
			list_file_path = self._lists_dir / f'{list_name}.txt'
			with open(list_file_path, 'r', encoding='utf-8') as list_file:
				self._lists[list_name] = [line.strip() for line in list_file.readlines()]

		# If that file doesn't exist, we let them know the file we were looking for and what directory we looked in.
		except FileNotFoundError as e:
			raise FileNotFoundError(f'Unable to find list `{list_file_path}`.') from e

	def get_dummy_phrases(self, count:int=1) -> list:
		''' Return a list of random filled phrases.

		This will not remove phrases even if the setting is on. You must use get_filled_phrase for that.

		Arguments:
			count(int=1): Number of phrases to generate

		Returns:
			List of generated phrases
		'''
		phrases = []
		for _ in range(count):
			filled_phrase = self._fill_phrase(random_choice(self._phrases))
			phrases.append(filled_phrase)

		return phrases

	def get_filled_phrase(self) -> str:
		''' Return a single phrase that has been populated with list information.

		Will remove phrase from working phrase list if setting is on.
		'''
		shuffle(self._phrases)
		phrase = self._fill_phrase(self._phrases[0])

		# Removing phrase if requested
		if self._phrase_duplication is False:
			print('removing a phrase')
			del self._phrases[0]
			# Checking if our phrases are running low and repopulating if needed
			if len(self._phrases) < self._min_phrase_count:
				self.update_phrases()

		# Returning our phrase
		print(f'Current phrases:\n{self._phrases}')
		return phrase

	def set_phrase_list(self, phrase_list:list) -> None:
		''' Updates the randomizers' copy of the phrase list.

		If the length of this is the same or less than our _min_phrase_count, then this will throw a value error.

		Arguments:
			phrase_list(list:str): A list of phrases from the user.
		'''
		# First, we check for length
		if len(phrase_list) <= self._min_phrase_count:
			raise ValueError(f'Phrase list must include more than {self._min_phrase_count} phrases.')

		self._phrases_master = phrase_list

		# Now we need to update our working phrase lists
		self.update_phrases()

	def set_lists_dir(self, lists_dir:Path) -> None:
		''' Updates the path in whci to search for lists.

		Arguments:
			lists_dir(Path): The directory in which to search for our lists. They should be immediate children of this directory.
		'''
		print(f'setting our new lists directory to `{Data.lists_dir}')
		self._lists_dir = Path(lists_dir).resolve()

	def clear_list_cache(self) -> None:
		''' Forces a clear of the list cache. Useful if you've updated a list while the script has been launched and seen the list.
		'''
		self._lists = {}

	def set_phrase_duplication(self, phrase_duplication:bool=True) -> None:
		''' Configures the randomizer to give duplicated phrases. If this is set to false, an internal list of phrases are used to remove phrases from.
		'''
		print(f'Updating phrase duplication to {phrase_duplication}')
		self._phrase_duplication = phrase_duplication

		# Now we need to update our phrase lists
		self.update_phrases()

	def update_phrases(self) -> None:
		''' Updates the working copy of phrases with our master list.

		Typically used when we're changing our phrase duplication setting, or updating our phrases master list.
		'''
		# If we're duplicating, we're just setting our internal list as a pointer to our external list
		if self._phrase_duplication:
			self._phrases = self._phrases_master

		# Otherwise, we're going to copy our phrases
		else:
			self._phrases = self._phrases_master.copy()


# Language class to help manage language translation
########################################

class Lang:
	def __init__(self, code:str):
		# Attempting to get the given language code
		lang_dir = SCRIPT_DIRECTORY / 'lang'
		print(f'Getting language code `{code}` in {lang_dir}')
		lang_file =  lang_dir / f'{code}.json'

		# If we don't have that language file, we throw an error
		if not lang_file.is_file():
			raise Exception('Lang file not found in %s' % lang_dir)

		# Otherwise, we load our messages from that language file
		with open(lang_file, 'r', encoding='utf-8') as language_file:
			self.messages = loads(language_file.read())

	def t(self, key:str):
		''' Translate function to provide a message from the given key

		Arguments:
			key(str): The name of the key to look for in our lanaugage dictionary
		'''
		if key in self.messages:
			return self.messages[key]

		return key

# OBS data class. All data here is persistant
########################################

class Data:
	# Required variables
	props = None
	settings = None

	# Creating our language translator
	lang_code = 'en'
	lang = Lang(lang_code)

	phrases = []
	phrases_unique = False
	source_name = ''
	phrase_lifetime = 8000
	lists_dir = SCRIPT_DIRECTORY / 'lists'
	Randomizer = Phrase_Randomizer(lists_dir)

	# Animation Settings
	animation_enabled      = True
	animation_phrase_count = 12
	animation_length       = 4
	animation_delay        = 52
	animation_deceleration = 52

	# Sound settings
	sound_enabled = False
	sound_path = SCRIPT_DIRECTORY / 'sounds' / 'alert.mp3'
	media_source = None # Null pointer
	output_index = 63 # Last index


# ------------------------------------------------------------

class Hotkey:
	def __init__(self, callback, obs_settings, _id, description):
		self.obs_data = obs_settings
		self.hotkey_id = obs.OBS_INVALID_HOTKEY_ID
		self.hotkey_saved_key = None
		self.callback = callback
		self._id = _id
		self.description = description

		self.load_hotkey()
		self.register_hotkey()
		self.save_hotkey()

	def register_hotkey(self):
		self.hotkey_id = obs.obs_hotkey_register_frontend(
			'htk_id' + str(self._id), self.description, self.callback
		)
		obs.obs_hotkey_load(self.hotkey_id, self.hotkey_saved_key)

	def load_hotkey(self):
		self.hotkey_saved_key = obs.obs_data_get_array(
			self.obs_data, 'htk_id' + str(self._id)
		)
		obs.obs_data_array_release(self.hotkey_saved_key)

	def save_hotkey(self):
		self.hotkey_saved_key = obs.obs_hotkey_save(self.hotkey_id)
		obs.obs_data_set_array(
			self.obs_data, 'htk_id' + str(self._id), self.hotkey_saved_key
		)
		obs.obs_data_array_release(self.hotkey_saved_key)


class HotkeyStore:
	htk_copy = None

# ------------------------------------------------------------

class OBS_Source:
	def __init__(self, source_name:str):
		self.source_name = source_name
		self._obs_source = None

	def __enter__(self):
		''' Custom magic methods for using an obs source. Checks for a valid reference.

		This will get a reference to ths source using the proper methods, as well as create dummy data for you to fill. See class methods for more details.

		This defaults to opening the source with the name in Data.source_name.
		'''
		self._obs_source = obs.obs_get_source_by_name(self.source_name)

		if self._obs_source is None:
			raise Exception(f'Could not find source with name {self.source_name}')

		return self

	def __exit__(self, _, __, ___):
		''' Closing statement for keyword 'with' usage. See self.__enter__ for more details.
		'''
		obs.obs_source_release(self._obs_source)
		self._obs_source = None

	def _check_source(self):
		''' Checks if we have a valid source. If we don't, this function raises a ValueError detailing that we don't have a valid source set.

		This can be called at the beginning of methods that require a valid source, or this class to be used with the 'with' keyword.
		'''
		if self._obs_source is None:
			raise ValueError('No source found. Please make sure that there is a referenced source and that the source is opened using `with`')

	def set_data(self, data:dict):
		''' Updates the data of the source. this is a general use function to update obs sources.

		Arguments:
			data(dict): Dictionary in JSON style that will correlate with data in the source you wish to alter.
		'''
		# First, we check if we have a valid source
		self._check_source()

		# Creating a dataset with our dictionary
		source_data = obs.obs_data_create_from_json(dumps(data))

		# We'll attempt to update our source. Doing this in a try as we need to release reference to data if there is an issue.
		try:
			obs.obs_source_update(self._obs_source, source_data)
		finally:
			obs.obs_data_release(source_data)

	def set_text(self, new_text:str=''):
		''' Convinence function to quickly update the text. Utalizes obs_source.set_data().

		Arguments:
			new_text(str=''): String that contains the new text. This defaults to an emptry string to remove text data from the source.
		'''
		self.set_data({
			'text': new_text
		})

	def set_opacity(self, opacity:float=0):
		''' Convinence function to quickly update the opacity. Utalizes obs_source.set_data().

		Arguments:
			opacity(float=0): The new opacity of the source.
		'''
		self.set_data({
			'opacity': opacity
		})


	def text_animation(self, length:float, deceleration_scale:float, text_list:list):
		''' Plays a budget text animation by changing the source's text value with a delay following the slope of a cubic.

		I've played around with this function for many an hour to perfect. I've landed on a cubic function modeled by this wolframapha link.
		https://www.wolframalpha.com/input?i=52+*+%28x+%2F+8000+*+2%29+%5E+%281%2F4%29
		Where deceleration_scale is 52 and length is 8000 (8 seconds)
		This functions always starts with very fast delays and slows down as the index increases.

		Arguments:
			length(float): The length of the animation in ms.
			deceleration_scale(float): The scale at which to decelerate.
			text_list(list): A list of text to use as text examples in animation. Length must be more than 1.
		'''
		print('Playing animation')
		animation_length = length

		# Raising an error if our list is not less than 1
		num_texts = len(text_list)
		if not num_texts > 1:
			raise ValueError('Size of text_list must be more than 1')

		# Playing our animation. Capping our animation after 800 loops to prevent an infinite loop
		for deceleration_index in range(1, 400):
			anim_delay = (deceleration_index ** 4) / (animation_length * deceleration_scale)

			# Sleeping, then continuing if we have time remaining
			length = length - anim_delay
			sleep(anim_delay / 1000)

			# Displaying a random phrase unless our time is too short
			if length < 0:
				break

			# Setting our text
			self.set_text(
				text_list[deceleration_index % num_texts]
			)

def source_delayed_hide():
	''' Hides the source immediatly, but is de-referenced from obs-source to allow for the use of timers.
	'''
	# Removing any timers for this method
	obs.remove_current_callback()

	# Setting our source opacity to 0
	with OBS_Source(Data.source_name) as source:
		source.set_text('')

def source_randomize_text():
	''' Updates the text displayed in the source.

	This uses the phrase randomizer to generate the phrases used in the animation as well as the chosen phrase.

	This function is also in charge of removing the phrase from our internal list if requested.

	'''
	print('Randomizing source text')

	# Opening our source
	with OBS_Source(Data.source_name) as source:

		# Displaying our animation if requested
		if Data.animation_enabled:
			source.text_animation(
				Data.animation_length * 1000, # In seconds
				Data.animation_deceleration,
				Data.Randomizer.get_dummy_phrases(Data.animation_phrase_count)
			)

		# Displaying value requested as the final result reguardless if we have an animation
		phrase = Data.Randomizer.get_filled_phrase()
		print(f'Setting final text to {phrase}')
		source.set_text(phrase)

		# Settings a timer to remove text after delay
		if Data.phrase_lifetime != 0:
			obs.timer_add(source_delayed_hide, Data.phrase_lifetime)

	# Playing sound if requested
	if Data.sound_enabled:
		play_sound()

def play_sound():
	if Data.media_source == None:
		Data.media_source = obs.obs_source_create_private(
			'ffmpeg_source', 'Global Media Source', None
		)
	s = obs.obs_data_create()
	obs.obs_data_set_string(s, 'local_file', Data.sound_path)
	obs.obs_source_update(Data.media_source, s)
	obs.obs_source_set_monitoring_type(
		Data.media_source, obs.OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT
	)
	obs.obs_data_release(s)

	obs.obs_set_output_source(Data.output_index, Data.media_source)

def save_settings():
	''' Saves settings to the SCRIPT_SETTINGS file into Data.settings.
	'''
	# Checking if we have settings to save
	if Data.settings:
		# Attempting to write out settings
		try:
			with open(SCRIPT_SETTINGS_FILE, 'w', encoding='utf-8') as settings_file:
				settings_file.write(obs.obs_data_get_json(Data.settings))
		except Exception as e:
			print(e, f'Unable to save settings to `{SCRIPT_SETTINGS_FILE}`')
	print(f'Settings file `{SCRIPT_SETTINGS_FILE}` updated.')

def load_settings():
	''' Load settings from the SCRIPT_SETTINGS file into Data.settings.
	'''
	if SCRIPT_SETTINGS_FILE.is_file():
		# If our settinsg exist, we load the file
		with open(SCRIPT_SETTINGS_FILE, 'r', encoding='utf-8') as settings_file:
			Data.settings = obs.obs_data_create_from_json(settings_file.read())

		# If our language exists in our settings file, we load that language
		lang_code = obs.obs_data_get_string(Data.settings, 'lang')
		if lang_code:
			Data.lang_code = lang_code
			Data.lang = Lang(lang_code)



# Event methods
########################################

def on_click_get_random_phrase(_=None, __=None):
	''' When someone clicks the random button on the Scripts settings menu
	'''
	print('Random phrase button pressed')
	# Updates the text
	source_randomize_text()

def on_hotkey_get_random_phrase(pressed):
	''' When someone hits the hotkey to generate the random phrase
	'''
	print('Random phrase hotkey pressed')
	if pressed:
		on_click_get_random_phrase()

def on_click_clear_cache(_, __):
	''' Clearing our list cache
	'''
	Data.Randomizer.clear_list_cache()

def on_click_update_phrases():
	''' Updates our internal phrases list when this button is pressed.

	This lets up keep two phrase lists when phrase_duplication is unchecked.
	'''
	# The randomizer handles all the phrase duplication, so we call their helper function
	Data.Randomizer.update_phrases()

# ------------------------------------------------------------

hotkey_get_random = HotkeyStore()
load_settings()

# ------------------------------------------------------------



''' Script life-cycle

The script life-cycle are functions executed by OBS during it's launch, shutdown, or when it receives a request to update information.
https://github.com/upgradeQ/OBS-Studio-Python-Scripting-Cheatsheet-obspython-Examples-of-API

Scripts should be organized in order of execution for a typical session.

'''
def script_defaults(settings):
	''' Called to initalize default values in data settings. This is what gets displayed as settings for the script.

	https://obsproject.com/docs/scripting.html#script_defaults
	'''
	# Language settings defaults
	obs.obs_data_set_default_string(settings, 'lang', 'en')

	# Phrases section
	obs.obs_data_set_default_string(settings, 'phrases_list',    'Each\nLine\nis\na\nPhrase')
	obs.obs_data_set_default_bool(  settings, 'phrases_unique',  Data.phrases_unique)
	obs.obs_data_set_default_int(   settings, 'phrase_lifetime', Data.phrase_lifetime)
	obs.obs_data_set_default_string(settings, 'lists_dir',       str(Data.lists_dir))

	# Animation settings defaults
	obs.obs_data_set_default_bool( settings, 'animation_enabled',      Data.animation_enabled)
	obs.obs_data_set_default_int(  settings, 'animation_phrase_count', Data.animation_phrase_count)
	obs.obs_data_set_default_int(  settings, 'animation_delay',        Data.animation_delay)
	obs.obs_data_set_default_int(  settings, 'animation_length',       Data.animation_length)
	obs.obs_data_set_default_int(  settings, 'animation_deceleration', Data.animation_deceleration)

	# Sound settings defaults
	obs.obs_data_set_default_bool(  settings, 'sound_enabled', Data.sound_enabled)
	obs.obs_data_set_default_string(settings, 'sound_path',    str(Data.sound_path))


def script_description():
	''' Setting the description of the plugin
	'''
	return Data.lang.t('description')


def script_load(settings):
	''' Called for one-time init using values of data settings
	'''
	hotkey_get_random.htk_copy = Hotkey(on_hotkey_get_random_phrase, settings, 'get_random_text', Data.lang.t('get_random'))


def script_update(settings):
	''' Called during initalization and after any update to the settings.

	Arguments:
		settings: the provided settings from OBS
	'''
	Data.settings = settings

	# Updating language settings
	Data.lang_code = obs.obs_data_get_string(settings, 'lang')
	Data.lang      = Lang(Data.lang_code)

	# Updating source name
	Data.source_name = obs.obs_data_get_string(settings, 'source')

	# Gathering our phrases
	Data.phrases = obs.obs_data_get_string(settings, 'phrases').splitlines()
	Data.phrases = [phrase.strip().replace('\\n', '\n') for phrase in Data.phrases] # The list comp here is replacing the literal '\n' in the phrases with a newline char
	# Removing empty strings from list
	if '' in Data.phrases:
		Data.phrases.remove('')

	# User is requesting that we don't duplicate phrases
	Data.phrases_unique = obs.obs_data_get_bool(settings, 'phrases_unique')
	Data.Randomizer.set_phrase_duplication(not Data.phrases_unique)

	# Lists folder and phrase lifetime
	Data.phrase_lifetime = obs.obs_data_get_int(   settings, 'phrase_lifetime')
	Data.lists_dir       = obs.obs_data_get_string(settings, 'lists_dir')

	# Getting animation settings
	Data.animation_enabled      = obs.obs_data_get_bool(settings, 'animation_enabled')
	Data.animation_phrase_count = obs.obs_data_get_int( settings, 'animation_phrase_count')
	Data.animation_deceleration = obs.obs_data_get_int( settings, 'animation_deceleration')
	Data.animation_length       = obs.obs_data_get_int( settings, 'animation_length')
	Data.animation_delay        = obs.obs_data_get_int( settings, 'animation_delay')

	# Getting sound settings
	Data.sound_enabled = obs.obs_data_get_bool(  settings, 'sound_enabled')
	Data.sound_path    = obs.obs_data_get_string(settings, 'sound_path')

	# Updating our randomizer
	Data.Randomizer.set_phrase_list(Data.phrases)
	Data.Randomizer.set_lists_dir(Data.lists_dir)

	# Saving our settings to file
	save_settings()


def script_save(_):
	''' Called when saving the script

	https://obsproject.com/docs/scripting.html#script_save
	'''
	hotkey_get_random.htk_copy.save_hotkey()
	save_settings()


def script_properties():
	''' Called to define how to display the script properties.
	https://obsproject.com/docs/scripting.html#script_properties
	'''
	Data.props = obs.obs_properties_create()

	# Language selection
	######################################
	language_list = obs.obs_properties_add_list(Data.props,
		'lang',
		'Language',
		obs.OBS_COMBO_TYPE_LIST,
		obs.OBS_COMBO_FORMAT_STRING)

	for lang in AVAILABLE_LANGUAGES:
		obs.obs_property_list_add_string(language_list, lang, lang)


	# Source selection
	######################################
	source_list = obs.obs_properties_add_list(Data.props,
		'source',
		Data.lang.t('source'),
		obs.OBS_COMBO_TYPE_EDITABLE,
		obs.OBS_COMBO_FORMAT_STRING)

	# Checking if we have a valid list of sources
	sources = obs.obs_enum_sources()
	# Checking if there are sources
	if sources is not None:
		for source in sources:
			# Only allow text id's
			if obs.obs_source_get_unversioned_id(source) in ['text_gdiplus', 'text_ft2_source']:
				source_name = obs.obs_source_get_name(source)
				obs.obs_property_list_add_string(source_list, source_name, source_name)

	# Releasing our access to sources
	obs.source_list_release(sources)

	# Phrases field
	######################################
	obs.obs_properties_add_text(Data.props,
		'phrases',
		Data.lang.t('Phrases'),
		obs.OBS_TEXT_MULTILINE)

	obs.obs_properties_add_button(Data.props,
		'phrase_update_button',
		Data.lang.t('phrases_update'),
		on_click_update_phrases)

	obs.obs_properties_add_bool(Data.props,
		'phrases_unique',
		Data.lang.t('phrases_unique'))

	obs.obs_properties_add_int_slider(Data.props,
		'phrase_lifetime',
		Data.lang.t('phrase_lifetime'),
		0, 16000, 250)

	obs.obs_properties_add_path(Data.props,
		'lists_dir',
		Data.lang.t('lists_dir'),
		obs.OBS_PATH_DIRECTORY,
		'dir',
		str(SCRIPT_DIRECTORY))

	# Animation settings
	######################################
	obs.obs_properties_add_bool(Data.props,
		'animation_enabled',
		Data.lang.t('animation_enabled'))

	obs.obs_properties_add_int_slider(Data.props,
		'animation_phrase_count',
		Data.lang.t('animation_phrase_count'),
		2, 80, 1)

	obs.obs_properties_add_int_slider(Data.props,
		'animation_length',
		Data.lang.t('animation_length'),
		1, 10, 1)

	obs.obs_properties_add_int_slider(Data.props,
		'animation_delay',
		Data.lang.t('animation_delay'),
		1, 200, 1)

	obs.obs_properties_add_int_slider(Data.props,
		'animation_deceleration',
		Data.lang.t('animation_deceleration'),
		1, 200, 1)

	# Sound settings
	######################################
	obs.obs_properties_add_bool(Data.props,
		'sound_enabled',
		Data.lang.t('sound_enabled'))

	obs.obs_properties_add_path(Data.props,
		'sound_path',
		Data.lang.t('sound_path'),
		obs.OBS_PATH_FILE,
		'audio',
		str(SCRIPT_DIRECTORY))

	# Inputs
	######################################
	obs.obs_properties_add_button(Data.props,
		'phrase_generate_button',
		Data.lang.t('get_random'),
		on_click_get_random_phrase)

	obs.obs_properties_add_button(Data.props,
		'clear_cache_button',
		Data.lang.t('clear_cache'),
		on_click_clear_cache)

	return Data.props