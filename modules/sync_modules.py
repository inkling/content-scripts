#!/usr/bin/env python
#
# sync_modules.py
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

"""A script to sync modules between projects.

This script will locally check out only the module directories of every relevant
project svn repo. If the repo is already checked out you can substitute the path
to the repo for the repo shortname and the environment will be ignored. Modules
will be synced only after both source and destination repos are successfully
checked out and updated.

Configuration files must be a CSV in the form of:
source_shortname,source_environment,destination_shortname,destination_environment,module_name,module_name2,...
source_shortname,source_environment,destination_shortname,destination_environment,module_name,module_name2,...

Example command lines:
    ./sync_modules --source sn_abd7/ --repos andys_test_projec-testing/ \
        --modules com.inkling.samples.sample-patterns \
        com.inkling.samples.sample-widgets
    ./sync_modules -c <config file>
"""

from __future__ import print_function

import argparse
import csv
import json
import logging
import os
import subprocess
import sys

from distutils.version import StrictVersion

import list_modules
from s9logging import s9logging
import svn.project_svn as svn

parser = argparse.ArgumentParser(description='Sync modules across Inkling '
    'projects')
parser.add_argument('--modules', nargs='+', help='Names of modules to sync')
parser.add_argument('-s', '--source-repo', dest='source', help='Source project '
    'shortname or path')
parser.add_argument('--repos', nargs='+', help='Destination project shortnames '
    'or paths')
parser.add_argument('-e', '--environment', choices=['stable', 'testing'],
    default='stable')
parser.add_argument('-f', '--force', action='store_true', default=False,
    help='Force module sync regardless of version incompatibility')
parser.add_argument('-c', '--config', help='CSV file specifying repos and '
    'environments, each row in the form '
    '"source-shortname,source-environment,destination-shortname,'
    'destination-environment,module1,module2,..."')
parser.add_argument('-n', '--dry-run', action='store_true', default=False,
    help='Dry run performing no sync or svn commit')

s9logging.configureLogging()
log = logging.getLogger(__name__)


def _getSyncSpecsFromCsv():
    """Returns a list of tuples of the form (source name, source environment,
    destination name, destination environment, set of modules to sync) taken
    from the CSV configuration file if one was specified.
    """
    results = []
    if args.config:
        with open(args.config, 'rb') as file:
            reader = csv.reader(file)
            try:
                for row in reader:
                    # Strip any whitespace in row contents.
                    row = map(str.strip, row)
                    if len(row) < 5 or not (row[0] and row[1] and row[2] and
                            row[3] and row[4]):
                        log.warning('CSV has invalid number of arguments at '
                            'line %s, skipping line.\n', reader.line_num)
                    else:
                        results.append((row[0], row[1], row[2], row[3],
                                        set(row[4:])))
            except csv.Error as e:
                logging.error('Unable to parse CSV at line %s, skipping rest of'
                    ' file.\n', reader.line_num)

    return results

def _getVersionTuple(v):
    """Convert version string into a version tuple for easier comparison.
    """
    return tuple(map(int, (v.split("."))))

def _getModulesToSync(sourceInfo, targetInfo, moduleNames):
    """Returns a list of modules to sync.

    Finds all modules in sourceInfo that are in moduleNames. Compares each
    version of those modules between source and target repos. If --force is
    false, will remove any matches that would cause a downgrade or a major
    version change.

    Args:
        sourceInfo - Source repo module info object
        targetInfo - Target repo module info object
        moduleNames - A list of module names to sync between the two repos

    Returns:
        A list of modules to sync.
    """
    modulesToSync = {}
    for module in sourceInfo:
        if module['name'] in moduleNames:
            modulesToSync[module['name']] = module
            moduleNames.remove(module['name'])

    if len(moduleNames) > 0:
        print ('\nUnable to find the following modules in source project:')
        for name in moduleNames:
            print('\t' + name)

    for module in targetInfo:
        if module['name'] in modulesToSync:
            existingVersion = _getVersionTuple(module['version'])
            newVersion = _getVersionTuple(
                modulesToSync[module['name']]['version'])
            if existingVersion > newVersion:
                if args.force:
                    log.warning('Downgrading module "%s" from version %s to '
                        'version %s\n', module['name'],
                        module['version'],
                        modulesToSync[module['name']]['version'])
                else:
                    log.error('Downgrading module "%s" from version %s to '
                        'version %s. Skipping sync\n', module['name'],
                        module['version'],
                        modulesToSync[module['name']]['version'])
                    del modulesToSync[module['name']]
            elif newVersion[0] > existingVersion[0]:
                if args.force:
                    log.warning('Potentially breaking upgrade (major version '
                        'change) for module "%s" from version %s to '
                        'version %s\n', module['name'],
                        module['version'],
                        modulesToSync[module['name']]['version'])
                else:
                    log.error('Potentially breaking upgrade (major version '
                        'change) for module "%s" from version %s to '
                        'version %s. Skipping update\n', module['name'],
                        module['version'],
                        modulesToSync[module['name']]['version'])
                    del modulesToSync[module['name']]
    return modulesToSync.values()

def _syncModules(modulesToSync, target):
    """Syncs all modules into the target repo.

    Args:
        modulesToSync - A list of module infos from source repo to sync to
            target.
        target - Target repo information
    """
    for module in modulesToSync:
        targetPath = os.path.join(target['path'], svn.PROJECT_MODULE_DIR)
        if args.dry_run:
            print('\n"Move"', module['name'], 'v' + module['version'])
        else:
            subprocess.check_call(['rsync', '--delete',
                '--recursive', module['systemPath'], targetPath])
            print('\nMoved', module['name'], 'v' + module['version'])


if __name__ == '__main__':
    args = parser.parse_args()

    if not args.config and not (args.source and args.repos and args.modules):
        parser.print_usage()

    moduleInfo = []

    syncSpecs = _getSyncSpecsFromCsv()
    if args.repos:
        syncSpecs = [(args.source, args.environment, repo, args.environment,
            set(args.modules)) for repo in args.repos]

    for sourceName, sourceEnv, targetName, targetEnv, moduleNames in syncSpecs:
        try:
            source = svn.ensureRepo(sourceName, svn.MODULES_UPDATE_SPECS,
                environment=sourceEnv)
        except svn.SvnError as e:
            log.error(e.message)
            log.error('Source repo in error state, unable to copy any modules '
                      'from %s to %s. Skipping\n', sourceName, targetName)
            continue

        try:
            target = svn.ensureRepo(targetName, svn.MODULES_UPDATE_SPECS,
                environment=targetEnv)
        except svn.SvnError as e:
            log.error(e.message)
            log.error('Target repo in error state, unable to copy any modules '
                      'from %s to %s. Skipping\n', sourceName, targetName)
            continue

        print('Syncing modules from "%s" to "%s"' % (sourceName, targetName))
        sourceInfo = list_modules.getModuleInfo(source['path'])
        targetInfo = list_modules.getModuleInfo(target['path'])

        modulesToSync = _getModulesToSync(sourceInfo, targetInfo, moduleNames)

        # Don't clean & commit if we're not going to move anything.
        if len(modulesToSync) == 0:
            continue

        try:
            _syncModules(modulesToSync, target)
        except Exception as e:
            log.error('Error syncing modules to "%s", skipping commit.\n',
                      target['path'])
            continue

        if args.dry_run:
            print('\n"Clean" SVN status for', target['path'])
            print('\n"SVN commit"', target['path'])
        else:
            try:
                svn.cleanRepo(target['path'])
                svn.commit(target['path'], 'Copying modules from ' +
                           sourceName + ' using sync_modules.py.')
            except svn.SvnError as e:
                log.error(e.message + '\n')
