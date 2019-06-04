#!/usr/bin/env python3.6

from uuid import uuid4

import parser

from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, error

VERSION = 0.2

class Poll:

    def __init__(self, name, description, creator_id, days):

        self.version = VERSION
        self.users = []
        self.longest_user = 0
        self.single_votes = dict()
        self.name = name
        self.description = description
        self.creator_id = creator_id
        self.days = int(days)
        self.day_sum = [0] * self.days
        self.messages = []
        self.open = True
        self.id = str(uuid4())

    def __str__(self):
        return self.__repr__()
    def __repr__(self):
        r = "{"
        try:
            r += "'version': "        + repr(self.version)
        except AttributeError:
            r += "'version': "        + "unknown"
        try:
            r += ", 'users': "        + repr(self.users)
        except AttributeError:
            r += ", 'users': "        + "unknown"
        try:
            r += ", 'longest_user': " + repr(self.longest_user)
        except AttributeError:
            r += ", 'longest_user': " + "unknown"
        try:
            r += ", 'single_votes': " + repr(self.single_votes)
        except AttributeError:
            r += ", 'single_votes': " + "unknown"
        try:
            r += ", 'name': "         + repr(self.name)
        except AttributeError:
            r += ", 'name': "         + "unknown"
        try:
            r += ", 'description': "  + repr(self.description)
        except AttributeError:
            r += ", 'description': "  + "unknown"
        try:
            r += ", 'creator_if': "   + repr(self.creator_id)
        except AttributeError:
            r += ", 'creator_id': "   + "unknown"
        try:
            r += ", 'days': "         + repr(self.days)
        except AttributeError:
            r += ", 'days': "         + "unknown"
        try:
            r += ", 'day_sum': "      + repr(self.day_sum)
        except AttributeError:
            r += ", 'day_sum': "      + "unknown"
        try:
            r += ", 'messages': "     + repr(self.messages)
        except AttributeError:
            r += ", 'messages': "     + "unknown"
        try:
            r += ", 'open': "         + repr(self.open)
        except AttributeError:
            r += ", 'open': "         + "unknown"
        r += "}"
        return r

    def get_id(self):
        return self.id
    def new_id(self):   # really?
        self.id = str(uuid4())
        return self.id
    def get_creator_id(self):
        return self.creator_id
    def get_name(self):
        return self.name
    def set_name(self, name):
        self.name = name
    def get_description(self):
        return self.description
    def set_description(self, description):
        self.description = description
    def get_days(self):
        return self.days
    def knows_msg(self, msg):
        return [msg.chat_id, msg.message_id] in self.messages
    def is_open(self):
        return self.open

    def vote(self, user, st):
        if not self.open:
            return
        if not user in self.users:
            self.users.append(user)
            if len(user) > self.longest_user:
                self.longest_user = len(user)
        self.single_votes[user] = parser.reduce(st, self.days)

    def to_text(self):
        try:
            out = f"*{self.name}*{' (closed)' if not self.open else ''} ({self.days})\n{self.description}\n```\n"
        except AttributeError:
            self.description = ""
            out = f"*{self.name}* ({self.days})\n\n```\n"
        self.day_sum = [0] * self.days
        for user in self.users:
            out += f"{user:{self.longest_user}}: {parser.parse(self.single_votes[user])}\n"
            for i in range(self.days):
                if self.single_votes[user][i:i+1] == '+':
                    self.day_sum[i] += 1
        out += "\n"
        out += " " * (self.longest_user + 2) + parser.parse(self.day_sum) + "```"
        return out

    def update(self, bot):
        if self.open:
            for msg in self.messages:
                kbd = InlineKeyboardMarkup([[InlineKeyboardButton("vote", url=f'{bot.get_me().link}?start={self.id}')]])
                try:
                    bot.edit_message_text(self.to_text(), chat_id=msg[0], message_id=msg[1], parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)
                except error.BadRequest:
                    pass
        else:
            for msg in self.messages:
                try:
                    bot.edit_message_text(self.to_text(), chat_id=msg[0], message_id=msg[1], parse_mode=ParseMode.MARKDOWN)
                except error.BadRequest:
                    pass

    def update_or_print(self, bot, chat):
        if self.messages:
            self.update(bot)
        else:
            self.print(bot, chat)

    def print(self, bot, chat, votable=True):
        if(self.open and votable):
            kbd = InlineKeyboardMarkup([[InlineKeyboardButton("vote", url=f'{bot.get_me().link}?start={self.id}')]])
            msg = bot.send_message(chat.id, self.to_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)
            self.add_msg([msg.chat_id, msg.message_id])
        else:
            msg = bot.send_message(chat.id, self.to_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=None)
            self.add_msg([msg.chat_id, msg.message_id])
        return msg


    def add_msg(self, msg):
        self.messages.append(msg)

    def close(self, user_id, bot):
        if user_id == self.creator_id:
            self.open = False
            self.update(bot)
            self.messages = []
            return True
        else:
            return False
