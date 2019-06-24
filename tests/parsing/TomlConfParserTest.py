import logging
import os
import tempfile
import unittest
from collections import OrderedDict

from coalib.parsing.ConfParser import ConfParser
from coalib.parsing.TomlConfParser import TomlConfParser
from coalib.settings.Section import Section


class TomlConfParserTest(unittest.TestCase):
    example_file = """setting = 'without_section'
comment0 = 'Hello'
# hello
[all]
# Hello World
max_line_length = 80 #cadc
ignore = './vendor'
a = true #ccas

[EMPTY_ELEM_STRIP]
    A = ['a', 'b', 'c']
    B = ['a', '  ', '  ', 'd']
    C = ['','',
    '','']

[foo]
files = '**'
aspects = ['aspectname1', 'AspectName2']
aspectname1.aspect_taste = 80
aspectname1.subaspect_taste = ['word1', 'word2', 'word3']
aspectname1.subaspect_taste1 = 'word5'

[foo2]
inherits = ['foo']
aspects = 'aspectname3'
aspectname1.subaspect_taste1 = ['dog', 'cat']
appends = 'aspectname1.subaspect_taste1'


[sample]
    # coala
    [sample.item]
    # Hello World
    b = [ '1', #Hello
          '2'
        ]

    a = 10

[a]
p = '10'
q = '20'

[b]
c = '5'
d  = '6'

[c]
inherits = [ 'a', 'b' ]
p  = 'a'
d  = 'b'
appends.a = 'p'
appends.b = 'd'
"""

    def setUp(self):
        self.tempdir = tempfile.gettempdir()
        self.file = os.path.join(self.tempdir, '.coafile.toml')
        self.nonexistentfile = os.path.join(self.tempdir, 'w31efr3rk')
        with open(self.file, 'w') as file:
            file.write(self.example_file)

        self.uut = TomlConfParser()

        try:
            os.remove(self.nonexistentfile)
        except FileNotFoundError:
            pass

        logger = logging.getLogger()

        with self.assertLogs(logger, 'WARNING') as self.cm:
            self.sections = self.uut.parse(self.file)

    def tearDown(self):
        os.remove(self.file)

    def test_parse_nonexisting_file(self):
        self.assertRaises(FileNotFoundError,
                          self.uut.parse,
                          self.nonexistentfile)

    def test_parse_nonexistent_section(self):
        self.assertRaises(IndexError,
                          self.uut.get_section,
                          'non-existent-section'
                          )
        self.assertNotEqual(self.uut.parse(self.file, True), self.sections)

    def test_format_value(self):
        self.assertEqual(self.uut.format_value(80), '80')
        self.assertEqual(self.uut.format_value(True), 'True')
        self.assertEqual(self.uut.format_value([1, 2, 3]), '1, 2, 3')

    def test_parse_default_section_deprecated(self):
        default_should = OrderedDict([
            ('setting', 'without_section'),
            ('comment0', 'Hello'),
            ('(comment0)', '# hello')
        ])

        key, val = self.sections.popitem(last=False)
        self.assertTrue(isinstance(val, Section))
        self.assertEqual(key, 'default')

        is_dict = OrderedDict()
        for k in val:
            is_dict[k] = str(val[k])
        self.assertEqual(is_dict, default_should)

        self.assertRegex(self.cm.output[0],
                         'A setting does not have a section.')

    def test_parse_all(self):
        all_should = OrderedDict([
            ('(comment1)', '# Hello World'),
            ('max_line_length', '80'),
            ('ignore', './vendor'),
            ('a', 'true'),
            ('(comment2)', '')
        ])

        # pop off default
        self.sections.popitem(last=False)

        key, val = self.sections.popitem(last=False)
        self.assertTrue(isinstance(val, Section))
        self.assertTrue(key, 'all')

        is_dict = OrderedDict()

        for k in val:
            is_dict[k] = str(val[k])
        self.assertEqual(is_dict, all_should)

    def test_parse_empty_elem_strip_section(self):
        empty_elem_strip_should = OrderedDict([
            ('a', 'a, b, c'),
            ('b', 'a,   ,   , d'),
            ('c', ', , ,'),
            ('(comment3)', '')
        ])

        # Pop off default and all section.
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)

        key, val = self.sections.popitem(last=False)
        self.assertTrue(isinstance(val, Section))
        self.assertEqual(key, 'empty_elem_strip')

        is_dict = OrderedDict()
        for k in val:
            is_dict[k] = str(val[k])
        self.assertEqual(is_dict, empty_elem_strip_should)

    def test_parse_aspects(self):
        aspects_should = OrderedDict([
            ('files', '**'),
            ('aspects', 'aspectname1, AspectName2'),
            ('aspectname1:aspect_taste', '80'),
            ('aspectname1:subaspect_taste', 'word1, word2, word3'),
            ('aspectname1:subaspect_taste1', 'word5'),
            ('(comment4)', '')
        ])

        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        key, val = self.sections.popitem(last=False)

        self.assertTrue(isinstance(val, Section))
        self.assertEqual(key, 'foo')

        is_dict = OrderedDict()
        for k in val:
            is_dict[k] = str(val[k])
        self.assertEqual(is_dict, aspects_should)

    def test_inherited(self):
        inherited_should = OrderedDict([
            ('inherits', 'foo'),
            ('aspects', 'aspectname3'),
            ('aspectname1:subaspect_taste1', 'dog, cat'),
            ('appends', 'aspectname1.subaspect_taste1'),
            ('(comment5)', '')])

        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        key, val = self.sections.popitem(last=False)

        self.assertTrue(isinstance(val, Section))
        self.assertEqual(key, 'foo.foo2')
        is_dict = OrderedDict()
        for k in val:
            is_dict[k] = str(val[k])
        self.assertEqual(is_dict, inherited_should)

    def test_remove_empty_iter_elements(self):

        # Test without stripping.
        uut = TomlConfParser(remove_empty_iter_elements=False)
        uut.parse(self.file)
        self.assertEqual(list(uut.get_section('EMPTY_ELEM_STRIP')['A']),
                         ['a', 'b', 'c'])
        self.assertEqual(list(uut.get_section('EMPTY_ELEM_STRIP')['B']),
                         ['a', '', '', 'd'])
        self.assertEqual(list(uut.get_section('EMPTY_ELEM_STRIP')['C']),
                         ['', '', '', ''])

        # Test with empty-elem stripping.
        uut = TomlConfParser(remove_empty_iter_elements=True)
        uut.parse(self.file)
        self.assertEqual(list(uut.get_section('EMPTY_ELEM_STRIP')['A']),
                         ['a', 'b', 'c'])
        self.assertEqual(list(uut.get_section('EMPTY_ELEM_STRIP')['B']),
                         ['a', 'd'])
        self.assertEqual(list(uut.get_section('EMPTY_ELEM_STRIP')['C']),
                         [])

    def test_nested_inheritance(self):
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)

        inherit_should = OrderedDict([
            ('inherits', 'a, b'),
            ('p', 'a'),
            ('d', 'b'),
            ('appends:a', 'p'),
            ('appends:b', 'd')])

        # Test a.c
        key, val = self.sections.popitem(last=False)
        self.assertTrue(isinstance(val, Section))
        self.assertEqual(key, 'a.c')
        is_dict = OrderedDict()
        for k in val:
            is_dict[k] = str(val[k])
        self.assertTrue(val.contents.get('p').to_append)
        self.assertFalse(val.contents.get('d').to_append)
        self.assertEqual(is_dict, inherit_should)

        # Test b.c
        key, val = self.sections.popitem(last=False)
        self.assertTrue(isinstance(val, Section))
        self.assertEqual(key, 'b.c')
        is_dict = OrderedDict()
        for k in val:
            is_dict[k] = str(val[k])
        self.assertTrue(val.contents.get('d').to_append)
        self.assertFalse(val.contents.get('p').to_append)
        self.assertEqual(is_dict, inherit_should)

    def test_config_directory(self):
        self.uut.parse(self.tempdir)

    def test_consistency(self):

        coafile_str = '''
        [foo]
        files = **
        aspects = aspectname1, AspectName2
        aspectname1:aspect_taste = 80
        aspectname1:subaspect_taste = word1, word2, word3
        aspectname1:subaspect_taste1 = word5
        '''

        # Test that the sections generated in toml and coafile format
        # is same

        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        self.sections.popitem(last=False)
        toml_dict = OrderedDict()
        key_toml, val_toml = self.sections.popitem(last=False)
        for k in val_toml:
            toml_dict[k] = str(val_toml[k])
        toml_dict.popitem()

        self.coafile = os.path.join(self.tempdir, '.coafile')
        with open(self.coafile, 'w') as file:
            file.write(coafile_str)
        sections_ini = ConfParser().parse(self.coafile)
        os.remove(self.coafile)

        sections_ini.popitem(last=False)
        key_ini, val_ini = sections_ini.popitem(last=False)
        ini_dict = OrderedDict()

        for k in val_ini:
            ini_dict[k] = str(val_ini[k])
        ini_dict.popitem()

        self.assertEqual(key_toml, key_ini)
        self.assertEqual(toml_dict, ini_dict)
