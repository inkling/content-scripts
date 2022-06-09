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
    * Migrating from non-modular to modular versions of widgets with `migrate`

## Getting Started

Get started easily with a one line command to download the repo, or if you want to
see under the hood, you can follow setup instructions manually. These instructions will help you locally clone the content-scripts repository for running the scripts.


### Installation

`This process will spin up a detach container to use the tool but won't launch the bash terminal to start using it due docker limitations for interactive consoles that are thought for servers.`

In the directory you want to house the content-scripts repo run:

`curl 'https://raw.githubusercontent.com/inkling/content-scripts/master/install.sh' | bash`

The installation process starts by checking that you have installed all the prerequisites needed to run the content scripts. If you have not, the installation will fail with an error message before even cloning the repository. Install the necessary tool and repeat.


#### After confirming last step is done you should launch the interactive console reattaching the detached pod with the following command:
`docker exec -it inkling-rsync bash`

#### Then you are in container but you will need set your SVN credentials running the following command and after that you will be able to use the tool:
`./set-credentials.sh`



### Manuall installation on terminal

1. Clone the content-scripts repository on desired path:
`git clone git@github.com:inkling/content-scripts`

2. In the directory of content-scripts repo run:
    * `docker-compose -f toolkit-compose.yml up -d`
This step will download the tool image needed to spin the container up then it will be detached to use.

4. Run `docker exec -it inkling-rsync bash` in order to launch an interactive terminal
    * This step will mount two shared folders between you host machine and the container 
    `/sync`
    `/svn`
Any change made on those local machine folders will be reflected into the container tool path.



#### Multiple tool containers
* In case you need run more that one tool bash you can uncomment the whole block on `toolkit-compose.yml` that points to the number 2 tool and replicate the block as many containers you need.


## Docker commands 
* `docker images -a` [will display the image repository if it has been downloaded on your machine]
    `REPOSITORY                             TAG
     shipyard.inkling.com/inkling-rsync     local`

* `docker ps` this command displays if container tool is in use.
`CONTAINER ID   IMAGE                                      COMMAND   NAMES
1937s6db9a58   shipyard.inkling.com/inkling-rsync:local   "bash"    inkling-rsync`
Take in consideration the name, if you have experience with docker it could be helpful

* `docker-compose -f toolkit-compose.yml up -d` command builds the local image the container will use

* `docker exec -it inkling-rsync bash` interactive terminal to use the tool.
  Once the image is detached (Detached mode -d: Run containers in the background) you need to execute the bash from the container.

## Docker commands to clean up docker containers
* `docker stop inkling-rsync # Stops the container `
* `docker rm inkling-rsync # Removes the container `
* `docker rmi shipyard.inkling.com/inkling-rsync:local # Removes the image`



## Requirements

The content scripts are Python or Bash scripts that use the shell to complete most actions.
They should work on any Mac OSX or Linux machine with the following programs installed and available
on the users path:

* Docker latest
    

## Usage

Once you opened up the container in the interactive terminal:

Each python script located in the container tool directory is wrapped by a bash script located in
`content-scripts/bin`. These bash scripts take identical arguments, but the container sets up the PYTHONPATH for the run of the scripts. These bash wrappers are also added to the container PATH so the scripts are available from any directory inside the container.

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

#### Migrating from widgets to modular widgets

The `migrate` script helps with the final steps of cleaning up projects while migrating from widgets
to modular versions of the same widget. For a project that has non-modular widgets the migration
process is as follows:

For each widget you want to migrate:

1. Create a module containing a single widget and any patterns that reference that widget.
2. Upload the created module to the module repository.
3. Install the module into all projects that have the widget to be replaced.
4. Run the `migrate` script to clean up all projects that have duplicate versions of widgets: the
older widget and modular replacement.

The script will update all the content (HTML files) and widget JSON config files changing all
references from the non-modular widgets to instead reference the modular widgets. It then deletes
the non-modular widget and all patterns that reference it.

The script is available as:

* `content-scripts/modules/migrate.py`
* `content-scripts/bin/migrate.sh`

##### Flags

* `--config`, `-c`: Path to the CSV configuration file.
* `--skip-commit`, `-s`: Whether to skip SVN commit. If used all specified migrations will still
be performed but the changes won't be committed to SVN. That must be done manually.

##### Examples

```
migrate.py -c migrate.csv
migrate.py -c migrate.csv -s
```

##### CSV format

Each line of the CSV file specifies a single widget/module pair to migrate in a single project with
the following format:

`project short name, project environment, widget directory name, module directory name`

where the widget directory name is relative to `/assets/widgets` and the module
directory name is relative to `/assets/modules`. The module directory name should always be of the
form `orgslug.modulename`. For example, to migrate the project with shortname `sn_test_project`
from the Inkling platform Flashcard widget to its modular counterpart the config line would be:

`sn_test_project,stable,flashcard,inkling.flashcard`

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
