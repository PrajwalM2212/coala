import re

from coala_utils.string_processing import unescape
from coalib.parsing.TomlConfParser import TomlSetting
from coalib.settings.Section import Section
from tomlkit import document, table, dumps, array, string, key, integer, comment
from tomlkit.items import Array, String, Bool, Integer, Comment, Key, KeyType, Trivia


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
                    value = self.get_original_value(setting.value)

                if isinstance(value, Array):
                    table_contents.add(setting_key, array(value.as_string()))
                    if value.trivia.comment:
                        table_contents[setting_key].comment(value.trivia.comment)
                elif isinstance(value, String):
                    table_contents.add(setting_key, string(value))
                    if value.trivia.comment:
                        table_contents[setting_key].comment(value.trivia.comment)
                elif isinstance(value, Bool):
                    table_contents.add(setting_key, value)
                elif isinstance(value, Integer):
                    table_contents.add(setting_key, integer(value.as_string()))
                    if value.trivia.comment:
                        table_contents[setting_key].comment(value.trivia.comment)
                elif isinstance(value, Comment):
                    table_contents.add(Comment(
                        Trivia(comment_ws="  ", comment=str(value))
                    ))
                elif isinstance(value, (str, bool, int, list)):
                    table_contents.add(setting_key, value)

            self.document.add(table_name, table_contents)

        print(dumps(self.document))

    def coafile_to_toml(self):
        comment_regex = re.compile(r'comment[\d]+')
        for item in self.sections:
            section = self.sections[item]
            table_name, inherits = self.get_section_name(section.name)
            appends = []
            table_contents = table()
            for k, setting in section.contents.items():
                setting_key = self.get_setting_key(setting)

                if comment_regex.search(setting_key.as_string()):
                    continue

                if setting.to_append:
                    appends.append(k)
                    value = section[k].value
                else:
                    value = self.get_original_value(setting.value)
                table_contents.add(setting_key, value)

            if not inherits == []:
                table_contents.add(key('inherits'), inherits)

            if not appends == []:
                table_contents.add(key('appends'), appends)

            self.document.add(table_name, table_contents)
        print(dumps(self.document))

    @staticmethod
    def get_section_name(section_name):
        dot_pos = section_name.rfind('.')

        inherits = []
        if dot_pos != -1:
            inherits = section_name[:dot_pos]

        return section_name[dot_pos + 1:], inherits

    @staticmethod
    def get_original_value(value):

        if ',' in value:
            v = [unescape(v) for v in value.split(',')]
            return [unescape(v, '\n').strip() for v in v]

        if (value.lower() == 'true') or (value.lower() == 'false'):
            return bool(value)

        if value.isdigit():
            return int(value)

        return unescape(value)

    @staticmethod
    def get_setting_key(setting):
        if ':' in setting.key:
            count = setting.key.count(':')
            setting_key = Key(setting.key.replace(':', '.', count),
                              t=KeyType.Bare,
                              dotted=True)
        else:
            setting_key = key(setting.key)
        return setting_key

    @staticmethod
    def get_table_name(section: Section):
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


if __name__ == '__main__':
    print(TomlConfWriter.get_section_name('all.python.java'))
