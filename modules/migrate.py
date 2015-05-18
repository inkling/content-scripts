#!/usr/bin/env python
#
# migrate.py
# content-scripts
#
# For details and documentation:
# http://github.com/inkling/content-scripts
#
# Copyright 2015 Inkling Systems, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A script to migrate from old style widgets & patterns to modular widgets and
patterns.

This script will check out the entire trunk of a project repo. It must do this
to ensure it correctly fixes all relative paths referenced from a widget. This
can be slow! If the repo is already checked out you can substitute the path
to the repo for the repo shortname and the existing svn repository will be
re-used and the environment will be ignored.

This script uses a series of very targetted, programatically generated regular
expressions to do the actual content migration. As a result the diff is very
specific to the changes that are required and easy to review. If the content
was parsed and re-rendered to HTML almost every line would change to do some
formatting difference between python's libraries and Habitat's stack. While
extensively tested, bugs happen, especially in complex regular expressions.

REVIEW ALL PROJECTS MIGRATED BY THIS SCRIPT FOR CORRECTNESS!

Configuration files must be a CSV in the form of:

repo_shortname,environment,widget_directory_name,module_directory_name

where the widget directory name is relative to /assets/widgets and the module
directory name is relative to /assets/modules, e.g.,

sn_test_project,stable,flashcard,inkling.flashcard

Example command lines:
    migrate.py -c migrate.csv
    migrate.py -c migrate.csv -s
"""

import argparse
import codecs
import csv
import glob
import json
import logging
import os
import re
import subprocess

from bs4 import BeautifulSoup

from s9logging import s9logging
import svn.project_svn as svn

parser = argparse.ArgumentParser(description='Migrate content from a widget to '
    'modularized form of the same widget in a given project.')
parser.add_argument('-c', '--config', required=True, help='CSV file specifying '
    'widgets migrating to modules in each project, each row in the form "'
    'repo_shortname,environment,widget_directory_name,module_directory_name"')
parser.add_argument('-s', '--skip-commit', action='store_true', default=False,
    help='Whether to skip svn commit of project changes')

s9logging.configureLogging()
log = logging.getLogger(__name__)

def _getSpecsFromCsv():
    """Returns a list of tuples of the form (source name, source environment,
    widget directory name, module directory name) taken from the CSV
    configuration file.
    """
    results = []
    with codecs.open(args.config, 'rb', encoding='utf8') as f:
        reader = csv.reader(f)
        try:
            for row in reader:
                # Strip any whitespace in row contents.
                row = [column.strip() for column in row]
                if len(row) < 4 or not all(row):
                    log.warning('CSV has invalid number of arguments at '
                        'line %s, skipping line.\n', reader.line_num)
                else:
                    results.append((row[0], row[1], row[2], row[3]))
        except csv.Error as e:
            log.error('Unable to parse CSV at line %s, skipping rest of'
                ' file.\n', reader.line_num)

    return results


def _getAllHTMLFiles(rootDir):
    """Returns a list of all HTML files under the root directory.

    Args:
        rootDir - String absolute path of the directory tree to search.
    """
    htmlFiles = []
    for root, dirs, files in os.walk(rootDir):
        for filename in [f for f in files if f.endswith('.html')]:
            htmlFiles.append(os.path.join(root, filename))
    return htmlFiles

def _updateHTMLFile(filePath, widgetAbsolutePath, modularWidgetAbsolutePath):
    """Updates file and linked widget JSON config files.

    Updates the specified HTML file changing all references to the
    non-modular widget to instead reference the modular widget, and all paths
    relative to the non-modular widget to be relative to the modular widget.
    Also fixes any JSON configuration files references from a widget's <object>
    tag.

    Args:
        filePath - String absolute path to the file to update.
        widgetAbsolutePath - String absolute path to the non-modular widget.
        modularWidgetAbsolutePath - String absolute path to the modular widget.
    """
    log.debug('Reading HTML file: %s', filePath)
    with codecs.open(filePath, 'rb', encoding='utf8') as htmlFile:
        htmlContent = ''.join(htmlFile.readlines())

    soup = BeautifulSoup(htmlContent)

    # Non-modular Widget view page path relative to the content. This path
    # will be the data attribute of any widget object tags.
    widgetViewRelativePath = os.path.join(
        os.path.relpath(widgetAbsolutePath, os.path.dirname(filePath)),
        'index.html')

    # Absolute path to the modular version of the widget view page.
    absModuleViewPath = os.path.join(
        modularWidgetAbsolutePath, 'index.html')
    # Widget view page path relative to the content.
    relativeModuleViewPath = os.path.relpath(
        absModuleViewPath, os.path.dirname(filePath))

    # Convert all object data (iframe src) links to new modular location.
    # This migrates all the widgets to point to their modular versions, but
    # leaves all parameters and JSON config files incorrectly relative to
    # the wrong location.
    toReplace = r'(<object\s.*?data=")' + widgetViewRelativePath +'"'
    replacement = r'\g<1>' + relativeModuleViewPath + '"'
    htmlContent = re.sub(toReplace,
                         replacement,
                         htmlContent,
                         flags=re.IGNORECASE)

    # For all object tags, clean up params and including config file. Use
    # the old relative path because BeautifulSoup parse tree was created
    # before the regex replace above and doesn't know about it.
    for object in soup.find_all('object',
            attrs={'data': widgetViewRelativePath}):
        # Find all param tags for that widget
        for param in object.find_all('param'):
            # Param value could be anything, but it might be a relative
            # path. Treat it as such creating an absolute path and see if it
            # exists. If it does, assume it is a relative path to something
            # in the project and update it to be relative to the new modular
            # widget location.
            val = param.get('value')

            # Don't replace empty string "" with path relative to widget.
            if not val:
                continue

            path = os.path.normpath(os.path.join(widgetAbsolutePath, val))

            # NOTE(andy): For this test to work we have to check out the
            # whole book. Sad times. But now we do.
            if os.path.exists(path):
                newPath = os.path.relpath(path, modularWidgetAbsolutePath)

                # Target specifically the parameter with a relative path
                # inside the <object> tag we are migrating. If we didn't
                # include the <object> tag we could accidentally change
                # a relative path for a widget that wasn't migrating that
                # referenced the same asset / content.
                toReplace = (r'(<object.*?data="' + relativeModuleViewPath +
                    '".*?<param.*?value=")' + val + '(".*?)(?=</object>)')
                replacement = r'\g<1>' + newPath + r'\g<2>'
                htmlContent = re.sub(toReplace,
                                     replacement,
                                     htmlContent,
                                     flags=re.IGNORECASE|re.DOTALL)

                # If the param is for the widget config file, also clean up
                # that config file.
                if param.get('name') == 'configFile':
                    _updateConfigFile(path, widgetAbsolutePath,
                                      modularWidgetAbsolutePath)

    # Write out all the changes.
    log.info('Writing updated HTML file: %s', filePath)
    with codecs.open(filePath, 'wb', encoding='utf8') as htmlFile:
        htmlFile.write(htmlContent)

def _updateConfigFile(filePath, widgetPath, modularWidgetPath):
    """Updates all values nested in the JSON object that are paths relative to
    the widgetPath to instead be relative to modularWidgetPath.

        Args:
            filePath - String absolute path to the JSON config file.
            widgetPath - String absolute path to the non-modular widget.
            modularWidthPath - String absolute path to the modular widget.
    """
    log.debug('Reading JSON config file: %s', filePath)
    with codecs.open(filePath, 'rb', encoding='utf8') as configFile:
        jsonContent = ''.join(configFile.readlines())

    data = json.loads(jsonContent)

    # Create a map of all Strings in the JSON that need migration. The key is
    # the non-modular relative path and the value is the modular relative path.
    if isinstance(data, dict):
        replacementMap = _getStringReplacementsInDict(data, widgetPath,
                modularWidgetPath)
    if isinstance(data, list):
        replacementMap = _getStringReplacementsInList(data,
                widgetPath, modularWidgetPath)

    # For each entry in the map, replace.
    for key, value in replacementMap.iteritems():
            # Negative lookbehind for a '\' ensures we are only matching
            # complete JSON strings and not quoted entities inside strings. For
            # example if the relative path was '../foo' we would match
            # {"bar": "../foo"} but we would not match
            # {"baz": "confusing value \"../foo"} or
            # {"baz": "confusing value \"../foo\""}
            # JSON Strings must be double quoted.
            jsonContent = re.sub(r'(?<!\\)"' + key + '"',
                                 '"' + value + '"',
                                 jsonContent)

    log.info('Writing updated JSON config file: %s', filePath)
    with codecs.open(filePath, 'wb', encoding='utf8') as configFile:
        configFile.write(jsonContent)

def _getStringReplacementsInDict(data, widgetPath, modularWidgetPath):
    """Returns a map of all string relative paths in dictionary that need
    updating.

    Args:
        data - The dictionary to search
        widgetPath - The absolute path to the non-modular widget.
        modularWidgetPath - The absolute path to the modular widget.
    """
    replacementMap = {}
    for key, value in data.iteritems():
        if isinstance(value, basestring):
            newValue = _getUpdatedString(value, widgetPath, modularWidgetPath)
            if newValue != value:
                replacementMap[value] = newValue
        elif isinstance(value, dict):
            replacementMap.update(_getStringReplacementsInDict(value,
                widgetPath, modularWidgetPath))
        elif isinstance(value, list):
            replacementMap.update(_getStringReplacementsInList(value,
                widgetPath, modularWidgetPath))
    return replacementMap

def _getStringReplacementsInList(data, widgetPath, modularWidgetPath):
    """Returns a map of all string relative paths in list that need updating.

    Args:
        data - The list to search
        widgetPath - The absolute path to the non-modular widget.
        modularWidgetPath - The absolute path to the modular widget.
    """
    replacementMap = {}
    for item in data:
        if isinstance(item, basestring):
            newValue = _getUpdatedString(item, widgetPath, modularWidgetPath)
            if newValue != item:
                replacementMap[item] = newValue
        elif isinstance(item, dict):
            replacementMap.update(_getStringReplacementsInDict(item,
                widgetPath, modularWidgetPath))
        elif isinstance(item, list):
            replacementMap.update(_getStringReplacementsInList(item,
                widgetPath, modularWidgetPath))
    return replacementMap

def _getUpdatedString(value, widgetPath, modularWidgetPath):
    """Returns updated version of the string.

    If the string is not a valid relative path from widgetPath returns the
    string. If it is a valid relative path from widgetPath returns the same
    path instead relative to modularWidgetPath.

    Args:
        value - The string to check.
        widgetPath - The absolute path to the non-modular widget.
        modularWidgetPath - The absolute path to the modular widget.
    """
    if not value:
        return value

    absPath = os.path.normpath(os.path.join(widgetPath, value))
    if os.path.exists(absPath):
        newPath = os.path.relpath(absPath, modularWidgetPath)
        return newPath
    return value

def _deleteNonModularWidgetPatterns(repoPath, widgetDir):
    """Deletes all patterns referencing the specified widget.

    Args:
        repoPath - String absolute path to the root of the project SVN repo.
        widgetDir - String name of the widget directory (not path).
    """
    patternFilePath = os.path.join(repoPath, 's9ml', '.templates',
        'pattern-snippets.html.tpls')
    if os.path.exists(patternFilePath):
        log.debug('Reading pattern snippet file: %s', patternFilePath)
        with codecs.open(patternFilePath, 'rb', encoding='utf8') as patternFile:
            patternContent = ''.join(patternFile.readlines())

        soup = BeautifulSoup(patternContent)

        # All patterns written assuming the content is in
        # /s9ml/chapter/file.html
        widgetViewRelativePath = os.path.join('..', '..', 'assets', 'widgets',
            widgetDir, 'index.html')

        # For each pattern, figure out if the pattern references the
        # non-modular widget. If it does we want to delete it.
        for script in  soup.find_all('script'):
            # BeautifulSoup stops processing the file at the <script> tag
            # because its contents might not be HTML. We must separately
            # parse its content to find the object tags it contains that
            # reference the widget.
            innerSoup = BeautifulSoup(script.text)
            widget = innerSoup.find('object',
                attrs={'data': widgetViewRelativePath})
            if widget is not None:
                # Script tag's contents are exactly referenced by its text
                # attribute. We can escape that for a regex that perfectly
                # matches the pattern contents and just find the surrounding
                # script tags and preceeding comment that names the pattern.
                toRemove = (r'\n*<!--.*?-->(?:\s)*<script.*\n?' +
                    re.escape(script.text) + r'(?:\s*)</script>')
                patternContent = re.sub(
                    toRemove,
                    '',
                    patternContent)

        log.info('Writing updated pattern snippets file: %s', patternFilePath)
        with codecs.open(patternFilePath, 'wb', encoding='utf8') as patternFile:
            patternFile.write(patternContent)
    else:
        log.warning('No pattern file at "%s", not deleting patterns.',
            patternFilePath)


if __name__ == '__main__':
    args = parser.parse_args()

    # For each line of the CSV, after migrating the specified widget we commit
    # the SVN repo. We skip the commit if there are errors during the migration.
    # However, if another line of the CSV moves a different widget in the same
    # project without errors we don't want to then commit both the successful
    # and unsuccessful migrations. Track the repos with errors to prevent this.
    # Some errors (unable to find widget or module) don't need to block commit.
    # Dict value indicates if commit blocking error has happened.
    reposWithErrors = {}

    repoSpecs = _getSpecsFromCsv()
    for name, environment, widgetDir, moduleDir in repoSpecs:
        try:
            repo = svn.ensureRepo(name, svn.MODULE_MIGRATION_UPDATE_SPECS,
                environment=environment)
        except svn.SvnError as e:
            log.error(e.message + '\n')
            # Haven't done any migration, don't worry about skipping future
            # commits.
            reposWithErrors[name + '-' + environment] = False
            continue

        logging.info('Migrating from widget %s to module %s in %s-%s',
                     widgetDir, moduleDir, name, environment)

        widgetAbsolutePath = os.path.join(repo['path'], 'assets', 'widgets',
            widgetDir)
        modularWidgetAbsolutePath = os.path.join(repo['path'], 'assets',
            'modules', moduleDir, 'widgets', widgetDir)

        if not os.path.isdir(widgetAbsolutePath):
            log.error('Unable to find non-modular widget at: %s, unable to '
                'continue migration.\n',
                widgetAbsolutePath)
            # Haven't done any migration, don't worry about skipping future
            # commits.
            reposWithErrors[repo['path']] = False
            continue

        if not os.path.isdir(modularWidgetAbsolutePath):
            log.error('Unable to find modular widget at: %s, unable to '
                'continue migration.\n',
                modularWidgetAbsolutePath)
            # Haven't done any migration, don't worry about skipping future
            # commits.
            reposWithErrors[repo['path']] = False
            continue

        # Find all html files that might have a widget to migrate.
        htmlFiles = _getAllHTMLFiles(os.path.join(repo['path'], 's9ml'))

        # For each html file, fix file contents and linked widget JSON config
        # files.
        try:
            for filename in htmlFiles:
                    _updateHTMLFile(filename, widgetAbsolutePath,
                                    modularWidgetAbsolutePath)
        except (IOError, ValueError) as e:
            log.error(str(e))
            log.error('Unable to update project content files, skipping rest '
                      'of migration of %s to %s\n', widgetDir, moduleDir)
            reposWithErrors[repo['path']] = True
            continue

        # Delete patterns that reference the non-modular widget. Assuming that
        # the modular widget includes the relevant patterns.
        try:
            _deleteNonModularWidgetPatterns(repo['path'], widgetDir)
        except (IOError, ValueError) as e:
            log.error(e.strerror)
            log.error('Unable to update project pattern snippet file, skipping '
                      'rest of migration of %s to %s\n', widgetDir, moduleDir)
            reposWithErrors[repo['path']] = True
            continue

        # Delete non-modular widget.
        try:
            svn.delete(widgetAbsolutePath)
        except svn.SvnError as e:
            log.error(e.message)
            log.error('Unable to delete non-modular widget, skipping rest of '
                      'migration of %s to %s\n', widgetDir, moduleDir)
            reposWithErrors[repo['path']] = True
            continue

        # SVN update & commit
        if reposWithErrors.get(repo['path'], False):
            log.warning('A previous migration in this script run modifying '
                'the project "%s" had errors. Skipping SVN commit so that the '
                'bad migration can be fixed. Please address errors and re-run '
                'the script or commit manually.', repo['path'])
        elif args.skip_commit:
            logging.info('Skipping SVN Commit. You must commit manually to '
                'save changes.')
        else:
            try:
                svn.cleanRepo(repo['path'])
                svn.commit(repo['path'], 'Migrating from %s non-modular widget '
                    'to modular widgets in %s using migrate.py' %(
                        widgetDir, moduleDir))
            except svn.SvnError as e:
                log.error(e.message)
                log.error('Unable to commit migration of %s to %s\n', widgetDir,
                          moduleDir)
        print '\n'

    # Report results
    if len(reposWithErrors):
        log.error('Some errors were encountered during this migration. See the '
            'logs for details.')

        uncommitedRepos = []
        unchangedRepos = []
        for key, value in reposWithErrors.iteritems():
            if value:
                uncommitedRepos.append(key)
            else:
                unchangedRepos.append(key)

        if len(unchangedRepos):
            log.error('At least one migration was skipped in each of the '
                'following repos because of errors in updating the repo or '
                'finding the widget and module to migrate between: \n\t' +
                '\n\t'.join(unchangedRepos))
        if len(uncommitedRepos):
            log.error('Changes to the following repos have not been '
                'committed due to errors during migration: \n\t' +
                '\n\t'.join(uncommitedRepos))
    elif args.skip_commit:
        print ('Modular widget migration successful, please check and commit '
               'all changes.')
    else:
        print 'Modular widget migration successful, all changes committed!'
