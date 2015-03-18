#!/usr/bin/env python
#
# list_modules.py
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

"""A script to print out the modules in a set of projects.

This script will locally check out only the module directories of every relevant
project svn repo. If the repo is already checked out you can substitute the path
to the repo for the repo shortname and the environment will be ignored.

Configuration files must be a CSV in the form of:
repo1_shortname,repo1_environment
repo2_shortname,repo2_environment

Example command lines:
    ./list_modules -e testing andys_test_projec
    ./list_modules andys_test_project-testing/
    ./list_modules -c <config file>
"""

from __future__ import print_function

import argparse
import csv
import json
import logging
import os
import sys

from s9logging import s9logging
import svn.project_svn as svn

parser = argparse.ArgumentParser(description='List modules in an Inkling '
    'project')
parser.add_argument('repos', nargs='*', help='Project shortname in specified '
    'environment or path to existing project repos')
parser.add_argument('-c', '--config', help='CSV file specifying repos and '
    'environments, each row in the form "shortname,environment"')
parser.add_argument('-e', '--environment', choices=['stable', 'testing'],
    default='stable')

s9logging.configureLogging()
log = logging.getLogger(__name__)

MODULE_CONFIG_FILE = 'module.json'


def getModuleInfo(projectPath):
    """Returns a list of the project's modules' module.json as a dict, with an
    extra 'systemPath' property added for module path.
    """
    moduleInfo = []
    moduleDir = os.path.join(projectPath, svn.PROJECT_MODULE_DIR)
    if not os.path.isdir(moduleDir):
        return moduleInfo

    modules = os.listdir(moduleDir)

    for module in modules:
        jsonPath = os.path.join(projectPath, svn.PROJECT_MODULE_DIR, module,
            MODULE_CONFIG_FILE)
        if os.path.exists(jsonPath):
            with open(jsonPath) as json_data:
                data = json.load(json_data)
                data['systemPath'] = os.path.join(projectPath,
                    svn.PROJECT_MODULE_DIR, module)
                moduleInfo.append(data)

    return moduleInfo


def _getRepoSpecsFromCsv():
    """Returns a list of tuples of the form (source name, source environment)
    taken from the CSV configuration file if one was specified.
    """
    results = []
    if args.config:
        with open(args.config, 'rb') as file:
            reader = csv.reader(file)
            try:
                for row in reader:
                    # Strip any whitespace in row contents.
                    row = map(str.strip, row)
                    if len(row) != 2 or not row[0] or not row[1]:
                        log.warning('CSV has invalid number of arguments at '
                                    'line %s, skipping line.\n',
                                    reader.line_num)
                    else:
                        results.append((row[0], row[1]))
            except csv.Error as e:
                log.error('Unable to parse CSV at line %s, skipping rest of '
                          'file.\n', reader.line_num)

    return results

if __name__ == '__main__':
    args = parser.parse_args()

    if not args.repos and not args.config:
        parser.print_usage()

    repoSpecs = [(name, args.environment) for name in args.repos] + \
            _getRepoSpecsFromCsv()

    for name, environment in repoSpecs:
        try:
            repo = svn.ensureRepo(name, svn.MODULES_UPDATE_SPECS,
                environment=environment)
        except svn.SvnError as e:
            log.error(e.message + '\n')
            continue

        print('Project:', repo['path'])
        info = getModuleInfo(repo['path'])
        if len(info) > 0:
            for data in info:
                print('\t' + data['name'] + ' v' + data['version'])
            print('')
        else:
            print('\tNo modules\n')
