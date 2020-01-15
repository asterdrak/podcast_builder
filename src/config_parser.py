""" This module is to parse config.yaml podcast structure definition. """

import logging
import yaml


class ConfigParser():
    """ Parses given file and privdes interface to get config values. """

    def __init__(self, config_filename):
        self.config_filename = config_filename
        self.config = {}

    def read(self):
        """ Reads config file and saves it in instance variable. """
        with open(self.config_filename, 'r') as stream:
            try:
                self.config = yaml.safe_load(stream)
                logging.debug('Config file %s has been read', self.config_filename)
            except yaml.YAMLError as exc:
                logging.error(exc)
        return self

    def dirs(self):
        """ Returns config for directories (list). """
        return self.config['dirs']

    def __getitem__(self, key):
        return self.config[key]

    def __contains__(self, key):
        return key in self.config

    def __repr__(self):
        return str(self.config)

    def get(self, key, default=None):
        return self.config.get(key, default)
