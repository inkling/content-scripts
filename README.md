# Content Scripts

The Inkling Content Scripts are a set of scripts that automate inspecting and copying content
between your Inkling projects. These scripts will locally check out projects using subversion and
call out to the shell to run most commands. You will only be able to use these scripts with projects
that you have read and write access to.

## Features

* Copy CSS & Sass between SVN projects with `sync_styles`
* Support modules in projects by:
    * Listing the modules in a project with `list_modules`
    * Deleting modules from a project with `delete_modules`
    * Copying modules between projects with `sync_modules`

## Getting Started

Get started easily with a one line command to download and bootstrap the repo, or if you want to
see under the hood, you can follow setup instructions manually. These instructions will help you
locally clone the content-scripts repository and get bootstrapped for running the scripts.

### Automatic installation

In the directory you want to house the content-scripts repo run:

`curl 'https://raw.githubusercontent.com/inkling/content-scripts/master/install.sh' | bash`

If you want to change the installation directory you can do so by setting the ICS_INSTALL_DIR
environment variable. You can do that just for this one command by doing:

`ICS_INSTALL_DIR='<path to install location>' bash -c 'curl https://raw.githubusercontent.com/inkling/content-scripts/master/install.sh | bash'`

The installation process starts by checking that you have installed all the prerequisites needed to
run the content scripts. If you have not, the installation will fail with an error message before
even cloning the repository. Install the necessary tool and repeat.

The installation process will modify your `~/.profile` file to:
* Add the `content-scripts` repo to your `PYTHONPATH`.
* Add the `content-scripts/bin` directory to your `PATH`. This directory holds bash wrappers to the
python scripts that will setup your `PYTHONPATH` for a run for easy use immediately.

These changes to your profile will not take effect globally until you restart your machine. As the
installation script should direct, you can have them take immediate effect in your terminal session
by sourcing your profile:
`source ~/.profile`

### Manual installation

1. Clone the content-scripts repository:
`git clone git@github.com:inkling/content-scripts`

2. Run `bootstrap.sh` located at the root of the content-scripts repo.
This script will check that you have installed all necessary prerequisites and fail if you have not.
Please install any tools as directory and re-run the bootstrap script until it completes without an
error.

3. The bootstrap script will modify your `~/.profile` file to:
    * Add the `content-scripts` repo to your `PYTHONPATH`.
    * Add the `content-scripts/bin` directory to your `PATH`. This directory holds bash wrappers to the
python scripts that will setup your `PYTHONPATH` for a run for easy use immediately.

These changes to your profile will not take effect globally until you restart your machine. As the
installation script should direct, you can have them take immediate effect in your terminal session
by sourcing your profile:
`source ~/.profile`

## Requirements

The content scripts are Python or Bash scripts that use the shell to complete most actions.
They should work on any Mac OSX or Linux machine with the following programs installed and available
on the users path:

* Python 2.7+
* rsync 2.6.9+
* RubyGems 2.2.2+
* Compass 1.0.3+

## Usage

Each python script located in this repository is wrapped by a bash script located in
`content-scripts/bin`. These bash scripts take identical arguments, but set up the PYTHONPATH for
the run of the script, helping work around any path issues you might have, especially after first
install. These bash wrappers are also added to your PATH so the scripts are available from any
directory.

Each script is configured using a CSV file unique to that script.

Each script has an option for the environment projects are in. This environment should always
be `stable` for all externally available projects.

Each script will locally check out the repositories via SVN, modify, and commit changes. You must
have read and write permissions for the projects you want to update.

### Syncing styles

The `sync_styles` script copies CSS & Sass files between projects and commits them only if Sass
compilation succeeds in the destination project. The script is available as:

* `content-scripts/sync/styles/sync_styles.py`
* `content-scripts/bin/sync_styles.sh`

#### Flags

* `--config`, `-c`: Path to the CSV configuration file.
* `--delete`, `-d`: Enable deleting extraneous files from destination directories.
* `--dry-run`, `-n`: Dry run that prints script actions but does not actually copy files or SVN
commit.

#### Examples

```
sync_styles.py -c sync.csv
sync_styles.py --delete -c sync.csv
```

#### CSV format

Each line of the CSV details a set of files to copy between two projects with the following format:

`source project short name, source environment, destination project short name, destination environment, rsync exclude file, comma separated list of paths to copy`

* Each path can be a file or a directory. If it is a directory the directory name must end in a trailing slash.
* Paths to copy are relative to the project trunk.
* The exclude file path is relative to where you are running the script from.

### Modules

Until a hosted module management UI is available, we have provided a few scripts to help users
manage modules in their projects. These scripts will be deprecated and removed when all the
functionality is available through Inkling APIs and UIs.

#### Listing modules in a project

The `list_modules` script will print the name and version of modules in a project. The script is
available as:

* `content-scripts/modules/list_modules.py`
* `content-scripts/bin/list_modules.sh`

You can call `list_modules` with a CSV configuration file, or just specify the project shortnames
as positional arguments.

##### Flags

* `--config`, `-c`: Path to the CSV configuration file.
* `--environment`, `-e`: Environment of projects specified as positional arguments rather than in
a CSV config file. Should generally be stable

##### Examples

```
list_modules.py -c list.csv
list_modules.py -e [environment] [project short name]
```

##### CSV format

Each line of the CSV specifies a project to list the modules for with the following format:

`project short name, project environment`

#### Deleting modules from a project

The `delete_modules` script will delete modules with a given name from a project, regardless of
the module version. The script is available as:

* `content-scripts/modules/delete_modules.py`
* `content-scripts/bin/delete_modules.sh`

##### Flags

* `--config`, `-c`: Path to the CSV configuration file.
* `--dry-run`, `-n`: Dry run that prints script actions but does not actually delete modules or SVN
commit.

##### Examples

```
delete_modules.py -c delete.csv
delete_modules.py -n -c delete.csv
```

##### CSV format

Each line of the CSV file specifies a project and a set of modules to delete from that project
with the following format:

`project short name, project environment, comma separated list of module names`

#### Copying modules between projects

The `sync_modules` script will copy a set of modules from one project to another. Depending on the
configuration it will warn or error if you try to downgrade a module or do a major version upgrade
as a result of the sync. The script is available as:

* `content-scripts/modules/sync_modules.py`
* `content-scripts/bin/sync_modules.sh`

##### Flags

* `--config`, `-c`: Path to the CSV configuration file.
* `--force`, `-f`: Force module sync regardless of potential problems from version downgrade or
major version upgrade.
* `--dry-run`, `-n`: Dry run that prints script actions but does not actually delete modules or SVN
commit.

##### Examples

```
sync_modules.py -c sync.csv
sync_modules.py -f -c sync.csv
```

##### CSV format

Each line of the CSV file specifies a list of modules to copy between two projects with the
following format:

`source project short name, source environment, destination project short name, destination environment, comma separated list of modules to copy`

## Contributing

If you'd like to contribute to the content scripts, please fork this project and create a pull
request with any changes from your branch to inkling/master.

## Credit

This project was created by the Inkling Client Solutions and Context Extensibility teams.

## Contact

If you are an Inkling customer and need to reach out please contact your Inkling account
representative.

## Copyright and License

Copyright 2015 Inkling Systems, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
