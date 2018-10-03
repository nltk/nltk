#!/bin/bash

# This will fire a comment on Github after the build from pull-request builds in Travis.
# Note: this can be used in after_success but it's not used for anything now.
if [ "$TRAVIS_PULL_REQUEST" != "false" ] ; then
    curl -H "Authorization: token ${GITHUB_TOKEN}" -X POST \
    -d "{\"body\": \"<Some message>\"}" \
    "https://api.github.com/repos/${TRAVIS_REPO_SLUG}/issues/${TRAVIS_PULL_REQUEST}/comments"
fi
