# DeepCode Toolshed - suggestion_to_jira
# Author - @cu-0xff
# Sample application using DeepCode CLI to generate suggestions, picking top severe suggestion and generate JIRA ticket

# Library GitPython from here https://gitpython.readthedocs.io/en/stable/tutorial.html#meet-the-repo-type
# Library JIRA from here https://jira.readthedocs.io/en/master/index.html
# See https://blog.softhints.com/request-jira-api-with-python-examples/
# DeepCode CLI from here https://pypi.org/project/deepcode/

import os
import json
import pathlib
import copy
import sys

from jira import JIRA
from git import Repo

import urllib.parse

#Separate secrets into different module
from app_config.Configuration import Configuration

"""
The configuration is a simple data structure

class Configuration:
    Jira = {
        'host' : 'http://192.168.0.6:8080',
        'user' : 'frank',
        'token' : '...',
        'project' : 'demo'
    }
    Git = {
        'repo_url' : 'https://github.com/CU-0xff/deepcode-vuln-logviewer.git',
        'user' : 'cu-0xff',
        'branch' : 'master',
        'repo_dir' : 'e:/temp/cloned_temp'
    }

"""

config = Configuration()

# Helper functions

def log_error(msg):
    print("Fatal Error: {msg}".format(msg=msg))

def log_msg(msg):
    print(msg)

def load_demo_json():
    app_path = os.path.split(os.path.abspath(__file__))[0]
    print(app_path)
    with open(app_path+'\\demo_output.json') as f:
        data = json.load(f)
    return data

def load_json(filename):
    try:
        with open(filename) as f:
            data = json.load(f)
        return data
    except:
        log_error("Something is wrong with the input file")
        sys.exit(1)

def read_file(filename):
    with open(filename) as f:
        content = f.readlines()
    return content

def retrieve_top_suggestion(suggestions):
    files = []
    try:
        # Flatten the data
        for file in suggestions['results']['files']:
            file_entry = suggestions['results']['files'][file]
            for suggestion in suggestions['results']['files'][file]:
                temp_body = copy.deepcopy(file_entry[suggestion])[0]            
                temp_body["suggestion"] = suggestions['results']['suggestions'][suggestion]
                temp_body["file"] = file
                files.append(temp_body)
        # Search for highest severity
        selected_file = {}
        highest_severity = 0
        for file in files:
            if file['suggestion']['severity'] > highest_severity:
                selected_file = file
    except:
        log_error("Something is wrong with the input file")
        os._exit(1)
    return selected_file

def decorate_source(sourcecode):
    decorated_text = []
    line_counter = 1
    for line in sourcecode:
        #Add line numbers
        new_line = "{Line}:{code}".format(Line=line_counter, code=line)
        decorated_text.append(new_line)
        line_counter += 1
    return decorated_text

def generate_source_excerpt(Row_Start, Row_End, sourcecode):
    TheStart = int(Row_Start) - 5
    if TheStart < 0: 
        TheStart = 0
    TheEnd = int(Row_End) + 5
    if TheEnd > len(sourcecode): 
        TheEnd = len(sourcecode)
    return "".join(sourcecode[TheStart:TheEnd])

def generate_Markers(top_suggestion):
    #Transform markers into list of data entries for easier access plus have a MarkerId
    Markers = []
    MarkerId = 0
    for Marker in top_suggestion['markers']:
        msg = (Marker['msg'][0], Marker['msg'][1])
        col = (Marker['pos'][0]['cols'][0], Marker['pos'][0]['cols'][1])
        row = (Marker['pos'][0]['rows'][0], Marker['pos'][0]['rows'][1])
        newMarker = [MarkerId, msg, col, row]
        Markers.append(newMarker)
        MarkerId += 1
    return Markers

def generate_Suggestion_Text(TopSuggestion, Markers):
    SuggestionText = TopSuggestion['suggestion']['message']
    Markers.sort(key=lambda tup: tup[1][0], reverse=True)
    for Marker in Markers:
        SuggestionText = "{Prelude}({id}) [{Highlight}|#Msg{id}]{Rest}".format(Prelude=SuggestionText[:Marker[1][0]], id=str(Marker[0]), Highlight=SuggestionText[Marker[1][0]:Marker[1][1]+1], Rest=SuggestionText[Marker[1][1]+1:])
    return SuggestionText

def generate_Code_Text(Marker, sourcecode):
    Output = "{{anchor:Msg{id}}}({id}) Code - refer to line {start} to {stop} \n".format(id=Marker[0], start=Marker[3][0], stop=Marker[3][1])
    Output += "{{code}}\n{code}\n{{code}}\n\n".format(code=generate_source_excerpt(Marker[3][0], Marker[3][1], sourcecode))
    return Output

def generate_Jira_Text(TopSuggestion, sourcecode):
    Output = "*Repository:* {repo}\n".format(repo=config.Git['repo_url'])
    Output += "*File:* {file}\n\n".format(file=TopSuggestion['file'])
    Markers = generate_Markers(TopSuggestion)
    Output += "*Suggestion:* {suggestion}\n\n".format(suggestion=generate_Suggestion_Text(TopSuggestion, Markers))
    Markers.sort(key=lambda tup: tup[1][0])
    for Marker in Markers:
        Output += generate_Code_Text(Marker, sourcecode)
    return Output    



##### MAIN #####

log_msg("**** Suggestion to Jira ****")

if not(len(sys.argv)==2):
    log_error("Need filename as argument")
    sys.exit(1) 


log_msg("Connecting to Jira")
try:
    jira = JIRA(config.Jira['host'], basic_auth=(config.Jira['user'], config.Jira['token']))
except:
    log_error("Problems with JIRA")
    sys.exit(1)

# Clean up before

log_msg("Cleaning temp directory")
repo_path = pathlib.Path(config.Git['repo_dir'])
if repo_path.exists:
    os.system("rd /s /Q {dir}".format(dir=pathlib.PureWindowsPath(repo_path)))

# - get checks from DC in
log_msg("Loading Suggestion JSON")
#dc_suggestions = load_demo_json()
dc_suggestions = load_json(sys.argv[1])
top_suggestion = retrieve_top_suggestion(dc_suggestions)

# - get source code from Git
log_msg("Downloading repo to retrieve source")
Repo.clone_from(url=config.Git['repo_url'], to_path=config.Git['repo_dir'], branch=config.Git['branch'] )
sourcecode = read_file(config.Git['repo_dir'] + top_suggestion['file'])
sourcecode = decorate_source(sourcecode)

# - get decoration text
jiraText = "h1. DeepCode Scan - Automatically Generated Ticket\n\n{msg}".format(msg=generate_Jira_Text(top_suggestion, sourcecode))

# - generate Jira ticket
issue_dict = {
    'project': 'DEMO',
    'summary': 'DeepCode - {Suggestion}'.format(Suggestion=urllib.parse.unquote(top_suggestion["suggestion"]["id"])),
    'description': jiraText,
    'issuetype': {'name': 'Bug'},
}


new_issue = jira.create_issue(fields=issue_dict)

log_msg("New jira issue created {issueid}".format(issueid=new_issue.key))


#Clean up after
log_msg("Cleanup...")
os.system("rd /s /Q {dir}".format(dir=pathlib.PureWindowsPath(repo_path)))