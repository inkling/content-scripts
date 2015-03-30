#!/usr/bin/env bash
#
# install.sh
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
#
#
# Install the content scripts repo. This script is expected to be fetched separately from the
# entire repo and used to download the repo. To fetch and run the installation script run the
# following command from the terminal:
#
# curl 'https://raw.githubusercontent.com/inkling/content-scripts/master/install.sh' | bash
#
# To change the installation directory set the ICS_INSTALL_DIR environment variable, e.g.,
# ICS_INSTALL_DIR='~/cs' bash -c 'curl https://raw.githubusercontent.com/inkling/content-scripts/master/install.sh | bash'

echo "Checking prerequisites."

# Check prerequisites.
# Keep these insync with bootstrap.sh
if [[ ! `command -v gem` ]]; then
  echo "RubyGems is required to run style sync scripts."
  echo "Please install RubyGems from https://rubygems.org/pages/download and then try again."
  exit 1
fi

if [[ ! `command -v compass` ]]; then
  echo "Compass is required to run style sync scripts."
  echo "Please run 'sudo gem install compass' and try again."
  exit 1
fi

if [[ ! `command -v python` ]]; then
  echo "Python is required for running python content scripts."
  echo 'Please install Python 2.7+ on your machine.'
  exit 1
elif [[ `python -c 'import sys; print sys.version_info < (2, 7) and "1" or "0"'` != "0" ]]; then
  echo "Python version 2.7 or later is required. Please update the Python version found in your PATH."
  exit 1
fi

if [[ ! `command -v git` ]]; then
  echo "Git is required to download the content-scripts repository."
  echo "Please follow the installation instructions at http://git-scm.com/book/en/v2/Getting-Started-Installing-Git"
  exit 1
fi

echo "Downloading content-scripts."
echo ""

# Clone git into content-scripts or environment specified instalation directory.
# Use read-only clone syntax so that you don't need a github.com account with configured ssh keys.
installDir=${ICS_INSTALL_DIR:-content-scripts}
git clone git://github.com/inkling/content-scripts.git $installDir

if [[ $? == 0 ]]; then
  $installDir/bootstrap.sh
else
  echo "Error cloning git repo locally, unable to continue."
fi
