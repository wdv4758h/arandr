#!/bin/sh

set -e

for t in "$@"
do
	echo --$t--
	PATH=$t:$PATH python3 -m screenlayout.executions.run --zip-out $t/output.zip --zip-out-stateless --shell --verbose --ignore-errors "xrandr --query --verbose" "xrandr --help" "xrandr --version"
done
