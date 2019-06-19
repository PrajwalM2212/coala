import logging

import os

import tomlkit.container
import tomlkit.items
from coalib.misc import Constants
from tomlkit.items import Table, Item

from coalib.results.SourcePosition import SourcePosition
from coalib.settings.Section import Section
from coalib.settings.Setting import Setting
from collections import Iterable, OrderedDict


class TomlSetting(Setting):
    def __init__(self, key,
                 value,
                 original_value,
                 origin: (str, SourcePosition) = '',
                 strip_whitespaces: bool = True,
                 list_delimiters: Iterable = (',', ';'),
                 from_cli: bool = False,
                 remove_empty_iter_elements: bool = True,
                 to_append: bool = False,
                 ):
        self.original_value = original_value
        super(TomlSetting, self).__init__(
            key,
            value,
            origin,
            strip_whitespaces,
            list_delimiters,
            from_cli,
            remove_empty_iter_elements,
            to_append)


class TomlConfParser:

    def __init__(self, remove_empty_iter_elements=True):

        self.sections = None
        self.data = None
        self.__rand_helper = None
        self.__init_sections()
        self.__remove_empty_iter_elements = remove_empty_iter_elements

    def parse(self, input_data, overwrite=False):
        """
        Parses the input and adds the new data to the existing.

        :param input_data: The filename to parse from.
        :param overwrite:  If True, wipes all existing Settings inside this
                           instance and adds only the newly parsed ones. If
                           False, adds the newly parsed data to the existing
                           one (and overwrites already existing keys with the
                           newly parsed values).
        :return:           A dictionary with (lowercase) section names as keys
                           and their Setting objects as values.
        """

        if os.path.isdir(input_data):
            input_data = os.path.join(input_data, Constants.local_coafile_toml)

        if overwrite:
            self.__init_sections()

        with open(input_data, 'r') as file:
            self.data = tomlkit.parse(file.read())

        self.data = self.data.body

        for item in self.data:
            self.generate_section(item, input_data)

        return self.sections

    def get_section(self, name, create_if_not_exists=False):
        """
        Returns or creates a section with given name

        :param name: The name of the section
        :param create_if_not_exists: create a section if it does not exist
        :return: Section of given name
        """
        key = self.__refine_key(name)
        sec = self.sections.get(key, None)
        if sec is not None:
            return sec

        if not create_if_not_exists:
            raise IndexError

        retval = self.sections[key] = Section(str(name))
        return retval

    @staticmethod
    def __refine_key(key):
        return str(key).lower().strip()

    def generate_section(self, item, origin):
        """
        Generates section

        :param item: Configuration group
        :param origin: The file from which the configuration originated
        """

        section_name = item[0]
        section_content = item[1]
        appends = []

        # Handle Default section
        if not isinstance(section_content, Table):
            original_value = section_content
            current_section = self.get_section('default', True)
            logging.warning('A setting does not have a section.'
                            'This is a deprecated feature please '
                            'put this setting in a section defined'
                            ' with `[<your-section-name]` in a '
                            'configuration file.')

            if section_name is None:
                section_content = section_content.as_string()
                section_name = '(' + 'comment' + str(self.__rand_helper) + ')'
                self.__rand_helper += 1
            self.create_setting(current_section,
                                section_name,
                                section_content,
                                original_value,
                                origin,
                                False
                                )
            return

        # Get to be appended keys
        if 'appends' in section_content.keys():
            appends.append(section_content.get('appends'))

        if 'inherits' in section_content.keys():

            for parent in section_content.get('inherits'):
                s_name = parent + '.' + section_name.as_string()
                current_section = self.get_section(s_name, True)
                self.fill_table_settings(current_section, section_content,
                                         origin, appends)
        else:

            section_name = section_name.as_string()
            current_section = self.get_section(section_name, True)
            self.fill_table_settings(current_section, section_content,
                                     origin, appends)

    def fill_table_settings(self, current_section, section_content,
                            origin, appends):
        for content_key, content_value in section_content.value.body:

            original_value = content_value
            # Handle full-line comments
            if content_key is None:
                content_key = '(' + 'comment' + str(self.__rand_helper) + ')'
                self.__rand_helper += 1
                self.create_setting(current_section, content_key,
                                    content_value.as_string(),
                                    original_value,
                                    origin, False)
                continue
            else:
                content_key = content_key.as_string()
                # Handle Aspects
                if isinstance(content_value, Table):
                    self.generate_aspects(content_key, content_value,
                                          current_section, appends,
                                          origin)
                    continue

                to_append = False

                if not isinstance(content_value, str):
                    content_value = self.format_value(content_value)

                if content_key in appends:
                    to_append = True

                self.create_setting(current_section, content_key, content_value,
                                    original_value, origin, to_append)

    def __init_sections(self):
        self.sections = OrderedDict()
        self.sections['default'] = Section('Default')
        self.__rand_helper = 0

    def create_setting(self, current_section, key, value, original_value,
                       origin, to_append):
        current_section.add_or_create_setting(
            TomlSetting(key,
                        value,
                        original_value,
                        SourcePosition(
                            str(origin)),
                        to_append=to_append,
                        # Start ignoring PEP8Bear, PycodestyleBear*
                        # they fail to resolve this
                        remove_empty_iter_elements=
                        self.__remove_empty_iter_elements),
            # Stop ignoring
            allow_appending=(key == []))

    def generate_aspects(self, content_key, content_value,
                         current_section, appends, origin):
        """
        Generates aspects related settings

        :param origin: The origin of the settings
        :param appends: The list containing the settings to be appended
        :param content_key: Aspect group name
        :param content_value: Aspect group value
        :param current_section: The section the aspects belong to
        """

        base_key = content_key
        for k, v in content_value.value.body:
            original_value = v
            if k is None:
                com_key = '(' + 'comment' + str(self.__rand_helper) + ')'
                self.__rand_helper += 1
                self.create_setting(current_section, com_key, v.as_string(),
                                    original_value, origin, False)
            else:
                k = k.as_string()

                key = base_key + ':' + k

                # handle aspects
                if isinstance(v, Table):
                    self.generate_aspects(key, v, current_section, appends,
                                          origin)
                    continue

                if not isinstance(v, str):
                    v = self.format_value(v)

                to_append = False

                if base_key + '.' + k in appends:
                    to_append = True

                self.create_setting(current_section, key, v, original_value,
                                    origin, to_append)

    @staticmethod
    def format_value(value):
        if isinstance(value, list):
            value = [str(i) for i in value]
            return ', '.join(value)
        elif isinstance(value, Item):
            return value.as_string()
        else:
            return str(value)
