#!/usr/bin/env bash
#
# sync_styles.sh
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
# Convenience script to run python script without bootstrapping. Manually setups up python path
# just for this script run and then runs python script passing along all args.


# Setup PYTHONPATH
root=$( cd "$( dirname "${BASH_SOURCE[0]}" )/../" && pwd )
export PYTHONPATH=$PYTHONPATH:$root

# Call python script with whatever python is on the path, and pass through all arguments.
python $root/sync/styles/sync_styles.py "$@"
