#!/bin/env python36

'''
Script written for the intention to be used to randomize phrases with variable inputs.

Relalvent pages:
	- Official OBS scriping page: https://github.com/obsproject/obs-studio/wiki/Getting-Started-With-OBS-Scripting
	- Community made python scripting cheat sheet: https://github.com/upgradeQ/OBS-Studio-Python-Scripting-Cheatsheet-obspython-Examples-of-API

Author: Matthew Pogue - matthewpogue606+phraseRandomizer@gmail.com

'''

# Standard libraries
from pathlib import Path
from time import sleep
from random import shuffle, randint, choice as random_choice
import json

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
	def __init__(self, list_directory:Path):
		''' A tool for filling phrases with random information provided by list files.

		Arguments:
			list_directory: Directory to look for our lists.

		'''
		self._list_directory = list_directory
		self._phrases = []
		self._lists   = {}

	def _fill_phrase(self, phrase:str):
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


	def _load_list(self, list_name:str):
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
			list_file_path = self._list_directory / f'{list_name}.txt'
			with open(list_file_path, 'r', encoding='utf-8') as list_file:
				self._lists[list_name] = [line.strip() for line in list_file.readlines()]

		# If that file doesn't exist, we let them know the file we were looking for and what directory we looked in.
		except FileNotFoundError as e:
			raise FileNotFoundError(f'Unable to find list `{list_file_path}`.') from e

	def _get_next_field(self, phrase:str, start:int):
		try:
			left  = phrase.index('{', start)
			right = phrase.index('}', left) + 1
			return (left, right)
		except ValueError:
			return (None, None)


	def get_random_phrases(self, count:int=1) -> list:
		''' Return a list of random phrases.

		Arguments:
			count(int=1): Number of phrases to generate

		Returns:
			List of generated phrases
		'''
		print(f'Getting {count} random phrases')
		print(self._phrases)
		phrases = []
		for _ in range(count):
			filled_phrase = self._fill_phrase(random_choice(self._phrases))
			phrases.append(filled_phrase)

		return phrases


	def set_phrase_list(self, phrase_list:list):
		''' Updates the randomizers' copy of the phrase list.

		Arguments:
			phrase_list(list:str): A list of phrases from the user.
		'''
		self._phrases = phrase_list

	def clear_list_cache(self):
		''' Forces a clear of the list cache. Useful if you've updated a list while the script has been launched and seen the list.
		'''
		self._lists = {}

	# def eager_load_lists(self):
		''' A function to increase performance during processing-intense moments.

		This forces the class to load all lists in the list directory to prevent having to look for them during runtime.
		'''
		#@TODO Impliment list eager loading

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
			self.messages = json.loads(language_file.read())

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
	source_name = ''
	Randomizer = Phrase_Randomizer(SCRIPT_DIRECTORY / 'lists')

	# Animation Settings
	animation_enabled      = True
	animation_length       = 4
	animation_delay        = 52
	animation_deceleration = 52

	# Sound settings
	sound_enabled = False
	sound_path = ''
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

def update_text(phrases:list):
	''' Updates the text displayed in the source
	'''
	print('Updating text')

	# Getting reference to our source and some example data
	source      = obs.obs_get_source_by_name(Data.source_name)
	source_data = obs.obs_data_create()

	# If our source is invalid, we're going to do absolutely nothing
	if source is None:
		raise Exception(f'Source `{Data.source_name}` not found')

	# Displaying our animation if requested
	print('Playing animation')
	if Data.animation_enabled:
		play_animation(source_data, source, phrases)

	# Displaying just the value if requested
	else:
		phrase = random_choice(phrases)
		print(f'Setting text to {phrase}')
		obs.obs_data_set_string(source_data, 'text', phrase)
		obs.obs_source_update(source, source_data)

	# Reasing access to our data and source now that we're done
	obs.obs_data_release(source_data)
	obs.obs_source_release(source)

	# Playing sound if requested
	if Data.sound_enabled:
		play_sound()

def play_animation(source_data, source, phrases):
	print('Playing animation')
	# Some values for easy reference
	anim_delay        = Data.animation_delay / 1000 # in ms
	anim_deceleration = Data.animation_deceleration / 1000 # in ms
	anim_length       = Data.animation_length + anim_delay

	deceleration_index = 1
	while anim_length > 0:
		# Sleeping, then continuing if we have time remaining
		anim_length = anim_length - anim_delay
		sleep(anim_delay)

		# Displaying a random phrase
		obs.obs_data_set_string(source_data, 'text', phrases[deceleration_index % len(phrases)])
		obs.obs_source_update(source, source_data)

		# Calculating how much sleep time, decel, and the remaining time for our animation.
		''' I've spent quite a bit on this animation function. This is a cubic function that is scaled by the animation length. This keeps the animation smooth reguardless the time. If you find something better please submit a pull request :)
		'''
		anim_delay = anim_deceleration * (deceleration_index / anim_length * 2) ** (1/4) # Cubic root
		deceleration_index += 1

		# Killing after 200 iterations just in case
		if deceleration_index > 200:
			break

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



# Events
########################################

def on_click_get_random_phrase(_=None, __=None):
	''' When someone clicks the random button on the Scripts settings menu
	'''
	print('Random phrase button pressed')
	# Generate random phrases
	phrases = Data.Randomizer.get_random_phrases(14)
	# Update the text with the phrase
	update_text(phrases)

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
	obs.obs_data_set_default_string(settings, 'phrases', 'Each\nLine\nis\na\nPhrase')

	# Animation settings defaults
	obs.obs_data_set_default_bool(settings, 'animation_enabled',      Data.animation_enabled)
	obs.obs_data_set_default_int( settings, 'animation_delay',        Data.animation_delay)
	obs.obs_data_set_default_int( settings, 'animation_length',       Data.animation_length)
	obs.obs_data_set_default_int( settings, 'animation_deceleration', Data.animation_deceleration)

	# Sound settings defaults
	obs.obs_data_set_default_string(settings, 'sound_path', str(SCRIPT_DIRECTORY / 'alert.mp3'))

	# Language settings defaults
	obs.obs_data_set_default_string(settings, 'lang', 'en')


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
	# Gathering our phrases
	phrases = obs.obs_data_get_string(settings, 'phrases').splitlines()
	phrases = [phrase.strip().replace('\\n', '\n') for phrase in phrases]
	# Removing empty strings from list
	if '' in phrases:
		phrases.remove('')

	Data.settings    = settings
	Data.phrases     = phrases
	Data.source_name = obs.obs_data_get_string(settings, 'source')
	Data.Randomizer.set_phrase_list(Data.phrases)

	# Getting animation settings
	Data.animation_enabled      = obs.obs_data_get_bool(settings, 'animation_enabled')
	Data.animation_deceleration = obs.obs_data_get_int( settings, 'animation_deceleration')
	Data.animation_length       = obs.obs_data_get_int( settings, 'animation_length')
	Data.animation_delay        = obs.obs_data_get_int( settings, 'animation_delay')

	# Getting sound settings
	Data.sound_enabled = obs.obs_data_get_bool(  settings, 'sound_enabled')
	Data.sound_path    = obs.obs_data_get_string(settings, 'sound_path')

	# Getting language settings
	Data.lang_code = obs.obs_data_get_string(settings, 'lang')
	Data.lang      = Lang(Data.lang_code)

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

	# Animation settings
	######################################
	obs.obs_properties_add_bool(Data.props,
		'animation_enabled',
		Data.lang.t('animation_enabled'))

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
		'')

	# Inputs
	######################################
	obs.obs_properties_add_button(Data.props,
		'button',
		Data.lang.t('get_random'),
		on_click_get_random_phrase)

	obs.obs_properties_add_button(Data.props,
		'button2',
		Data.lang.t('clear_cache'),
		on_click_clear_cache)

	return Data.props