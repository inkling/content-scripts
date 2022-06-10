#!/bin/bash 


SVN_AUTH_OPTIONS="--username ${SVN_USERNAME} --password ${SVN_PASSWORD} --config-option servers:global:store-plaintext-passwords=yes --config-option servers:global:store-passwords=yes --config-option config:auth:password-stores=yes --non-interactive --trust-server-cert"

PROJECT="https://svn.inkling.com/svn/productdesign/trunk svnTestFolder"

svn checkout $SVN_AUTH_OPTIONS $PROJECT --depth empty
