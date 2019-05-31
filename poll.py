#!/usr/bin/python3

import builtins

import parser

from telegram import message, ParseMode, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

class Poll:

    def __init__(self, name, creator, days):

        self.users = []
        self.longest_user = 0
        self.single_votes = dict()
        self.name = name
        self.creator = creator
        self.days = int(days)
        self.day_sum = [0] * self.days
        self.messages = []
        self.open = True

    def get_creator(self):
        return self.creator
    def get_name(self):
        return self.name
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