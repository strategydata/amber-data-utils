#!/bin/bash

git checkout -B release-next origin/master
git diff --quiet || { echo "Working directory is dirty, please commit or stash your changes."; exit 1; }
CURTAG=`git describe --abbrev=0 --tags`
CURTAG=${CURTAG:1}

IFS='.' read -a vers <<< "$CURTAG"

MAJ=${vers[0]}
MIN=${vers[1]}
BUG=${vers[2]}
MIN=$(($((MIN))+1))
BUG=0
NEWTAG="v$MAJ.$MIN.$BUG"
echo "CREATING TAG: $NEWTAG"
git tag -a $NEWTAG -m $NEWTAG
git push origin $(git describe --tags --abbrev=0)
git push origin release-next
