# project_svn.py
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

"""Utility methods for manipulating project svn repos.
"""

import logging
import os
import subprocess

from s9logging import s9logging

s9logging.configureLogging()
log = logging.getLogger(__name__)

PROJECT_MODULE_DIR = 'assets/modules'
TESTING_SUFFIX = '-testing'

# Spec for module-only work such as listing, deleting, or synchronizing modules.
MODULES_UPDATE_SPECS = [
    {
        'path': './' + PROJECT_MODULE_DIR,
        'depth': 'infinity'
    }
]

# Spec for migrating from old widgets & patterns to modular ones.
MODULE_MIGRATION_UPDATE_SPECS = MODULES_UPDATE_SPECS + [
    {
        'path': './',
        'depth': 'infinity'
    }
]

# Spec for syncing styles across projects.
STYLES_UPDATE_SPECS = [
    {
        'path': './',
        'depth': 'immediates'
    },
    {
        'path': './assets/sass',
        'depth': 'infinity',
    },
    {
        'path': './assets/css',
        'depth': 'infinity'
    }
]


class SvnError(Exception):
    """Exception raised for errors executing SVN commands.

    Attributes:
        message - Explanation of the error.
        cause - Exception raised executing the svn command, if any.

    """

    def __init__(self, message, cause=None):
        self.message = message


def cleanRepo(path):
    """Adds unversioned files and deletes missing files from SVN.
    """
    log.info('Cleaning up svn status for %s', path)
    try:
        subprocess.check_call([r"svn status " + path + r" | egrep '^\?' |"
            " awk '{print $2}' | xargs svn add"], shell=True)
        subprocess.check_call([r"svn status " + path + r" | egrep '^\!' |"
            " awk '{print $2}' | xargs svn --force delete"], shell=True)
    except subprocess.CalledProcessError as e:
        raise SvnError('Unable to clean up SVN state', cause=e)


def delete(path):
    """SVN deletes specified path.
    """
    log.info('Performing SVN delete of %s', path)
    try:
        subprocess.check_call(['svn', 'delete', path])
    except subprocess.CalledProcessError as e:
        raise SvnError('Unable to perform SVN delete', cause=e)


def commit(path, message):
    """SVN commits in specified repo with message.
    """
    log.info('Performing SVN commit of "%s" with message "%s"', path, message)
    try:
        subprocess.check_call(['svn', 'commit', '-m', message], cwd=path)
    except subprocess.CalledProcessError as e:
        raise SvnError('Unable to perform SVN commit', cause=e)


def ensureRepo(name, syncSpecs, environment='testing'):
    """Checks out and updates an existing repo, returning a dict of repo info.

    Args:
        repo - Repo project short name or path to repo
        environment - Project environment. Needed only when repo is not checked
            out. Defaults to testing.

    Returns:
        A dictionary representation of the repo with the following properties:
            name - The shortname of repo or specified relative path to repo.
            path - The path to the repo.
            message - An error message if checking out or updating the repo
                failed.
    """
    if os.path.isabs(name):
        path = name
    else:
        path = os.path.normpath(os.path.join(os.getcwd(), name))

    repo = {
        'name': name,
        'path': path
    }

    if os.path.isdir(path):
        _updateProject(path, syncSpecs)
    else:
        # 'name' is shortname rather than repo path. Still, the repo might
        # already be checked out.
        expectedRepoPath = _getRepoPath(name, environment)
        if os.path.isdir(expectedRepoPath):
            repo['path'] = expectedRepoPath
            _updateProject(expectedRepoPath, syncSpecs)
        else:
            repo['path'] = _checkoutProject(
                name, syncSpecs, environment=environment)

    return repo


def _getRepoPath(shortName, environment):
    return os.path.join(os.getcwd(),
                        shortName + _getEnvironmentSuffix(environment))


def _getEnvironmentSuffix(environment):
    return TESTING_SUFFIX if environment == 'testing' else ''


def _checkoutProject(shortName, syncSpecs, environment='testing'):
    """Checks out an SVN project into the working directory and returns project
    root path.
    """
    environmentSuffix = _getEnvironmentSuffix(environment)
    serverBaseUrl = 'https://svn' + environmentSuffix + '.inkling.com/svn/'
    serverUrl = serverBaseUrl + shortName + '/trunk'
    destinationPath = _getRepoPath(shortName, environment)

    log.info('Performing SVN checkout of %s as %s',
        serverUrl, destinationPath)
    # Checkout empty trunk of project repo to be sure it exists and have a fully
    # functional repo.
    try:
        subprocess.check_call(['svn', 'checkout',
            serverUrl,
            destinationPath,
            '--depth', 'empty'])
    except subprocess.CalledProcessError as e:
        raise SvnError('Unable to checkout SVN project %s in %s' % (
            shortName, environment), cause=e)

    _updateProject(destinationPath, syncSpecs)
    return destinationPath

def _updateProject(projectPath, syncSpecs):
    """Updates the svn project at projectPath.
    """
    log.info('Performing SVN update of %s', projectPath)
    if not _isRepoRoot(projectPath):
        raise SvnError('"%s" is not part of an SVN repo' % projectPath)

    for spec in syncSpecs:
        path = os.path.normpath(os.path.join(projectPath, spec['path']))
        try:
            if subprocess.call(['svn info %s | grep "Depth: %s"' % (
                    path, spec['depth'])], shell=True) == 0:
                subprocess.check_call(['svn', 'update', path, 'depth',
                    spec['depth']])
            else:
                subprocess.check_call(['svn', 'update', path,
                    '--set-depth', spec['depth'], '--parents'])
        except subprocess.CalledProcessError as e:
            raise SvnError('Unable to update SVN project at "%s"' % projectPath,
                cause=e)

def _isRepoRoot(path):
    """Returns whether the path is a SVN repo root.
    """
    # If SVN info returns without an error then path is part of a repo.
    return (subprocess.call(['svn', 'info', path],
                            stdout=open(os.devnull, 'w'),
                            close_fds=True) == 0
            and os.path.isdir(os.path.join(path, '.svn')))
