import re

from coalib.misc import Constants
from coalib.parsing.TomlConfParser import TomlSetting
from coalib.settings.Section import Section
from tomlkit import document, table, dumps, array, string, key, integer, comment
from tomlkit.items import Array, String, Bool, Integer, Comment, Key, KeyType


class TomlConfWriter:
    def __init__(self, sections):
        self.sections = sections
        self.document = document()

    def write(self):
        for item in self.sections:
            section = self.sections[item]
            table_name = self.get_table_name(section)
            if table_name in self.document:
                continue
            table_contents = table()
            for _, setting in section.contents.items():

                setting_key = self.get_setting_key(setting)

                if isinstance(setting, TomlSetting):
                    value = setting.original_value
                else:
                    value = self.get_value_type(setting.value)

                if isinstance(value, Array):
                    table_contents.add(setting_key, array(value.as_string()))
                    table_contents[setting_key].comment(value.trivia.comment)
                elif isinstance(value, String):
                    table_contents.add(setting_key, string(value))
                    table_contents[setting_key].comment(value.trivia.comment)
                elif isinstance(value, Bool):
                    table_contents.add(setting_key, value)
                elif isinstance(value, Integer):
                    table_contents.add(setting_key, integer(value.as_string()))
                    table_contents[setting_key].comment(value.trivia.comment)
                elif isinstance(value, Comment):
                    table_contents.add(comment(value.as_string()))
                elif isinstance(value, (str, bool, int, list)):
                    table_contents.add(setting_key, value)

            self.document.add(table_name, table_contents)

        with open('.coafile', 'w') as file:
            file.write(dumps(self.document))
        print(dumps(self.document))

    def get_value_type(self, value):

        if ',' in value:
            value_list = []
            mod = ''.join(re.split(r'\n', value))
            for v in re.split(r',', mod):
                value_list.append(v.strip())
            return value_list

        if (value.lower() == 'true') or (value.lower() == 'false'):
            return bool(value)

        if value.isdigit():
            return int(value)

        return value

    def get_setting_key(self, setting):
        if ':' in setting.key:
            count = setting.key.count(':')
            setting_key = Key(setting.key.replace(':', '.', count),
                              t=KeyType.Bare,
                              dotted=True)
        else:
            setting_key = key(setting.key)
        return setting_key

    def get_table_name(self, section: Section):
        name: str = section.name
        if name.startswith('"') or name.startswith("'"):
            return name
        elif '.' in name:
            if 'inherits' in section.contents:
                inherits = section.contents.get('inherits').original_value
                parent_pos = -1
                if isinstance(inherits, Array):
                    i = 0
                    while parent_pos == -1:
                        parent = inherits[i]
                        parent_pos = name.find(parent)
                        i += 1
                else:
                    parent = inherits
                    parent_pos = name.find(parent)
                name = name[parent_pos + len(parent) + 1:]
        return name
