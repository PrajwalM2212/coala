from coalib.parsing.TomlConfParser import TomlSetting
from tomlkit import document, table, dumps, array, string, boolean, integer, comment
from tomlkit.items import Array, String, Bool, Integer, Comment


class TomlConfWriter:
    def __init__(self, sections):
        self.sections = sections
        self.document = document()

    def write(self):
        for item in self.sections:
            section = self.sections[item]
            table_name = section.name
            table_contents = table()
            for key, setting in section.contents.items():
                key = setting.key

                if isinstance(setting, TomlSetting):
                    value = setting.original_value
                else:
                    value = setting.value

                if isinstance(value, Array):
                    table_contents.add(key, array(value.as_string()))
                    table_contents[key].comment(value.trivia.comment)
                elif isinstance(value, String):
                    table_contents.add(key, string(value))
                    table_contents[key].comment(value.trivia.comment)
                elif isinstance(value, Bool):
                    table_contents.add(key, boolean(value.as_string()))
                    table_contents[key].comment(value.trivia.comment)
                elif isinstance(value, Integer):
                    table_contents.add(key, integer(value.as_string()))
                    table_contents[key].comment(value.trivia.comment)
                elif isinstance(value, Comment):
                    table_contents.add(comment(value.as_string()))
                elif isinstance(value, str):
                    table_contents.add(key, value)

            self.document.add(table_name, table_contents)

        print(dumps(self.document))
