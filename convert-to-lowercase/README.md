# Convert Files and References to Lowercase

This shell script converts all filenames in a folder (and subfolders) to lowercase. Additionally, any references to the file will be replaced.

Based on example from:
http://stackoverflow.com/questions/17180580/how-to-create-a-bash-script-that-will-lower-case-all-files-in-the-current-folder

## Requirements

MacOSX (Windows users will need an application to run Shell scripts).

## Installation

Download the script and place it in your `/usr/local/bin` folder. If the folder does not exist or you have manually changed your PATH environment variable, use `echo $PATH` to print the location.

Run `chmod 755 /usr/local/bin/convertToLowercase.sh` to allow the script to be run without needing superadmin privelages.

Next, we'll set the locale in your bash profile so the string functions work as expected.

1. Open the terminal and rum `vim ~/.bash_profile` to open your profile.
2. Press `i` to enter INSERT mode
3. Paste the following lines into the file:
```
export LC_CTYPE=C
export LANG=C
```
4. Press `esc` to exit INSERT mode
5. Type `:wq` and press enter to save and quit vim
6. Run `source ~/.bash_profile` to reload your profile

You're now ready to run the script!

## Running the script

1. Open the folder you wish to run the script on in your terminal
2. Run `convertToLowercase.sh` which will change the case every filename and any references to that file in the folder

### Illegal byte error
If you see the error `sed: RE error: illegal byte sequence`, the LC_CTYPE locale has not been set. Review the installation instructions for setting the locale.


