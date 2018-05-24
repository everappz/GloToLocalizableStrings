#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Update or create an Apple XCode project localization strings file.

TODO: handle localization domains
'''

from __future__ import with_statement

import sys
import os
import os.path
import re
import tempfile
import subprocess
import codecs
import unittest
import optparse
import shutil
import logging
import urllib
import urllib2
import json
from xml.etree import ElementTree

ENCODINGS = ['utf16', 'utf8']


class LocalizedString(object):
    ''' A localized string from a strings file '''
    COMMENT_EXPR = re.compile(
        # Line start
        '^\w*'
        # Comment
        '/\* (?P<comment>.+) \*/'
        # End of line
        '\w*$'
    )
    LOCALIZED_STRING_EXPR = re.compile(
        # Line start
        '^'
        # Key
        '"(?P<key>.+)"'
        # Equals
        ' ?= ?'
        # Value
        '"(?P<value>.+)"'
        # Whitespace
        ';'
        # Comment
        '(?: /\* (?P<comment>.+) \*/)?'
        # End of line
        '$'
    )

    @classmethod
    def parse_comment(cls, comment):
        '''
        Extract the content of a comment line from a strings file.
        Returns the comment string or None if the line doesn't match.
        '''
        result = cls.COMMENT_EXPR.match(comment)
        if result != None:
            return result.group('comment')
        else:
            return None

    @classmethod
    def from_line(cls, line):
        '''
        Extract the content of a string line from a strings file.
        Returns a LocalizedString instance or None if the line doesn't match.

        TODO: handle whitespace restore
        '''
        result = cls.LOCALIZED_STRING_EXPR.match(line)
        if result != None:
            return cls(
                result.group('key'),
                result.group('value'),
                result.group('comment')
            )
        else:
            return None

    def __init__(self, key, value=None, comment=None):
        super(LocalizedString, self).__init__()
        self.key = key
        self.value = value
        self.comment = comment

    def is_raw(self):
        '''
        Return True if the localized string has not been translated.
        '''
        return self.value == self.key

    def __str__(self):
        if self.comment:
            return '"%s" = "%s"; /* %s */' % (
                self.key or '', self.value or '', self.comment
            )
        else:
            return '"%s" = "%s";' % (self.key or '', self.value or '')

def strings_from_folder(folder_path, extensions=None):
    '''
    Recursively scan folder_path for files containing localizable strings.
    Run genstrings on these files and extract the strings.
    Returns a dictionnary of LocalizedString instances, indexed by key.
    '''
    localized_strings = {}
    if extensions == None:
        extensions = frozenset(['lg'])

    logging.debug('Scanning for language files in %s', folder_path)
    for dir_path, dir_names, file_names in os.walk(folder_path):
        for file_name in file_names:
            extension = file_name.rpartition('.')[2]
            if extension in extensions:
                code_file_path = os.path.join(dir_path, file_name)
                logging.debug('Found %s', code_file_path)
                localized_strings_from_lg_file = strings_from_lg_file(code_file_path)
                for localized_string in localized_strings_from_lg_file:
                    localized_strings[localized_string.key] = localized_string

    return localized_strings
    
def recur_node(node, localized_strings):
    """Applies function f on given node and goes down recursively to its 
       children.
        
       Keyword arguments:
       node - the root node
       localized_strings - array of result LocalizableStrings
        
    """
    if node != None:
        if node.tag=="TranslationSet":
            base = ""
            tran = ""
            
            for item in node.getchildren():
                
                if item.tag=="base":
                    base = item.text
                    
                if item.tag=="tran":
                    tran = item.text
                    
            if (base != "" and tran != "" and base != None and tran != None and base.find('\"') == -1 and base.find('\n') == -1 and tran.find('\"') == -1 and tran.find('\n') == -1):
                localized_string = LocalizedString(base,tran)
                localized_strings.append(localized_string)
                logging.debug('Added string %s', localized_string)
                        
        else:
            for item in node.getchildren():
                recur_node(item, localized_strings)
    else:
        return 0
        
        
def strings_from_file(file_path):
    '''
    Try to autodetect file encoding and call strings_from_encoded_file on the
    file at file_path.
    Returns a dictionnary of LocalizedString instances, indexed by key.
    Returns an empty dictionnary if the encoding is wrong.
    '''
    for current_encoding in ENCODINGS:
        try:
            return strings_from_encoded_file(file_path, current_encoding)
        except UnicodeError:
            pass

    logging.error(
        'Cannot determine encoding for file %s among %s',
        file_path,
        ', '.join(ENCODINGS)
    )

    return {}


def strings_from_encoded_file(file_path, encoding):
    '''
    Extract the strings from the file at file_path.
    Returns a dictionnary of LocalizedString instances, indexed by key.
    '''
    localized_strings = {}

    with codecs.open(file_path, 'r', encoding) as content:
        comment = None

        for line in content:
            line = line.strip()
            if not line:
                comment = None
                continue

            current_comment = LocalizedString.parse_comment(line)
            if current_comment:
                if current_comment != 'No comment provided by engineer.':
                    comment = current_comment
                continue

            localized_string = LocalizedString.from_line(line)
            if localized_string:
                if not localized_string.comment:
                    localized_string.comment = comment
                localized_strings[localized_string.key] = localized_string
            else:
                logging.error('Could not parse: %s', line.strip())

    return localized_strings




def strings_from_lg_file(file_path):
    '''
    Try to autodetect file encoding and call strings_from_encoded_file on the
    file at file_path.
    Returns a dictionnary of LocalizedString instances, indexed by key.
    Returns an empty dictionnary if the encoding is wrong.
    '''
    for current_encoding in ENCODINGS:
        try:
            return strings_from_encoded_lg_file(file_path, current_encoding)
        except UnicodeError:
            pass

    logging.error(
        'Cannot determine encoding for file %s among %s',
        file_path,
        ', '.join(ENCODINGS)
    )

    return {}


def strings_from_encoded_lg_file(file_path, encoding):
    '''
    Extract the strings from the file at file_path.
    Returns an array of LocalizedString instances.
    '''
    localized_strings = []
    try:
        root = ElementTree.parse(file_path).getroot()
    except:
        logging.debug('Error parsing %s', file_path)
                  
    recur_node(root, localized_strings)

    return localized_strings

def strings_to_file(localized_strings,escape_strings,file_path, encoding='utf16'):
    '''
    Write a strings file at file_path containing string in
    the localized_strings dictionnary.
    The strings are alphabetically sorted.
    '''
    trans_keys = set()
    not_keys = set()
    extra_keys = set()
    escape_keys = set()
    
    for escape_string in sorted_strings_from_dict(escape_strings):
        escape_key = escape_string.key
        escape_keys.add(escape_key)

    with codecs.open(file_path, 'w', encoding) as output:
        for localized_string in sorted_strings_from_dict(localized_strings):
            key = localized_string.key
            comment = localized_string.comment
            comment_str = str(comment)
            
            if localized_string.is_raw():
                if key in escape_keys:
                    if comment_str.find('extra')>=0:
                        extra_keys.add(key)
                    else:
                        trans_keys.add(key)
                else:
                    not_keys.add(key)
            else:
                if comment_str.find('extra')>=0:
                    extra_keys.add(key)
                else:      
                    trans_keys.add(key)

        for localized_string in sorted_strings_from_dict(localized_strings):
            key = localized_string.key
            if key in trans_keys:
                localized_string.comment = None
                output.write('%s\n\n' % localized_string)
                
                
        if len(extra_keys) != 0:
            output.write('\n')
            output.write('/*Extra*/')
            output.write('\n')
            output.write('\n')
            output.write('\n')
            for localized_string in sorted_strings_from_dict(localized_strings):
                key = localized_string.key
                if key in extra_keys:
                    output.write('%s\n\n' % localized_string)

        if len(not_keys) != 0:
            output.write('\n')
            output.write('/*Not Translated*/')
            output.write('\n')
            output.write('\n')
            output.write('\n')
            for localized_string in sorted_strings_from_dict(localized_strings):
                key = localized_string.key
                if key in not_keys:
                    localized_string.comment = None
                    output.write('%s\n\n' % localized_string)



def update_file_with_strings(file_path, localized_strings):
    '''
    Try to autodetect file encoding and call update_encoded_file_with_strings
    on the file at file_path.
    The file at file_path must exist or this function will raise an exception.
    '''
    for current_encoding in ENCODINGS:
        try:
            return update_encoded_file_with_strings(
                file_path,
                localized_strings,
                current_encoding
            )
        except UnicodeError:
            pass

    logging.error(
        'Cannot determine encoding for file %s among %s',
        file_path,
        ', '.join(ENCODINGS)
    )

    return {}


def update_encoded_file_with_strings(
    file_path,
    localized_strings,
    encoding='utf16'
):
    '''
    Update file at file_path with translations from localized_strings, trying
    to preserve the initial formatting by only removing the old translations,
    updating the current ones and adding the new translations at the end of
    the file.
    The file at file_path must exist or this function will raise an exception.
    '''
    output_strings = []

    keys = set()
    with codecs.open(file_path, 'r', encoding) as content:
        for line in content:
            current_string = LocalizedString.from_line(line.strip())
            if current_string:
                key = current_string.key
                localized_string = localized_strings.get(key, None)
                if localized_string:
                    keys.add(key)
                    output_strings.append(unicode(localized_string))
            else:
                output_strings.append(line[:-1])

    new_strings = []
    for value in localized_strings.itervalues():
        if value.key not in keys:
            new_strings.append(unicode(value))

    if len(new_strings) != 0:
        output_strings.append('')
        output_strings.append('/* New strings */')
        new_strings.sort()
        output_strings.extend(new_strings)

    with codecs.open(file_path, 'w', encoding) as output:
        output.write('\n'.join(output_strings))
        # Always add a new line at the end of the file
        output.write('\n')


def match_strings(scanned_strings, reference_strings):
    '''
    Complete scanned_strings with translations from reference_strings.
    Return the completed scanned_strings dictionnary.
    scanned_strings is not affected.
    Strings in reference_strings and not in scanned_strings are not copied.
    '''
    final_strings = {}

    for key, value in scanned_strings.iteritems():
        reference_value = reference_strings.get(key, None)
        if reference_value:
            if reference_value.is_raw():
                # Mark non-translated strings
                logging.debug('[raw]     %s', key)
                final_strings[key] = value
            else:
                # Reference comment comes from the code
                reference_value.comment = value.comment
                final_strings[key] = reference_value
        else:
            logging.debug('[new]     %s', key)
            final_strings[key] = value

    final_keys = set(final_strings.keys())
    for key in reference_strings.iterkeys():
        if key not in final_keys:
            logging.debug('[deleted] %s', key)

    return final_strings


def merge_dictionaries(reference_dict, import_dict):
    '''
    Return a dictionnary containing key/values from reference_dict
    and import_dict.
    In case of conflict, the value from reference_dict is chosen.
    '''
    final_dict = reference_dict.copy()

    reference_dict_keys = set(reference_dict.keys())
    for key, value in import_dict.iteritems():
        if key not in reference_dict_keys:
            final_dict[key] = value

    return final_dict


def sorted_strings_from_dict(strings):
    '''
    Return an array containing the string objects sorted alphabetically.
    '''
    keys = strings.keys()
    keys.sort()

    values = []
    for key in keys:
        values.append(strings[key])

    return values


class Tests(unittest.TestCase):
    ''' Unit Tests '''

    def test_comment(self):
        ''' Test comment pattern '''
        result = LocalizedString.COMMENT_EXPR.match('/* Testing Comments */')
        self.assertNotEqual(result, None, 'Pattern not recognized')
        self.assertEqual(result.group('comment'), 'Testing Comments',
            'Incorrect pattern content: [%s]' % result.group('comment')
        )

    def test_localized_string(self):
        ''' Test localized string pattern '''
        result = LocalizedString.LOCALIZED_STRING_EXPR.match(
            '"KEY" = "VALUE";'
        )
        self.assertNotEqual(result, None, 'Pattern not recognized')
        self.assertEqual(result.group('key'), 'KEY',
            'Incorrect comment content: [%s]' % result.group('key')
        )
        self.assertEqual(result.group('value'), 'VALUE',
            'Incorrect comment content: [%s]' % result.group('value')
        )
        self.assertEqual(result.group('comment'), None,
            'Incorrect comment content: [%s]' % result.group('comment')
        )

    def test_localized_comment_string(self):
        ''' Test localized string with comment pattern '''
        result = LocalizedString.LOCALIZED_STRING_EXPR.match(
            '"KEY" = "VALUE"; /* COMMENT */'
        )
        self.assertNotEqual(result, None, 'Pattern not recognized')
        self.assertEqual(result.group('key'), 'KEY',
            'Incorrect comment content: [%s]' % result.group('key')
        )
        self.assertEqual(result.group('value'), 'VALUE',
            'Incorrect comment content: [%s]' % result.group('value')
        )
        self.assertEqual(result.group('comment'), 'COMMENT',
            'Incorrect comment content: [%s]' % result.group('comment')
        )


def main():
    ''' Parse the command line and do what it is telled to do '''
    parser = optparse.OptionParser(
        'usage: %prog [strings_file] [source folders]'
    )

    (options, args) = parser.parse_args()

    logging.basicConfig(
        format='%(message)s',
        level=logging.DEBUG or logging.INFO
    )

    if len(args) < 2:
        parser.error('Please specify strings_file and input folders')

    strings_file = args[0]
    input_folders = args[1:]

    scanned_strings = {}
    escape_strings = {}

    for input_folder in input_folders:
        if not os.path.isdir(input_folder):
            logging.error('Input path is not a folder: %s', input_folder)
            return 1

        scanned_strings = merge_dictionaries(
            scanned_strings,
            strings_from_folder(input_folder)
        )

        try:
            strings_to_file(scanned_strings,escape_strings, strings_file)
        except IOError, exc:
            logging.error('Error writing to file %s: %s', strings_file, exc)
            return 1

        logging.info(
            'Strings were generated in %s',
            strings_file
        )

    return 0


if __name__ == '__main__':
    sys.exit(main())
