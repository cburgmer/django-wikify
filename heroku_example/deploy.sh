#!/bin/sh

GIT_COMMIT_HASH=`git log | head -1 | sed "s/commit //"`

# Set-up heroku stuff
gem install heroku

echo "Host heroku.com" >> ~/.ssh/config
echo "   StrictHostKeyChecking no" >> ~/.ssh/config
echo "   CheckHostIP no" >> ~/.ssh/config
echo "   UserKnownHostsFile=/dev/null" >> ~/.ssh/config

heroku keys:clear
yes | heroku keys:add

# Prepare requirements for Heroku app
cat requirements.template | sed "s/\\\$GIT_COMMIT_HASH\\\$/$GIT_COMMIT_HASH/" > requirements.txt

# Receipt from http://stackoverflow.com/questions/7539382/how-can-i-deploy-from-a-git-subdirectory
git init
git add .
git commit -m "Git commit $GIT_COMMIT_HASH"
git remote add heroku git@heroku.com:django-wikify.git

# Merge with heroku copy
git pull heroku master
git checkout --ours .
git add -u
git commit -m "merged"

git push heroku master
rm -rf .git
