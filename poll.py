#!/usr/bin/env python3.6

import builtins

import parser

from telegram import message, ParseMode, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

VERSION = 0.1

class Poll:

    def __init__(self, name, description, creator, days):

        self.version = VERSION
        self.users = []
        self.longest_user = 0
        self.single_votes = dict()
        self.name = name
        self.description = description
        self.creator = creator
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
            pass
        try:
            r += ", 'users': "        + repr(self.users)
        except AttributeError: 
            pass
        try:
            r += ", 'longest_user': " + repr(self.longest_user)
        except AttributeError: 
            pass
        try:
            r += ", 'single_votes': " + repr(self.single_votes)
        except AttributeError: 
            pass
        try:
            r += ", 'name': "         + repr(self.name)
        except AttributeError: 
            pass
        try:
            r += ", 'description': "  + repr(self.description)
        except AttributeError: 
            pass
        try:
            r += ", 'creator': "      + repr(self.creator)
        except AttributeError: 
            pass
        try:
            r += ", 'days': "         + repr(self.days)
        except AttributeError: 
            pass
        try:
            r += ", 'day_sum': "      + repr(self.day_sum)
        except AttributeError: 
            pass
        try:
            r += ", 'messages': "     + repr(self.messages)
        except AttributeError: 
            pass
        try:
            r += ", 'open': "         + repr(self.open)
        except AttributeError: 
            pass
        r += "}"
        return r

    def get_creator(self):
        return self.creator
    def get_name(self):
        return self.name
    def set_name(self, name):
        self.name = name
    def get_description(self):
        return self.description
    def set_description(self, name):
        self.description = description
    def get_days(self):
        return self.days
    def knows_msg(self, msg):
        return msg in self.messages
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

    def update(self):
        if self.open:
            for msg in self.messages:
                kbd = InlineKeyboardMarkup([[InlineKeyboardButton("vote", callback_data="vote")]])
                msg.edit_text(self.to_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)
        else:
            for msg in self.messages:
                msg.edit_text(self.to_text(), parse_mode=ParseMode.MARKDOWN)

    def update_or_print(self, bot, chat):
        if self.messages:
            self.update()
        else:
            self.print(bot, chat)

    def print(self, bot, chat, votable=True):
        if(self.open and votable):
            kbd = InlineKeyboardMarkup([[InlineKeyboardButton("vote", callback_data="vote")]])
            msg = bot.send_message(chat.id, self.to_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=kbd)
            self.add_msg(msg)
        else:
            msg = bot.send_message(chat.id, self.to_text(), parse_mode=ParseMode.MARKDOWN, reply_markup=None)
            self.add_msg(msg)


    def add_msg(self, msg):
        self.messages.append(msg)

    def close(self, user):
        if(user == self.creator):
            self.open = False
            self.update()
            return True
        else:
            return False