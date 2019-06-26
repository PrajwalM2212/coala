from coalib.parsing.TomlConfParser import TomlSetting
from tomlkit import document, table, dumps, array, string, key, integer, comment
from tomlkit.items import Array, String, Bool, Integer, Comment, Key, KeyType


class TomlConfWriter:
    def __init__(self, sections):
        self.sections = sections
        self.document = document()

    def write(self):
        for item in self.sections:
            section = self.sections[item]
            table_name = section.name
            table_contents = table()
            for _, setting in section.contents.items():

                if ':' in setting.key:
                    count = setting.key.count(':')
                    setting_key = Key(setting.key.replace(':', '.', count),
                                      t=KeyType.Bare,
                                      dotted=True)
                else:
                    setting_key = key(setting.key)

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
                elif isinstance(value, (str, bool, int)):
                    table_contents.add(setting_key, value)

            self.document.add(table_name, table_contents)

        print(dumps(self.document))

    def get_value_type(self, value):
        try:
            value = int(value)
        except ValueError:
            try:
                value = bool(value)
            except ValueError:
                pass
        return value
