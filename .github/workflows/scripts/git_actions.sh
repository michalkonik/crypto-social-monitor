#!/bin/bash

function git_push_changes(){
    git_output=$(mktemp)
    for i in $(seq 1 15); do
        git fetch --quiet
        git merge --no-edit --quiet
        git push origin --quiet &> $git_output
        if [ "$?" != "0" ]; then
            echo "Re-trying..."
            sleep 2
            continue
        else
            return 0
        fi
    done
    cat $git_output
    return 1
}

if [ $# -ne 1 ]; then
    echo "Usage: $0 <function_name>"
    exit 1
fi

case "$1" in
    initialize_git_credentials)
        initialize_git_credentials
        ;;
    git_push_changes)
        git_push_changes
        ;;
    *)
        echo "Unknown function: $1"
        exit 1
        ;;
esac
