# An IRC bot for NBA stats

## Pre-reqs
We use pyenv so you don't need to have root access to manage your environment.
* pyenv https://github.com/pyenv/pyenv

## How to get started
This bot would probably work with other versions of python, but this one is known to work well.
1. `pyenv install 3.8.10`
2. from the cloned repository: `pyenv local 3.8.10`
3. `pyenv exec pip install --upgrade pip`
4. `pyenv exec pip install numpy irc3 nba-api`
5. `cd bot`
6. `cp config.ini yourbotname.ini`
7. Edit the `yourbotname.ini` file to change the bot name, server and default channels.
8. run `pyenv exec irc3 yourbotname.ini`

## Bot commands
Once your bot is up and running, type `-help` in the channel or via /msg to see the list of commands.
For help on a specific command, just type `-help <command>`

We use docopts (http://docopt.org/) to standardize the options for all commands.

## Potential Problems
If you are seeing timeout errors, it could be because `stats.nba.com` is blocking your provider. You have the option of changing to different providers or using a proxy. We will be adding configuration options for a proxy.

You can hack it by editing `~/.pyenv/versions/3.8.10/lib/python3.8/site-packages/nba_api/library/http.py`
and add the following to line 131:
```
proxies = {'http': 'http://user:pass@ip:port', 'https': 'http://user:pass@ip:port'} 
````
