#!/usr/bin/env zsh

echo "LINE STATS"
echo "----------"
radon raw fancy_dataclass/**/*.py -s | tail -n 11 | head -n 7
