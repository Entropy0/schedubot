# schedubot
A simple scheduling bot for Telegram groups

## Dependencies
This program requires python-telegram-bot version 12.0.0b1. To install, do:
```
pip3 install python-telegram-bot==12.0.0b1 --upgrade
```
## Usage
```
schedubot.py [-h] [--debug] [--version] [--logfile LOGFILE] [--savefile SAVEFILE]


Expects your bot API token in an environment variable called SCHEDUBOT_TOKEN

optional arguments:
  -h, --help           show this help message and exit
  --debug              Log every update.
  --version            Show version information and exit.
  --logfile LOGFILE    Where to store debugging info. Defaults to ./schedubot_debug.
  --savefile SAVEFILE  Where to store data neccesary for persistence. Defaults to ./schedubot_persistence.

```

Currently, the bot supports the following commands:

- /create Create a new poll.
- /name Edit the name of one of your polls.
- /desc Edit the description of one of your polls.
- /add Add one of your polls or a poll you have participated in to a chat.
- /print Send a new message for a poll already added to this chat.
- /close Close one of your polls.
- /help Print this message.
- /reset Send this if the bot seems stuck or unresponsive.