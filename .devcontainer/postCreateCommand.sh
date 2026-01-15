#!/bin/bash

set -e

echo 'Setting up Poetry auth for private registry...'
poetry config http-basic.fury ${FURY_SECRET} NOPASS

echo 'Setting up SSH agent and adding SSH key...'
if [ -z "$SSH_AUTH_SOCK" ]; then
    echo 'Starting SSH agent...'
    eval "$(ssh-agent -s)"
fi

ssh-add
