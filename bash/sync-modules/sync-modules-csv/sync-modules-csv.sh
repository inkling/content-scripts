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

# Get the name of the script to rexecute if CSV can't be found
script_name=$(basename -- "$0")

# Input CSV containing source and target projects and environments.
INPUT=project-list.csv

directory=/trunk/assets/modules/

rsync_delete=FALSE

fail_log_file=failed-projects.csv

# Option Flags
while getopts ":f:d" opt; do
  case $opt in
    d)
        rsync_delete=TRUE >&2
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
Modules Sync 1.0.0
------------------------------
"

#-------------------------------------------------------------------
# Check if the CSV file extist
#-------------------------------------------------------------------

if [ ! -f "$INPUT" ];
  then
    echo $c_error"No CSV file found. Make sure $c_info$INPUT$c_error is in
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
# BEGIN Reading CSV File to load the pre-flight overview
#-------------------------------------------------------------------

# Store the original internal field separator.
OLDIFS=$IFS

# Set the internal field separator to match the CSV, "," in this case.
IFS=","

# Display the overview message
echo -e $c_info"--- Warning ---
This script will overwrite the modules in the Target projects \
with the modules from the Source project. The list of projects \
and setting can be changed in $c_reset$INPUT$c_info.$c_source
"$c_reset

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

# Read the CSV file and loop through each line with the following variables.
[ ! -f $INPUT ] &while read col_a col_b
do

project_shortname="$col_a"
project_title="$col_b"

# Increment the CSV line number (for indexing)
let "csv_line++"

if [ $csv_line = 2 ]
    then
        # Display the source project and title
        echo -e $c_reset"Source Project:
$c_comment[S]$c_source $project_shortname | $project_title
"
fi

if [ $csv_line = 3 ]
    then

        # Display the target(s) title
        echo -e $c_reset"Target Project(s):"
fi

if [ $csv_line -ge 3 ]
    then
    # Increment the total sync count
    let "total_target_count++"

    echo -e "$c_comment[$total_target_count] $c_target $project_shortname | $project_title$c_reset"

fi

#-------------------------------------------------------------------
# END Read CSV File to load the overview
#-------------------------------------------------------------------
# The input is submitted to the CSV using "<"
done < $INPUT

# Reset the internal field separator
IFS=$OLDIFS

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



# Store the original internal field separator.
OLDIFS=$IFS

# Set the internal field separator to match the CSV, "," in this case.
IFS=","

# Reset CSV line number counter for second loop
csv_line=0;

# Read the CSV file and loop through each line with the following variables.
[ ! -f $INPUT ] &while read col_a col_b
do

# Increment the CSV line number (for indexing)
let "csv_line++"

# -------------------------------------------------------------------
# Skip the settings and column label lines
# -------------------------------------------------------------------
if [ $csv_line -le 1 ]; then
    continue
fi

# -------------------------------------------------------------------
# If source line, CHECKOUT SOURCE
# -------------------------------------------------------------------

if [ $csv_line = 2 ]; then

# Set semantic vars for columns for source
source_shortname=$col_a
source_title=$col_b

# Echo the current source project
echo -e $c_source\
"\n\
--------------------------------------------------------------------\n\
$c_reset[Source] $c_source$source_shortname | $source_title$c_reset"

    # If the project doesn't exist already, check out a working copy
    if [ ! -d projects/$source_shortname ]; then
            echo -e $c_info"Checking out source project"$c_reset
            svn checkout https://svn.inkling.com/svn/$source_shortname/trunk/assets/modules projects/$source_shortname
    else
        echo -e $c_info"Already checked out"$c_reset
    fi

    # Update the working copy for good measure
    svn update projects/$source_shortname

    # Restart the loop so you don't rsync source with source!
    continue
fi



# -------------------------------------------------------------------
# Every remaining line, CHECKOUT TARGET
# -------------------------------------------------------------------

# Increment the CSV line number (for indexing)
let "current_target_count++"

# Store semantic vars for the columns
target_shortname=$col_a
target_title=$col_b

# Log the current sync count and add a separator
echo -e $c_target\
"\n\
--------------------------------------------------------------------\n\
$c_reset[$current_target_count/$total_target_count] $c_target$target_shortname | $target_title$c_reset"


# If the project doesn't exist already, check out a working copy
if [ ! -d projects/$target_shortname ]; then
        echo -e $c_info"Checking out target project"$c_reset
        svn checkout https://svn.inkling.com/svn/$target_shortname/trunk/assets/modules projects/$target_shortname
else
    echo -e $c_info"Already checked out"$c_reset
fi

# Update the working copy for good measure
svn update projects/$target_shortname

#-------------------------------------------------------------------
# RUN the RSYNC
#-------------------------------------------------------------------

#-------------------------------------------------------------------
# Modify exclude list if non-existent
#-------------------------------------------------------------------
# Copy the source directory contents into the target directory
echo -e $c_reset"\nOverwriting contents of $c_info$directory$c_reset in" $c_target"$target_shortname$c_reset with "$c_source"$source_shortname"$c_reset

 if [ $rsync_delete = "TRUE" ]
 then
    rsync --delete --recursive --cvs-exclude projects/$source_shortname/ projects/$target_shortname
 else
    rsync --recursive --cvs-exclude projects/$source_shortname/ projects/$target_shortname
fi


#-------------------------------------------------------------------
# CLEAN local copy of TARGET for commiting
#-------------------------------------------------------------------

# Add any unversioned files (WARNING: this will add ignored files!)
printf $c_success
svn status projects/$target_shortname | grep ^\? | awk '{print $2}' | xargs svn add
printf $c_reset

# Delete any missing files
printf $c_error
svn status projects/$target_shortname | grep ^\! | awk '{print $2}' | xargs svn --force delete
printf $c_reset

fail_log_pre="Shortname,Project Title\n"$source_shortname,$source_title
#-------------------------------------------------------------------
# COMMIT new local changes in TARGET
#-------------------------------------------------------------------
echo -e $c_info"Commiting..."$c_reset
svn commit -m "Inkling module sync script" projects/$target_shortname

if [ ! "$?" == "0" ]; then
    echo -e $c_error"Error: "$c_reset$target_shortname$c_error" failed to commit. Added to $fail"
    fail_log_pre+="\n"$target_shortname,$target_title

    else
        echo -e $c_success"Done: "$c_reset$target_shortname$c_success" commited successfuly"
fi
# $? is the status of the last command. 0 === success, anything else === failure.

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

# Reset the internal field separator
IFS=$OLDIFS

# Log Errors to file
echo -e $fail_log_pre > $fail_log_file

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
