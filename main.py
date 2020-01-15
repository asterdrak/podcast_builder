#!/usr/bin/env python3

"""
That module allows to collect recordings and additional sounds with multiple
directory structure described in config.yaml and build single sounds with it.

Execution params:
--build       - build output files
--debug       - show debug notes (more descriptive output)
--just-one    - proceeds only first directory from config.yaml and quits
--skip        - skip building perform (makes sense only with -i option)
                it only reads classes definitions and creates PodcastBuilder object (no action taken)
-i            - interactive mode, starts python iterpreter at the and
                shortcuts (interpreter variables):
                    p -     podcasts list
                    b -     PodcastBuilder object
                    play -  play sound
"""

import logging
import logging.config
import sys
import code
import glob
from inspect import getframeinfo, stack

from pydub import AudioSegment

from src.config_parser import ConfigParser
from src.sound_utils import detect_leading_silence, detect_leading_microphone_error

logging.config.fileConfig('src/logging.conf')
logging.getLogger().setLevel(logging.DEBUG if '--debug' in sys.argv else logging.INFO)


class PodcastBuilder():

    """
    Top level interface to run model.
    Reads configuration from 'config.yaml'.
    Resolves files from directory settings.
    Builds multiple podcasts and upload it to directories.
    """

    def __init__(self):
        self.config = ConfigParser('config.yaml').read()
        self.podcasts = []

    def perform(self):
        """ Top level run for the module. """
        logging.info('Podcasts building started')
        skip_rest = '--just-one' in sys.argv

        for dirname, dirconfig in self.config.dirs().items():
            logging.debug('Reading config for podcast "%s"\nconfig: %s', dirname, str(dirconfig))
            podcast = Podcast(dirname, dirconfig, self.config).resolve_filenames()
            podcast.read_files()
            podcast.clean()
            podcast.build_background()
            if '--build' in sys.argv:
                podcast.join(background=True)
                podcast.save()

            else:
                logging.warning('This is dry run, build files will not be created.'
                                ' To perform full run use --build option')

            self.podcasts.append(podcast)

            if skip_rest:
                break

        logging.info('Podcasts building ended%s', ', build file was not generated due to dry run. '
                     'Use --build to generate output file' if '--build' not in sys.argv else '')
        return self

    def __repr__(self):
        return 'config: {}'.format(self.config)


class Podcast():
    """
    - Resolves configuration schedule to filenames
    - Represents podcast directory with config and schedule.
    """

    def __init__(self, dirname, dirconfig, config):
        logging.info('Proceeding podcast "%s" in dir "%s"', dirconfig['name'], dirname)
        self.dirname = dirname
        self.dirconfig = dirconfig
        self.config = config
        self.schedule = []
        self.output = AudioSegment.empty()
        self.background = None

    def build_background(self):
        background = Sound(self.config['background']).read_file()
        schedule = [[len(sound.file), sound.is_voice] for sound in self]
        total_len = sum(s[0] for s in schedule)
        background_file = background.file * (total_len // len(background.file) + 1)# + background.raw_file + sound.volume_transformation

        aggregated_schedule = [schedule[0]]
        for (duration, is_voice) in schedule[1:]:
            if is_voice == aggregated_schedule[-1][1]:
                aggregated_schedule[-1][0] += duration
            else:
                aggregated_schedule.append([duration, is_voice])

        self.background = AudioSegment.empty()

        begginning = 0
        for ending, is_voice in aggregated_schedule[:-1]:
            if is_voice:
                from pydub.generators import Sine
                # self.background += Sine(600).to_audio_segment(ending) - 20
                self.background += background_file[begginning:begginning+ending].fade_in(300).fade_out(300)
                # self.background += background_file[begginning:ending].fade_in(300).fade_out(300)
            else:
                self.background += AudioSegment.silent(duration=ending)

            begginning += ending + 1

        if aggregated_schedule[-1][1]:
            # is voice (the last piece, we use ending)
            self.background += background_file[-aggregated_schedule[-1][0]:]

        return self.background

    def clean(self):
        """ Takes each schedule sound and cuts it's head and tail silence. """
        for index, sound in enumerate(self.schedule):
            if sound.clean:
                logging.debug('Cleaning sound "%s"', sound.filename)
                file = sound.file.fade_in(sound.before_cleaning_fade).fade_out(sound.before_cleaning_fade)
                start = detect_leading_silence(file, silence_threshold='auto')
                detected_ending_silence = -detect_leading_silence(file.reverse(), silence_threshold=-55)
                stop = detected_ending_silence if detected_ending_silence else -1
                logging.debug('Cutting with %s', str(slice(start, stop)))
                if start < 100:
                    logging.warning('The leading silence cut is negligible (%d ms) it is probably a mistake.'
                                    ' index in schedule: %d, file: "%s"', start, index, sound.filename)
                sound.clean_file = file[start:stop]

                # cleaning fallback - detect leading microphone error
                microphone_error_ends = detect_leading_microphone_error(sound)
                if microphone_error_ends:
                    logging.debug('Cleaning fallback - Detected leading microphone error (%d ms) for file: "%s"',
                                  microphone_error_ends, sound.filename)
                    sound.clean_file = sound.clean_file[microphone_error_ends:]

                # after_cleaning_fade_in
                silence = AudioSegment.silent(duration=self.config.get('default_silence_around_voice') or 500)
                sound.clean_file = silence + sound.clean_file.fade_in(sound.fade_in).fade_out(sound.fade_out) + silence
            else:
                logging.debug('Cleaning sound "%s" WAS SKIPPED due to clean=False option', sound.filename)

            sound.cleaning_performed = True

    def read_files(self):
        """ Reads sound files from the config schedule (resolved filenames) and apply innitial transformation. """
        for sound in self.schedule:
            sound.read_file()
            if not sound.clean:
                logging.debug('Fading in: %s, out: %s', sound.fade_in, sound.fade_out)
                sound.file = sound.file.fade_in(sound.fade_in).fade_out(sound.fade_out)


        return self
    
    def __getitem__(self, index):
        return self.schedule[index]

    def resolve_filenames(self):
        """ Resolves files search names to full relative file names. """
        for search_name in self.dirconfig['schedule']:
            self.schedule.append(Sound(self._special_name(search_name) or self._name(search_name)))

        return self

    def join(self, background=False):
        """ Joins all sounds from schedule and puts it in output variable. """
        self.output = AudioSegment.empty()

        for sound in self.schedule:
            self.output += sound.file

        if background:
            self.output = self.output.overlay(self.background).fade_out(250)
        return self

    def save(self):
        """ Saves output sound to proper file. """
        self.output.export('{}/output - {}.flac'.format(self.dirname, self.dirconfig.get('name', '')))

        return self

    def _special_name(self, sound_search_name):
        return self.config[sound_search_name] if sound_search_name in self.config else None

    def _name(self, sound_search_name):
        names = glob.glob('{}/{}'.format(self.dirname, sound_search_name))
        if not names:
            logging.error('Could not resolve sound search name: %s for %s', sound_search_name,
                          self.dirname)
            raise Exception('Could not resolve sound search name.')
        if len(names) > 1:
            logging.error('Found %s files for sound search name %s \n %s', len(names),
                          sound_search_name, names)

        self.dirconfig.setdefault('default', {})
        self.dirconfig['default'].update(self.config['default_sound_config'])

        return {'filename': names[0], 'is_voice': True, **self.dirconfig['default']}


class Sound():
    def __init__(self, params_dict):
        self.fade_in = 1
        self.fade_out = 1
        self.volume_transformation = 0
        self.start = 0
        self.stop = -1
        self._raw_file = None
        self._file = None
        self._clean_file = None  # file handler for file which has been cleaned
        self.cleaning_performed = False  # becomes True in cleaning operation (for all Sounds)
        # self.after_cleaning_fade_in = 1
        self.before_cleaning_fade = 500
        self._is_voice = False
        self.clean = False # should file be cleaned

        if 'filename' not in params_dict:
            log.error('There was no "filename" key in %s', params_dict)

        for key, value in params_dict.items():
            setattr(self, key, value)

    @property
    def raw_file(self):
        return self._raw_file

    @raw_file.setter
    def raw_file(self, file):
        self._raw_file = validate_file(file, file_description='{} (raw_file)'.format(self.filename))

    @property
    def file(self):
        """ Returns _file or clean_file if it exists. """
        if self.clean_file:
            return self.clean_file
        elif self.clean and self.cleaning_performed:
            logging.warn('For "%s" there was no cleaned file, while there should be!!', getattr(self, 'filename', self))

        return self._file

    @file.setter
    def file(self, file):
        self._file = validate_file(file, file_description='{} (file)'.format(self.filename))

    @property
    def clean_file(self):
        return self._clean_file

    @clean_file.setter
    def clean_file(self, file):
        self._clean_file = validate_file(file, file_description='{} (clean_file)'.format(self.filename))

    @property
    def is_voice(self):
        return self._is_voice

    @is_voice.setter
    def is_voice(self, is_voice):
        self._is_voice = is_voice

    @property
    def slice(self):
        return slice(int(self.start), int(self.stop))

    def __repr__(self):
        return super().__repr__().replace('>', ' ' + str(self.__dict__) + '>')

    def export(self, *args):
        return self.file.export(*args)

    def __getitem__(self, index):
        return self.file[index]

    def update(self, config_dict):
        for key, value in config_dict.items():
            setattr(self, key, value)

    def read_file(self):
        logging.debug('Reading file %s', self.filename)
        self.raw_file = AudioSegment.from_file(self.filename, self.filename.split('.')[-1])
        logging.debug('Slicing: %s and volume trans: %s', str(self.slice), self.volume_transformation)
        self.file = self.raw_file[self.slice] + float(self.volume_transformation)

        return self

def validate_file(file, file_description=None):
    if not file:
        caller = getframeinfo(stack()[2][0])
        mes = '"{}"'.format(file_description) if file_description else file
        logging.error("File %s is wrong! Detected at: %s:%d", mes, caller.filename, caller.lineno)
    return file

if __name__ == '__main__':
    PB = PodcastBuilder()
    if '--skip' not in sys.argv:
        PB.perform()

    if '-i' in sys.argv:
        # pylint: disable=locally-disabled, unused-import, ungrouped-imports
        from pydub.playback import play
        from src.plot_utils import *
        from src.verification_utils import *
        code.interact(local=dict(globals(), **dict(b=PB, p=next(iter(PB.podcasts), None), **locals())))
