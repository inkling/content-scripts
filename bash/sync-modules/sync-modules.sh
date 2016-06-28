#! /bin/bash

#---------------------------------------------------------------------
# Inkling Project Sync
#---------------------------------------------------------------------

#-------------------------------------------------------------------
# Settings
#-------------------------------------------------------------------

# Terminal comment colors
c_reset=$(tput sgr0) # reset the foreground colour
c_error=$(tput setaf 1)
c_success=$(tput setaf 2)
c_info=$(tput setaf 3)
c_comment=$(tput setaf 4)
c_target=$(tput setaf 5)
c_source=$(tput setaf 6)
c_dim=$(tput dim)

# Get the name of the script to rexecute if JSON can't be found
script_name=$(basename -- "$0")

# Input CSV containing source and target projects and environments.
INPUT=project-list.json

directory=/trunk/assets/modules/

rsync_delete=FALSE

simulate_run=FALSE

fail_log_file=failed-projects.json

# Option Flags
while getopts ":f:ds" opt; do
  case $opt in
    d)
        rsync_delete=TRUE >&2
      ;;
    s)
        simulate_run=TRUE >&2
      ;;
    f)
      INPUT=$OPTARG
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo $c_error"Option -$OPTARG requires an argument."$c_reset >&2
      exit 1
      ;;
  esac
done

#-------------------------------------------------------------------
# Welcome Message
#-------------------------------------------------------------------
echo -e $c_success"
------------------------------
Modules JSON Sync 1.0.0
------------------------------
"

#-------------------------------------------------------------------
# Check if the JSON file extist
#-------------------------------------------------------------------

if [ ! -f "$INPUT" ];
  then
    echo $c_error"No JSON file found. Make sure $c_info$INPUT$c_error is in
the same folder as this script.
"

    #-------------------------------------------------------------------
    # Warn that the input CSV could not be found
    #-------------------------------------------------------------------

    # Pause while wating for user to acknloedge
    read -p $c_comment"Press RETURN to try again"$c_reset

    # Once
    exec bash ./$script_name
fi

#-------------------------------------------------------------------
# BEGIN Reading JSON File to load the pre-flight overview
#-------------------------------------------------------------------

# Display the overview message
if [ "$simulate_run" == "FALSE" ];then
    echo -e $c_info"--- Warning ---
This script will overwrite the modules in the Target projects \
with the modules from the Source project. The list of projects \
and setting can be changed in $c_reset$INPUT$c_info.$c_source
"$c_reset
else
    echo -e $c_comment"--- DRY RUN ACTIVE ---
This script will SIMULATE overwriting the modules in the Target projects \
with the modules from the Source project. The list of projects \
and setting can be changed in $c_reset$INPUT$c_info.$c_source
"$c_reset
fi

# Display Delete Mode Warning
if [ "$rsync_delete" = "TRUE" ]; then
    echo -e $c_error"--- DELETE MODE ACTIVE ---
Modules in the target projects that are NOT in the \
source projects will be deleted!
"$c_reset
fi

# Store the number of syncs so we can add a counter
total_target_count=0;

# Store CSV line number
csv_line=0;

# Index of the project (to determine source from targets)
project_index=0;

# Regex for the line
regex='"id":[^"]*"([^"]*)",[^"]*"title":[^"]*"([^"]*)",[^"]*"group":[^"]*"([^"]*)"'

# Read the CSV file and loop through each line with the following variables.
[ ! -f $INPUT ] &while IFS='' read -r line || [[ -n "$line" ]]; do

# If a project if is found, store the shortname and title
if [[ $line =~ $regex ]]
then
    # Increment the total sync count
    let "project_index++"

    project_shortname="${BASH_REMATCH[1]}"
    project_title="${BASH_REMATCH[2]}"
    project_group="${BASH_REMATCH[3]}"

# Skip the line if no project is found
else
    echo -e $c_info"---"$c_reset
    continue
fi


# Increment the CSV line number (for indexing)
let "csv_line++"

if [ $project_index = 1 ]
    then
        # Display the source project and title
        echo -e $c_reset"Source Project:
$c_comment[S]$c_source $project_shortname\t| $project_title $c_info($project_group)$c_reset
"
fi

if [ $project_index = 2 ]
    then

        # Display the target(s) title
        echo -e $c_reset"Target Project(s):"
fi

if [ $project_index -ge 2 ]
    then
    # Increment the total sync count
    let "total_target_count++"

    echo -e "$c_comment[$total_target_count] $c_target$project_shortname\t| $project_title $c_info($project_group)$c_reset"

fi

#-------------------------------------------------------------------
# END Read CSV File to load the overview
#-------------------------------------------------------------------
# The input is submitted to the CSV using "<"
done < $INPUT

#-------------------------------------------------------------------
# Prompt user to continue if settings are correct.
#-------------------------------------------------------------------
# Display Delete Mode Warning
if [ "$rsync_delete" = "TRUE" ]; then
    echo -e $c_error"
--- DELETE MODE ACTIVE ---
Modules in the target projects that are NOT in the \
source projects will be deleted!"$c_reset
fi

read -p $c_comment"
Do you want to continue (Y/N)? "$c_reset

[ "$(echo $REPLY | tr [:upper:] [:lower:])" == "y" ] || exit


#-------------------------------------------------------------------
# Set the timer to track elapsed time
#-------------------------------------------------------------------
# Get time as a UNIX timestamp (seconds elapsed since Jan 1, 1970 0:00 UTC)
T="$(date +%s)"

# Store the current sync count while iterating through
current_target_count=0;

#-------------------------------------------------------------------
# BEGIN Read CSV and run SVN commands per line
#-------------------------------------------------------------------
echo  -e $c_success"\n\
Beginning module sync!"$c_reset

# Reset CSV line number counter for second loop
csv_line=0;

# Index of the project (to determine source from targets)
project_index=0;

# Setup fail log
fail_log_pre='[\n
\t{ "id": "'$source_shortname'", "title": "'$source_title'", "group": "'$project_group'" },\n'

# Read the CSV file and loop through each line with the following variables.
[ ! -f $INPUT ] &while IFS='' read -r line || [[ -n "$line" ]]; do

# Increment the CSV line number (for indexing)
let "csv_line++"

# If a project if is found, store the shortname and title
if [[ $line =~ $regex ]]
then
    # Increment the total sync count
    let "project_index++"

    project_shortname="${BASH_REMATCH[1]}"
    project_title="${BASH_REMATCH[2]}"
    project_group="${BASH_REMATCH[3]}"

# Skip the line if no project is found
else
    continue
fi

# -------------------------------------------------------------------
# If source line, CHECKOUT SOURCE
# -------------------------------------------------------------------

if [ $project_index = 1 ]; then

# Set semantic vars for columns for source
source_shortname=$project_shortname
source_title=$project_title

# Echo the current source project
echo -e $c_source\
"\n\
--------------------------------------------------------------------\n\
$c_reset[Source] $c_source$source_shortname | $source_title$c_reset"

    if [ "$simulate_run" == "FALSE" ];then
        # If the project doesn't exist already, check out a working copy
        if [ ! -d projects/$source_shortname ]; then
                echo -e $c_info"Checking out source project"$c_reset
                svn checkout https://svn.inkling.com/svn/$source_shortname/trunk/assets/modules projects/$source_shortname
        else
            echo -e $c_info"Already checked out"$c_reset
        fi

        # Update the working copy for good measure
        svn update projects/$source_shortname
    else
        echo -e "Simulating source checkout and update..."
    fi

    # Restart the loop so you don't rsync source with source!
    continue
fi



# -------------------------------------------------------------------
# Every remaining line, CHECKOUT TARGET
# -------------------------------------------------------------------

# Increment the CSV line number (for indexing)
let "current_target_count++"

# Store semantic vars for the columns
target_shortname=$project_shortname
target_title=$project_title

# Log the current sync count and add a separator
echo -e $c_target\
"\n\
--------------------------------------------------------------------\n\
$c_reset[$current_target_count/$total_target_count] $c_target$target_shortname | $target_title$c_reset"

if [ "$simulate_run" == "FALSE" ];then
    # If the project doesn't exist already, check out a working copy
    if [ ! -d projects/$target_shortname ]; then
            echo -e $c_info"Checking out target project"$c_reset
            svn checkout https://svn.inkling.com/svn/$target_shortname/trunk/assets/modules projects/$target_shortname
    else
        echo -e $c_info"Already checked out"$c_reset
    fi

    # Update the working copy for good measure
    svn update projects/$target_shortname
else
    echo -e "Simulating target checkout and update..."
fi

#-------------------------------------------------------------------
# RUN the RSYNC
#-------------------------------------------------------------------

#-------------------------------------------------------------------
# Modify exclude list if non-existent
#-------------------------------------------------------------------
# Copy the source directory contents into the target directory
echo -e $c_reset"\nOverwriting contents of $c_info$directory$c_reset in" $c_target"$target_shortname$c_reset with "$c_source"$source_shortname"$c_reset

if [ "$simulate_run" == "FALSE" ];then
    if [ $rsync_delete = "TRUE" ]
    then
       rsync --delete --recursive --cvs-exclude projects/$source_shortname/ projects/$target_shortname
    else
       rsync --recursive --cvs-exclude projects/$source_shortname/ projects/$target_shortname
    fi
else
    echo -e "Simulating rsync with force delete..."
fi

#-------------------------------------------------------------------
# CLEAN local copy of TARGET for commiting
#-------------------------------------------------------------------
if [ "$simulate_run" == "FALSE" ];then
    # Add any unversioned files (WARNING: this will add ignored files!)
    printf $c_success
    svn status projects/$target_shortname | grep ^\? | awk '{print $2}' | xargs svn add
    printf $c_reset

    # Delete any missing files
    printf $c_error
    svn status projects/$target_shortname | grep ^\! | awk '{print $2}' | xargs svn --force delete
    printf $c_reset
else
    echo -e "Simulating cleaning local copy and adding files..."
fi

#-------------------------------------------------------------------
# COMMIT new local changes in TARGET
#-------------------------------------------------------------------
echo -e $c_info"Commiting..."$c_reset

if [ "$simulate_run" == "FALSE" ];then
    svn commit -m "Sync script commit" projects/$target_shortname

    if [ ! "$?" == "0" ]; then
        echo -e $c_error"Error: "$c_reset$target_shortname$c_error" failed to commit. Added to $fail_log_file"
        fail_log_pre+='\t{ "id": "'$target_shortname'", "title": "'$target_title'", "group": "'$project_group'" },\n'

        else
            echo -e $c_success"Done: "$c_reset$target_shortname$c_success" commited successfuly"
    fi
    # $? is the status of the last command. 0 === success, anything else === failure.
else
    echo -e "Simulating target commit..."
fi


if [ "$current_target_count" = "$total_target_count" ]; then
    echo -e $c_comment"No more projects in sync list"$c_reset
else
    echo -e $c_comment"Moving on to next target project..."$c_reset
fi

#-------------------------------------------------------------------
# END Read CSV File to load the overview
#-------------------------------------------------------------------
# The input is submitted to the CSV using "<"
done < $INPUT

fail_log_pre+="]"


if [ "$simulate_run" == "FALSE" ];then
    # Log Errors to file
    echo -e $fail_log_pre > $fail_log_file
else
    echo -e "Simulating writing to log file..."
fi

#-------------------------------------------------------------------
# LOG completion time of ALL SYNCS
#-------------------------------------------------------------------
# Get the new time
T="$(($(date +%s)-T))"

# Let the user know we're done
echo $c_comment'
--------------------------------------------------------------------
'$c_comment'All syncs completed in ~'$T' seconds'$c_reset

# This second check is required to catch the last line
# if [[ $source_project != "" ]] ; the\
#     echo -e "Source Project: $source_project \n\
# Source Env: $source_env \n\
# Target Project: $target_project \n\
# Target Env: $target_env"
# fi
