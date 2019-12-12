#!/bin/bash

if [ "$TRAVIS_PULL_REQUEST" != "false" ] ; then
    curl -H "Authorization: token ${GITHUB_TOKEN}" -X POST \
    -d "{\"body\": \"[CI: retest]\"}" \
    "https://api.github.com/repos/${TRAVIS_REPO_SLUG}/issues/${TRAVIS_PULL_REQUEST}/comments"
