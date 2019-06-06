#!/usr/bin/env python3.6
"""Poll class used by Schedubot.

Attributes:
    VERSION (str): Version string
"""

from uuid import uuid4

import parser

from telegram import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup, error

VERSION = 0.3

class Poll:

    """Poll class used by Schedubot.
    
    Attributes:
        id (str): Uuid(4) of this poll.
        name (str): The name for this poll.
        days (int): Number of days/ columns.
        description (str): The description for this poll.
        creator_id (int): Id of the user that created the poll.
        open (bool): Whether votes can be cast for this poll.
        users (list of str): Every user that has voted on this poll.
        longest_user (int): Longest username's length.
        single_votes (dict of str: str): A list of every user's votes.
        day_sum (list of int): How many users voted '+' for any given day.
        messages (list of list of int): List of messages to keep track of.
            Contains the chat_id and message_id.
        version (str): The version of this file that created the poll.
    """
    
    def __init__(self, name, description, creator_id, days):
        """__init__
        
        Args:
            name (str): The name for this poll.
            description (str): The description for this poll.
            creator_id (int): Id of the user that created the poll.
            days (int): Number of days/ columns.
        """
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
        """__str__
        
        Returns:
            str: A string representing this poll.
        """
        return self.__repr__()
    def __repr__(self):
        """__repr__
        
        Returns:
            str: A string representing this poll.
        """
        representation = "{"
        try:
            representation += "'version': "        + repr(self.version)
        except AttributeError:
            representation += "'version': "        + "unknown"
        try:
            representation += ", 'users': "        + repr(self.users)
        except AttributeError:
            representation += ", 'users': "        + "unknown"
        try:
            representation += ", 'longest_user': " + repr(self.longest_user)
        except AttributeError:
            representation += ", 'longest_user': " + "unknown"
        try:
            representation += ", 'single_votes': " + repr(self.single_votes)
        except AttributeError:
            representation += ", 'single_votes': " + "unknown"
        try:
            representation += ", 'name': "         + repr(self.name)
        except AttributeError:
            representation += ", 'name': "         + "unknown"
        try:
            representation += ", 'description': "  + repr(self.description)
        except AttributeError:
            representation += ", 'description': "  + "unknown"
        try:
            representation += ", 'creator_if': "   + repr(self.creator_id)
        except AttributeError:
            representation += ", 'creator_id': "   + "unknown"
        try:
            representation += ", 'days': "         + repr(self.days)
        except AttributeError:
            representation += ", 'days': "         + "unknown"
        try:
            representation += ", 'day_sum': "      + repr(self.day_sum)
        except AttributeError:
            representation += ", 'day_sum': "      + "unknown"
        try:
            representation += ", 'messages': "     + repr(self.messages)
        except AttributeError:
            representation += ", 'messages': "     + "unknown"
        try:
            representation += ", 'open': "         + repr(self.open)
        except AttributeError:
            representation += ", 'open': "         + "unknown"
        representation += "}"
        return representation

    def get_id(self):
        """Getter for this poll's uuid.
        
        Returns:
            str: This poll's uuid.
        """
        return self.id
    def new_id(self):   # really?
        """Generate a new uuid for this poll.
        
        Returns:
            str: The new uuid.
        """
        self.id = str(uuid4())
        return self.id
    def get_creator_id(self):
        """Getter for this poll's creator_id.
        
        Returns:
            str: This poll's creator_id.
        """
        return self.creator_id
    def get_name(self):
        """Getter for this poll's name.
        
        Returns:
            str: This poll's name.
        """
        return self.name
    def set_name(self, name):
        """Setter for this poll's name.
        
        Args:
            name (str): The new name.
        """
        self.name = name
    def get_description(self):
        """Getter for this poll's description.
        
        Returns:
            str: This poll's description.
        """
        return self.description
    def set_description(self, description):
        """Setter for this poll's description.
        
        Args:
            description (str): The new description.
        """
        self.description = description
    def get_days(self):
        """Getter for this poll's days.
        
        Returns:
            str: This poll's days.
        """
        return self.days
    def knows_msg(self, msg):
        """Check whether the poll is tracking this message.
        
        Args:
            msg (list of int): The chat_id and message_id to check.
        
        Returns:
            bool: Whether the poll is tracking this message
        """
        return [msg.chat_id, msg.message_id] in self.messages
    def is_open(self):
        """Check whether votes can be cast for this poll.
        
        Returns:
            bool: Whether votes can be cast for this poll.
        """
        return self.open

    def vote(self, user, str_):
        """Add a user's vote to this poll.
        
        Args:
            user (str): The user who is casting his vote.
            str_ (str): The user's vote.
        """
        if not self.open:
            return
        if not user in self.users:
            self.users.append(user)
            if len(user) > self.longest_user:
                self.longest_user = len(user)
        self.single_votes[user] = parser.reduce(str_, self.days)

    def to_text(self):
        """Generate a tabulated view of the poll to show to users.
        
        Returns:
            str: A tabulated view of the poll to show to users.
        """
        out = f"<b>{parser.html_safe(self.name)}</b>{' (closed)' if not self.open else ''} ({self.days})\n{parser.html_safe(self.description)}\n<pre>\n"
        self.day_sum = [0] * self.days
        for user in self.users:
            user_htmlsafe = parser.html_safe(f'{user:{self.longest_user}}')
            out += f"{user_htmlsafe}: {parser.parse(self.single_votes[user])}\n"
            for i in range(self.days):
                if self.single_votes[user][i:i+1] == '+':
                    self.day_sum[i] += 1
        out += "\n"
        out += " " * (self.longest_user + 2) + parser.parse(self.day_sum) + "</pre>"
        return out

    def update(self, bot):
        """Update the messages the poll is keeping track of.
        
        Args:
            bot (telegram.Bot): The Bot used to update the messages.
        """
        if self.open:
            for msg in self.messages:
                kbd = InlineKeyboardMarkup([[InlineKeyboardButton("vote", url=f'{bot.get_me().link}?start={self.id}')]])
                try:
                    bot.edit_message_text(self.to_text(), chat_id=msg[0], message_id=msg[1], parse_mode=ParseMode.HTML, reply_markup=kbd)
                except error.BadRequest:
                    pass
        else:
            for msg in self.messages:
                try:
                    bot.edit_message_text(self.to_text(), chat_id=msg[0], message_id=msg[1], parse_mode=ParseMode.HTML)
                except error.BadRequest:
                    pass

    def print(self, bot, chat, votable=True):
        """Print the poll to a chat returns that message.
        
        Args:
            bot (telegram.Bot): The Bot used to send the message.
            chat (telegram.Chat): The Chat to print the message in.
            votable (bool, optional): Whether the message should include a "vote" button if it is votable.
        
        Returns:
            list of int: The message sent.
        """
        if(self.open and votable):
            kbd = InlineKeyboardMarkup([[InlineKeyboardButton("vote", url=f'{bot.get_me().link}?start={self.id}')]])
            msg = bot.send_message(chat.id, self.to_text(), parse_mode=ParseMode.HTML, reply_markup=kbd)
            self.add_msg([msg.chat_id, msg.message_id])
        else:
            msg = bot.send_message(chat.id, self.to_text(), parse_mode=ParseMode.HTML, reply_markup=None)
            self.add_msg([msg.chat_id, msg.message_id])
        return msg


    def add_msg(self, msg):
        """Add a message to keep track of.
        
        Args:
            msg (list of int): The message's chat_id and message_id.
        """
        self.messages.append(msg)

    def close(self, user_id, bot):
        """End voting on the poll.
        
        Args:
            user_id (int): The user trying to close the poll.
            bot (telegram.Bot): The Bot used to update the tracked messages.
        
        Returns:
            bool: Returns True on success, false on failure.
        """
        if user_id == self.creator_id:
            self.open = False
            self.update(bot)
            self.messages = []
            return True
        else:
            return False
