#!/bin/sh

set -e

for t in `git tag |grep ^xrandr`
do
git checkout $t
git reset --hard
git clean -fx
mkdir -p $t
echo "building $t"
./autogen.sh > $t/autogen.out 2> $t/autogen.err
make xrandr > $t/make.out
mv xrandr $t/
done
