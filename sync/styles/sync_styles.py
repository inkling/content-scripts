#!/usr/bin/env python
#
# sync_styles.py
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

"""A script to sync styles between projects.

This script will locally check out only the module directories of every relevant
project svn repo. If the repo is already checked out you can substitute the path
to the repo for the repo shortname and the environment will be ignored. Files
will be synced only after both source and destination repos are successfully
checked out and updated.

This script will only sync files under assets/css and assets/sass in a project.

Configuration files must be a CSV in the form of:
source_shortname,source_environment,destination_shortname,destination_environment,path_to_rsync_exclude_file,path_to_sync1,path_to_sync2,...

* The exclude file is optional and its path is relative to where the script is
running. The file format is the rsync exclude file format and files should be
relative to the paths that are being copied.

* Paths to sync are relative to project trunk. Paths can specify either a file
or a directory but if it is a directory the path must end in a trailing slash.

Example command lines:
    ./sync_modules -c <config file>
    ./sync_modules --delete -c <config file>
"""

import argparse
import csv
import logging
import os
import subprocess

from s9logging import s9logging
import svn.project_svn as svn

parser = argparse.ArgumentParser(description='Sync styles between Inkling '
    'projects.')
parser.add_argument('-c', '--config', help='CSV file specifying sync behavior.',
    required=True)
parser.add_argument('-d', '--delete', action='store_true', default=False,
    help='Delete extraneous files from destination directories.')
parser.add_argument('-n', '--dry-run', action='store_true', default=False,
    help='Dry run performing no sync or svn commit')

s9logging.configureLogging()
log = logging.getLogger(__name__)

def _getSyncSpecsFromCsv():
    """Returns a list of tuples of the form (source name, source environment,
    destination name, destination environment, exclude file, set of paths to
    sync) taken from the CSV configuration file if one was specified.
    """
    results = []
    with open(args.config, 'rb') as file:
        reader = csv.reader(file)
        try:
            for row in reader:
                # Strip any whitespace in row contents.
                row = map(str.strip, row)
                if len(row) < 6 or not(row[0] and row[1] and row[2] and row[3]
                        and row[5]):
                    log.warning('CSV has invalid number of arguments at line '
                                '%s, skipping line.\n', reader.line_num)
                else:
                    results.append((row[0], row[1], row[2], row[3], row[4],
                        set(row[5:])))
        except csv.Error as e:
            logging.error('Unable to parse CSV at line %s, skipping rest of'
                          ' file.\n', reader.line_num)
    return results


if __name__ == '__main__':
    args = parser.parse_args()

    syncSpecs = _getSyncSpecsFromCsv()

    for sourceName, sourceEnv, targetName, targetEnv, excludeFile, \
            pathsToSync in syncSpecs:

        # Validate exclude file.
        if excludeFile and not os.path.isfile(excludeFile):
            logging.error('Exclude file "%s" does not exist. Skipping sync.\n',
                excludeFile)
            continue

        # Update source & target.
        try:
            source = svn.ensureRepo(sourceName, svn.STYLES_UPDATE_SPECS,
                environment=sourceEnv)
        except svn.SvnError as e:
            log.error(e.message)
            log.error('Source repo in error state, unable to copy any styles '
                    'from %s to %s. Skipping\n', sourceName, targetName)
            continue

        try:
            target = svn.ensureRepo(targetName, svn.STYLES_UPDATE_SPECS,
                environment=targetEnv)
        except svn.SvnError as e:
            log.error(e.message)
            log.error('Target repo in error state, unable to copy any styles '
                      'from %s to %s. Skipping\n', sourceName, targetName)
            continue

        # For each path rsync
        for path in pathsToSync:
            command = ['rsync', '--recursive', '-v']

            if args.delete:
                command.append('--delete')

            if excludeFile:
                command.extend(['--exclude-from', excludeFile])

            command.extend([os.path.join(source['path'], path),
                            os.path.join(target['path'],path)])

            if args.dry_run:
                print '"rsync" with %s' % command
            else:
                try:
                    log.info('Excuting rsync: %s', command)
                    subprocess.check_call(command)

                except subprocess.CalledProcessError as e:
                    log.error(e.message)
                    continue

        # Compile Sass.
        sassCommand = ['compass', 'compile', target['path']]

        if args.dry_run:
            print '"Compile Sass" with %s' % sassCommand
        else:
            try:
                log.info('Compiling Sass: %s', sassCommand)
                subprocess.check_call(sassCommand)
            except subprocess.CalledProcessError as e:
                log.error(e.message)
                log.error('Sass compilation error, skipping commit.')
                continue

        # Clean up svn status and commit.
        if args.dry_run:
            print '"Clean" SVN status for %s' % target['path']
            print '"SVN commit" for %s' % target['path']
        else:
            try:
                svn.cleanRepo(target['path'])
                svn.commit(target['path'], 'Syncing styles with sync_styles.py script.')
            except svn.SvnError as e:
                log.error(e.message)
                continue
