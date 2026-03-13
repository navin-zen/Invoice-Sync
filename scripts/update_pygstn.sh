#!/usr/bin/env bash
set -e

usage() {
cat <<EOF
    Usage: $0 new_commit_hash

    Updates the commit hash in requirements.in for local and lambda
    and generates the corresponding requirements.txt files.

    It should be executed from the root of the git repository.
EOF
}

if [ $# -ne 1 ]; then
    usage
    exit 1
fi

old_commit_hash=`cat utils/pygstn.version`
new_commit_hash=$1

set -x
sed -i "s/${old_commit_hash}/${new_commit_hash}/" utils/pygstn.version requirements.in requirements.txt
echo "Run the following command"
echo git add utils/pygstn.version requirements.in requirements.txt
