# DeepCode Toolshed

This is a collection of simple tools done to interact with DeepCode's CLI or API.

#Suggestion to Jira

Simply Python script that takes a DeepCode CLI JSON output file as an input, uses the most severe Suggestion and generates a decorated JIRA ticket entry.

Needs:
+ An `app_confg` module which stores the secrets and some config - see source code of script for layout
+ Will clone the repo to pick needed source code as decoration
+ Runs on Windows as of now
+ `jira`and `git` libraries need to be handy

