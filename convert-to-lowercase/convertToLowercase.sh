#!/bin/bash
find . -type f -name '*' -print0 | while IFS= read -r -d '' file; do
#Check to see if the filename contains any uppercase characters
    oldfilename=$(basename $file)
    iscap=`echo $oldfilename | awk '{if ($0 ~ /[[:upper:]]/) print }'`
    if [[ -n $iscap ]]
    then
#If the filename contains upper case characters convert them to lower case
        newname=`echo $oldfilename | tr '[A-Z]' '[a-z]'` #make lower case
#Rename file
        newpathandfile=$(dirname $file)/$newname
        echo "Moving $file"
        echo "To $newpathandfile"
        echo ""
        mv $file $newpathandfile
#Update all references to the new filename in all listed filetypes
        find . -type f \( -name "*.js" -o -name "*.json" -o -name "*.css" -o -name "*.scss" -o -name "*.html" -o -name "*.xhtml" -o -name "*.xml" \) -print0 | while IFS= read -r -d '' thisfile; do
            sed -i '' -e "s/$oldfilename/$newname/g" $thisfile
            echo "$thisfile s/$oldfilename/$newname/g"
        done
    fi
done
