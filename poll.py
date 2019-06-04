#!/usr/bin/env python3.6

import builtins
import pickle, base64

import parser

from telegram import message, ParseMode, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

VERSION = 0.2

class protoPoll:
    def __init__(self, name, description, creator_id, days, messages, single_votes):
        self.n = name
        self.de = description
        self.c = creator_id
        self.d = days
        self.m = messages
        self.s = single_votes

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
            r += ", 'longest_user': " + repr(self.longest_user)
        except AttributeError: 
            r += ", 'longest_user': " + "unknown"
        try:
            r += ", 'single_votes': " + repr(self.single_votes)
        except AttributeError: 
            r += ", 'single_votes': " + "unknown"
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

    def encode(self):
        proto_self = protoPoll( self.name, self.description, self.creator_id, self.days, self.messages, self.single_votes)
        serialized = base64.urlsafe_b64encode(pickle.dumps(proto_self))
        return serialized

    @classmethod
    def decode(_class, serialized):
        proto = pickle.loads(base64.urlsafe_b64decode(serialized))
        _poll = _class(proto.n, proto.de, proto.c, proto.d)
        for msg in proto.m:
            _poll.add_msg(msg)
        for u, v in proto.s.items():
            _poll.vote(u,v)
        return _poll



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

    def vote(self, user, str):
        if(not self.open):
            return False
        if(not(user in self.users)):
            self.users.append(user)
            if(len(user)>self.longest_user):
                self.longest_user = len(user)
        self.single_votes[user] = parser.reduce(str, self.days)

    def to_text(self):
        try:
            out = f"*{self.name}* ({self.days})\n{self.description}\n```\n"
        except AttributeError:
            self.description = ""
            out = f"*{self.name}* ({self.days})\n\n```\n"
        self.day_sum = [0] * self.days
        for user in self.users:
            out += f"{user:{self.longest_user}}: {parser.parse(self.single_votes[user])}\n"
            for i in range(self.days):
                if(self.single_votes[user][i:i+1]=='+'):
                    self.day_sum[i] += 1
        out += "\n"
        out += " " * (self.longest_user + 2) + parser.parse(self.day_sum) + "```"
        return out

    def update(self, bot):
        if self.open:
            for msg in self.messages:
                kbd = InlineKeyboardMarkup([[InlineKeyboardButton("vote", url=msg.from_user.link + "?/help")]])
                bot.edit_message_text(msg[0], msg[1], self.to_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)
        else:
            for msg in self.messages:
                bot.edit_message_text(msg[0], msg[1], self.to_text(), parse_mode=ParseMode.MARKDOWN)

    def update_or_print(self, bot, chat):
        if self.messages:
            self.update(bot)
        else:
            self.print(bot, chat)

    def print(self, bot, chat, votable=True):
        if(self.open and votable):
            kbd = InlineKeyboardMarkup([[InlineKeyboardButton("vote", url=bot.get_me().link + "?/help")]])
            msg = bot.send_message(chat.id, self.to_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)
            self.add_msg([msg.chat_id, msg.message_id])
        else:
            msg = bot.send_message(chat.id, self.to_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=None)
            self.add_msg([msg.chat_id, msg.message_id])


    def add_msg(self, msg):
        self.messages.append(msg)

    def close(self, user_id, bot):
        if(user_id == self.creator_id):
            self.open = False
            self.update(bot)
            return True
        else:
            return False