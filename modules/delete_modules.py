#!/usr/bin/env python
#
# delete_modules.py
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

"""A script to delete modules from a set of projects.

This script will locally check out only the module directories of every relevant
project svn repo. If the repo is already checked out you can substitute the path
to the repo for the repo shortname and the environment will be ignored. The
specified modules will be deleted from each project only after they are
successfully checked out and updated locally.

Configuration files must be a CSV in the form of:
repo1_shortname,repo1_environment,module_name,module_name2,...
repo2_shortname,repo2_environment,module_name3,module_name4,...

Example command lines:
    ./delete_modules -e testing --repos andys_test_projec \
            --modules com.inkling.samples.sample-patterns
    ./delete_modules --repos andys_test_project-testing/ \
            --modules com.inkling.samples.sample-patterns \
            com.inkling.samples.sample-widgets
    ./delete_modules -c <config file>
"""

from __future__ import print_function

import argparse
import csv
import json
import logging
import os
import sys

import list_modules
from s9logging import s9logging
import svn.project_svn as svn

parser = argparse.ArgumentParser(description='Delete modules in an Inkling '
    'project')
parser.add_argument('-c', '--config', help='CSV file specifying repos and '
    'environments, each row in the form'
    '"shortname,environment,module_name1,module_name2,..."')
parser.add_argument('--modules', nargs='+', help='Names of modules to delete')
parser.add_argument('--repos', nargs='+', help='Project shortnames in specified'
    ' environment or paths to existing project repos')
parser.add_argument('-e', '--environment', choices=['stable', 'testing'],
    default='stable')
parser.add_argument('-n', '--dry-run', action='store_true', default=False,
    help='Dry run performing no svn delete or commit')

s9logging.configureLogging()
log = logging.getLogger(__name__)

def _getRepoSpecsFromCsv():
    """Returns a list of tuples of the form (source name, source environment,
    set of modules to delete) taken from the CSV configuration file if one was
    specified.
    """
    results = []
    if args.config:
        with open(args.config, 'rb') as file:
            reader = csv.reader(file)
            try:
                for row in reader:
                    # Strip any whitespace in row contents.
                    row = map(str.strip, row)
                    if len(row) < 3 or not (row[0] and row[1] and row[2]):
                        log.warning('CSV has invalid number of arguments at '
                            'line %s, skipping line.\n', reader.line_num)
                    else:
                        results.append((row[0], row[1], set(row[2:])))
            except csv.Error as e:
                log.error('Unable to parse CSV at line %s, skipping rest of '
                    'file.\n', reader.line_num)

    return results


if __name__ == '__main__':
    args = parser.parse_args()

    if not args.config and not (args.repos and args.modules):
        parser.print_usage()

    repoSpecs = [(name, args.environment, set(args.modules)) for name in \
        args.repos] if args.repos else []
    repoSpecs = repoSpecs + _getRepoSpecsFromCsv()

    for repoName, environment, moduleNames in repoSpecs:
        try:
            repo = svn.ensureRepo(repoName, svn.MODULES_UPDATE_SPECS,
                environment=environment)
        except svn.SvnError as e:
            log.error(e.message + '\n')
            continue

        print('Deleting the following modules from "%s":' %
            repo['path'])
        info = list_modules.getModuleInfo(repo['path'])

        performedDelete = False

        for module in info:
            if module['name'] in moduleNames:
                moduleNames.remove(module['name'])
                if args.dry_run:
                    print('\t"%s"' % module['name'])
                    performedDelete = True
                else:
                    try:
                        svn.delete(module['systemPath'])
                        performedDelete = True
                        print('\t', module['name'])
                    except svn.SvnError as e:
                        log.error(e.message + '\n')
                        print('Skipping SVN commit for %s' % repo['path'])
                        break
        else:
            if performedDelete:
                if args.dry_run:
                    print('\n"SVN commit"', repo['path'])
                else:
                    try:
                        svn.commit(repo['path'], 'Deleting modules with '
                                   'delete_modules.py script')
                    except svn.SvnError as e:
                        log.error(e.message + '\n')

        if len(moduleNames) > 0:
            print('\nThe following modules were not present to delete:')
            for name in moduleNames:
                print('\t', name)

