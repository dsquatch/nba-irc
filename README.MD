# An IRC bot for NBA stats

## Pre-reqs
* python
* pyenv
* pip

## How to get started
1. `pyenv install 3.8.10`
2. from the cloned repository: `pyenv local 3.8.10`
3. `pyenv exec pip install --upgrade pip`
4. `pyenv exec pip install irc3`
5. `pyenv exec pip install nba-api`
6. `cd bot`
7. Edit the `config.ini` file to change the bot name, server and default channels.
8. run `pyenv exec irc3 config.ini`

