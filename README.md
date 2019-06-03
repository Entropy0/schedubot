# schedubot
A simple scheduling bot for Telegram groups

## Dependencies
This program requires python-telegram-bot version 12.0.0b1. To install, do:
```
pip3 install python-telegram-bot==12.0.0b1 --upgrade
```
## Usage
```
./schedubot.py <TOKEN> (--debug)
```

Currently, the bot supports the following commands:

- /create Create a new poll.
- /add Add a poll you have created or participated in to current chat.
- /print Send a new message for a poll already added to this chat.
- /close Close a poll you created.
- /help Print this message.
- /reset Send this if the bot seems stuck or unresponsive.

If there are problems with voting, make sure the user has allowed this bot to contact him by sending it a /start in a direct message. This is due to Telegrams spam prevention and cannot be circumvented by us.