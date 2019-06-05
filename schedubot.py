#!/usr/bin/env python3.6
"""A simple scheduling bot for Telegram groups.

Attributes:
    VERSION (str): Version String.
"""

import sys, os
import argparse
import logging
import inspect, pprint
from codecs import open as copen
from datetime import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove

import poll
from states import States
from pollpicklepersistence import PollPicklePersistence

VERSION = "0.1.1"

class Schedubot():

    """A simple scheduling bot for Telegram groups.
    """

    def __init__(self, token, persistence, debug_file='schedubot_debug', **kwargs):
        """__init__

        Args:
            token (str): Token for the Telegram bot API.
            persistence (PollPicklePersistence): Handle persistence between restarts.
            debug_file (str, optional): Where to save debug output, if any.
            verbosity (int, optional): Logging level.
                Currently, INFO logs errors and DEBUG logs every update.
            **kwargs: Description
        """
        self.__verbosity = kwargs.get('verbosity', logging.INFO)
        self.__poll_data = persistence.get_poll_data()
        self.__debug_file = debug_file
        self.__persistence = persistence

        self.__updater = Updater(token, persistence=persistence, use_context=True)
        self.__dispatch = self.__updater.dispatcher

        self.__dispatch.add_handler(CommandHandler("start", self.__start))                       # *       --> DEFAULT
        self.__dispatch.add_handler(CommandHandler("init", self.__start))                        # *       --> DEFAULT
        self.__dispatch.add_handler(CommandHandler("help", self.__help))                         # *       --> *
        self.__dispatch.add_handler(CommandHandler("link", self.__link))                         # *       --> *
        self.__dispatch.add_handler(CommandHandler("create", self.__create))                     # DEFAULT --> TYPING_NAME
        self.__dispatch.add_handler(CommandHandler("vote", self.__vote))                         # *       --> TYPING_VOTE
        self.__dispatch.add_handler(CommandHandler("add", self.__add_poll_to_chat))              # DEFAULT --> CHOOSING_POLL_ADD
        self.__dispatch.add_handler(CommandHandler("print", self.__print_poll))                  # DEFAULT --> CHOOSING_POLL_PRINT
        self.__dispatch.add_handler(CommandHandler("close", self.__close))                       # DEFAULT --> CHOOSING_POLL_CLOSE
        self.__dispatch.add_handler(CommandHandler("desc", self.__edit_description))             # DEFAULT --> CHOOSING_POLL_EDIT_DESCRIPTION
        self.__dispatch.add_handler(CommandHandler("name", self.__edit_name))                    # DEFAULT --> CHOOSING_POLL_EDIT_NAME
        self.__dispatch.add_handler(CommandHandler("cancel", self.__reset))                      # *       --> DEFAULT
        self.__dispatch.add_handler(CommandHandler("reset", self.__reset))                       # *       --> DEFAULT

        self.__dispatch.add_handler(MessageHandler(Filters.text, self.__default_handler))

        self.__dispatch.add_error_handler(self.__error)

    def start(self):
        """Start polling.
        """
        self.__updater.start_polling()
        self.__updater.idle()


    def __log_update(self, update, context):
        """Log everything in an update.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.

        Returns:
            bool: Whether anything has actually been logged.
        """
        if self.__verbosity > logging.DEBUG:
            return False
        str_ = ""
        try:
            str_ += f"> {update.message.from_user.name} called {inspect.currentframe().f_back.f_code.co_name} by sending the following:\n"
            str_ += update.message.text
            str_ += "\n"
        except AttributeError:
            try:
                str_ += f"> {update.callback_query.from_user.name} called {inspect.currentframe().f_back.f_code.co_name} by clicking a button.\n"
            except AttributeError:
                str_ += f"> {update.effective_user.name} called {inspect.currentframe().f_back.f_code.co_name} via unknown means.\n"
        try:
            str_ += f"> (conversation_state: {context.user_data['conversation_state']} - {States(context.user_data['conversation_state'])})\n"
        except (KeyError, ValueError):
            str_ += f"> (conversation_state: unknown)\n"
        try:
            str_ += "\n> chat_data:\n"
            str_ += pprint.pformat(context.chat_data)
            str_ += "\n"
        except AttributeError:
            str_ += f"> Could not find chat_data.\n"
        try:
            str_ += "> user_data:\n"
            str_ += pprint.pformat(context.user_data)
            str_ += "\n"
        except AttributeError:
            str_ += f"> Could not find user_data.\n"
        str_ += "> self.__poll_data:\n"
        str_ += pprint.pformat(self.__poll_data)
        str_ += "\n"
        try:
            str_ += "> args:\n"
            str_ += pprint.pformat(context.args)
            str_ += "\n"
        except AttributeError:
            str_ += f"> Could not find args.\n"
        str_ += "> raw update:\n"
        str_ += str(update)
        str_ += "\n"
        self.__log_text(str_)
        return True

    def __log_error(self, update, error):
        """Log an error

        Args:
            update (telegram.Update): The update that triggered this action.
            error (Exception): The triggering error.
        """
        if self.__verbosity > logging.INFO:
            return
        str_ = f"> ERROR: {error}\n"
        str_ += f"> raw update:\n{str(update)}\n"
        self.__log_text(str_)

    def __log_text(self, str_):
        """Log arbitrary text

        Args:
            str_ (str): String to log.
        """
        if self.__verbosity > logging.INFO:
            return False
        with copen(self.__debug_file, 'a', 'utf-8') as dbf:
            dbf.write("\n" + "-"*24 + "\n")
            dbf.write(f">  {datetime.now()}\n")
            dbf.write(str_)
            dbf.write("\n\n\n")
        return True

    def __start(self, update, context):  # * --> DEFAULT
        """Start the conversation with the bot and/ or start voting.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if not 'polls' in context.user_data:
            context.user_data['polls'] = []
        if not 'polls' in context.chat_data:
            context.chat_data['polls'] = []
        try:
            self.__vote(update, context)
        except (AttributeError, IndexError):
            help(self, update, context)
            context.user_data['conversation_state'] = States.DEFAULT

    def __help(self, update, context):   # * --> *
        """Print the /help message.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        update.message.reply_text(f'Welcome to *schedubot* (v{VERSION})!\n\nCurrently, this bot supports the following commands:\n\n/create Create a new poll.\n/name Edit the name of one of your polls.\n/desc Edit the description of one of your polls.\n/add Add one of your polls or a poll you have participated in to a chat.\n/print Send a new message for a poll already added to this chat.\n/close Close one of your polls.\n/help Print this message.\n/reset Send this if the bot seems stuck or unresponsive.', parse_mode=ParseMode.MARKDOWN) #pylint: disable=line-too-long

    def __link(self, update, context):   # * --> *
        """Print this bot's t.me /link.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        update.message.reply_text(context.bot.get_me().link)

    def __reset(self, update, context):  # * --> DEFAULT
        """/reset the conversation state of a given user. Useful if the bot got stuck die to connectivity issues or something similar.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if 'active_poll' in context.user_data:
            _poll = self.__poll_data.get(context.user_data['active_poll'])
            if _poll:
                _poll.update(context.bot)
                self.__persistence.update_poll_data(_poll.id, _poll)
            del context.user_data['active_poll']
        context.user_data['conversation_state'] = States.DEFAULT
        if 'create_description' in context.user_data:
            del context.user_data['create_description']
        if 'create_length' in context.user_data:
            del context.user_data['create_length']
        if 'create_name' in context.user_data:
            del context.user_data['create_name']
        if 'prompt' in context.user_data:
            context.user_data['prompt'].delete()
            del context.user_data['prompt']
        context.bot.send_message(update.effective_user.id, "resetting...", reply_markup=ReplyKeyboardRemove(selective=True)).delete()

    def __cancel(self, update, context): # * --> DEFAULT
        """Synonym for /reset.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__reset(update, context)



    def __create(self, update, context):             # DEFAULT            --> TYPING_NAME
        """Start the /create chain.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == States.DEFAULT:
            self.__default_handler(update, context)
            return
        if update.effective_chat.type != "private":
            context.bot.send_message(update.message.from_user.id, "To reduce spam, please /create polls here first and then add them to your group(s).")
            context.user_data['conversation_state'] = States.DEFAULT
            return
        if not 'polls' in context.user_data:
            context.user_data['polls'] = []
        update.message.reply_text("Please enter the name for your poll:", reply_markup=ReplyKeyboardRemove(selective=True))
        context.user_data['conversation_state'] = States.TYPING_NAME

    def __create_name(self, update, context):        # TYPING_NAME        --> TYPING_LENGTH
        """Part of the /create chain. Get name.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        context.user_data['create_name'] = update.message.text
        update.message.reply_text("Please enter how many columns your poll should include:")
        context.user_data['conversation_state'] = States.TYPING_LENGTH

    def __create_length(self, update, context):      # TYPING_LENGTH      --> TYPING_DESCRIPTION
        """Part of the /create chain. Get length.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        context.user_data['create_length'] = update.message.text
        if(not context.user_data['create_length'].isdigit() or int(context.user_data['create_length']) <= 0):
            update.message.reply_text("Please enter a number.")
            return
        update.message.reply_text("Please enter a description for your poll:")
        context.user_data['conversation_state'] = States.TYPING_DESCRIPTION

    def __create_description(self, update, context): # TYPING_DESCRIPTION --> DEFAULT
        """Completes the /create chain. Get description.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        context.user_data['create_description'] = update.message.text
        new_poll = poll.Poll(context.user_data['create_name'], context.user_data['create_description'], \
            update.message.from_user.id, context.user_data['create_length'])
        while new_poll.get_id() in self.__poll_data: # UUID(4) collisions? Really?
            new_poll.new_id()
        self.__poll_data[new_poll.get_id()] = new_poll
        self.__persistence.update_poll_data(new_poll.get_id(), new_poll)

        context.user_data['polls'].append(new_poll.get_id())
        new_poll.print(context.bot, update.effective_chat)
        update.message.reply_text(f"Created poll named {context.user_data['create_name']} with {context.user_data['create_length']} columns.\nYou can now /add this poll to whichever chat(s) you want to use it in.", reply_markup=ReplyKeyboardRemove(selective=True)) #pylint: disable=line-too-long
        context.user_data['conversation_state'] = States.DEFAULT



    def __edit_name(self, update, context):        # DEFAULT                 --> CHOOSING_POLL_EDIT_NAME
        """Start the /edit chain.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == States.DEFAULT:
            self.__default_handler(update, context)
            return
        if update.effective_chat.type != "private":
            context.bot.send_message(update.message.from_user.id, "To reduce spam, please edit your polls here.")
            return
        if not 'polls' in context.user_data:
            context.user_data['polls'] = []
            context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
            return
        elif context.user_data['polls'] == []:
            context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
            return
        else:
            kbd = []
            for i in range(len(context.user_data['polls'])):
                _poll = self.__poll_data.get(context.user_data['polls'][i])
                if not _poll:
                    continue
                if _poll.get_creator_id() != update.message.from_user.id:
                    continue
                if not _poll.is_open():
                    continue
                kbd.append([f"{i}: {_poll.get_name()}"])
            if kbd == []:
                update.message.reply_text("You don't have any open polls.")
                return
            kbd.append(["/cancel"])
            context.user_data['prompt'] = update.message.reply_text("Which of your polls would you like to edit?", \
                reply_markup=ReplyKeyboardMarkup(kbd, resize_keyboard=True, one_time_keyboard=True, selective=True))
            context.user_data['conversation_state'] = States.CHOOSING_POLL_EDIT_NAME

    def __edit_name_choice(self, update, context): # CHOOSING_POLL_EDIT_NAME --> TYPING_POLL_EDIT_NAME
        """Part of the /edit chain. Get poll to be edited.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if not update.message.text.split(':')[0].isdigit():
            update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
            return
        i = int(update.message.text.split(':')[0])
        if i < len(context.user_data['polls']):
            _poll = self.__poll_data.get(context.user_data['polls'][i])
            if not _poll:
                update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
                return
            if _poll.get_creator_id() != update.message.from_user.id:
                update.message.reply_text(f"ERROR:\n{update.message.text} --- You don't have permission to modify that poll. Chose another one or /cancel.")
                return
            if 'prompt' in context.user_data:
                context.user_data['prompt'].delete()
                del context.user_data['prompt']
            context.user_data['active_poll'] = context.user_data['polls'][i]
            context.user_data['prompt'] = update.message.reply_text(f"What would you like the new name for {_poll.get_name()} to be?", \
                reply_markup=ReplyKeyboardRemove(selective=True))
            context.user_data['conversation_state'] = States.TYPING_POLL_EDIT_NAME
            return
        else:
            update.message.reply_text(f"ERROR:{update.message.text} --- No such poll. Chose another one or /cancel.")
            return

    def __edit_name_final(self, update, context):  # TYPING_POLL_EDIT_NAME   --> DEFAULT
        """Completes the /edit chain. Get new name.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        _poll = self.__poll_data.get(context.user_data['active_poll'])
        _poll.set_name(update.message.text)
        _poll.update(context.bot)
        self.__persistence.update_poll_data(_poll.id, _poll)
        del context.user_data['active_poll']
        context.user_data['prompt'].delete()
        del context.user_data['prompt']
        context.user_data['conversation_state'] = States.DEFAULT



    def __edit_description(self, update, context):        # DEFAULT                        --> CHOOSING_POLL_EDIT_DESCRIPTION
        """Start the /desc chain.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == States.DEFAULT:
            self.__default_handler(update, context)
            return
        if update.effective_chat.type != "private":
            context.bot.send_message(update.message.from_user.id, "To reduce spam, please edit your polls here.")
            return
        if not 'polls' in context.user_data:
            context.user_data['polls'] = []
            context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
            return
        elif context.user_data['polls'] == []:
            context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
            return
        else:
            kbd = []
            for i in range(len(context.user_data['polls'])):
                _poll = self.__poll_data.get(context.user_data['polls'][i])
                if not _poll:
                    continue
                if _poll.get_creator_id() != update.message.from_user.id:
                    continue
                if not _poll.is_open():
                    continue
                kbd.append([f"{i}: {_poll.get_name()}"])
            if kbd == []:
                update.message.reply_text("You don't have any open polls.")
                return
            kbd.append(["/cancel"])
            context.user_data['prompt'] = update.message.reply_text("Which of your polls would you like to edit?", \
                reply_markup=ReplyKeyboardMarkup(kbd, resize_keyboard=True, one_time_keyboard=True, selective=True))
            context.user_data['conversation_state'] = States.CHOOSING_POLL_EDIT_DESCRIPTION

    def __edit_description_choice(self, update, context): # CHOOSING_POLL_EDIT_DESCRIPTION --> TYPING_POLL_EDIT_DESCRIPTION
        """Part of the /desc chain. Get poll to be edited.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if not update.message.text.split(':')[0].isdigit():
            update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
            return
        i = int(update.message.text.split(':')[0])
        if i < len(context.user_data['polls']):
            _poll = self.__poll_data.get(context.user_data['polls'][i])
            if not _poll:
                update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
                return
            if _poll.get_creator_id() != update.message.from_user.id:
                update.message.reply_text(f"ERROR:\n{update.message.text} --- You don't have permission to modify that poll. Chose another one or /cancel.")
                return
            if 'prompt' in context.user_data:
                context.user_data['prompt'].delete()
                del context.user_data['prompt']
            context.user_data['active_poll'] = context.user_data['polls'][i]
            context.user_data['prompt'] = update.message.reply_text(f"What would you like the new description for {_poll.get_name()} to be?", \
                reply_markup=ReplyKeyboardRemove(selective=True))
            context.user_data['conversation_state'] = States.TYPING_POLL_EDIT_DESCRIPTION
            return
        else:
            update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Chose another one or /cancel.")
            return

    def __edit_description_final(self, update, context):  # TYPING_POLL_EDIT_DESCRIPTION   --> DEFAULT
        """Completes the /desc chain. Get new description.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        _poll = self.__poll_data.get(context.user_data['active_poll'])
        _poll.set_description(update.message.text)
        _poll.update(context.bot)
        self.__persistence.update_poll_data(_poll.id, _poll)
        del context.user_data['active_poll']
        context.user_data['prompt'].delete()
        del context.user_data['prompt']
        context.user_data['conversation_state'] = States.DEFAULT



    def __close(self, update, context):        # DEFAULT --> CHOOSING_POLL_CLOSE
        """Start the /close chain.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == States.DEFAULT:
            self.__default_handler(update, context)
            return
        if update.effective_chat.type != "private":
            context.bot.send_message(update.message.from_user.id, "To reduce spam, please /close your polls here.")
            return
        if not 'polls' in context.user_data:
            context.user_data['polls'] = []
            context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
            return
        elif context.user_data['polls'] == []:
            context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
            return
        else:
            kbd = []
            for i in range(len(context.user_data['polls'])):
                _poll = self.__poll_data.get(context.user_data['polls'][i])
                if not _poll:
                    continue
                if _poll.get_creator_id() != update.message.from_user.id:
                    continue
                kbd.append([f"{i}: {_poll.get_name()}\n"])
            if kbd == []:
                update.message.reply_text("You don't have any open polls.")
                return
            kbd.append(["/cancel"])
            context.user_data['prompt'] = update.message.reply_text("Which of your polls would you like to close?", \
                reply_markup=ReplyKeyboardMarkup(kbd, resize_keyboard=True, one_time_keyboard=True, selective=True))
            context.user_data['conversation_state'] = States.CHOOSING_POLL_CLOSE

    def __close_choice(self, update, context): # CHOOSING_POLL_CLOSE --> DEFAULT
        """Completes the /close chain. Get the poll to be closed.

        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if not update.message.text.split(':')[0].isdigit():
            update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
            return
        i = int(update.message.text.split(':')[0])
        if i < len(context.user_data['polls']):
            _poll = self.__poll_data.get(context.user_data['polls'][i])
            if not _poll:
                update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
                return
            if  _poll.get_creator_id() != update.message.from_user.id:
                update.message.reply_text(f"ERROR:\n{update.message.text} --- You don't have permission to close that poll. Chose another one or /cancel.")
                return
            if 'prompt' in context.user_data:
                context.user_data['prompt'].delete()
                del context.user_data['prompt']
            _poll.close(update.message.from_user.id, context.bot)
            self.__persistence.update_poll_data(_poll.id, _poll)
            update.message.reply_text("resetting...", reply_markup=ReplyKeyboardRemove(selective=True)).delete()
            context.user_data['conversation_state'] = States.DEFAULT
            return
        else:
            update.message.reply_text(f"ERROR:\n {update.message.text} --- No such poll. Chose another one or /cancel.")
            return



    def __add_poll_to_chat(self, update, context):        # DEFAULT --> CHOOSING_POLL_ADD
        """Start the /add chain.
        
        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == States.DEFAULT:
            self.__default_handler(update, context)
            return
        if update.effective_chat.type == "private":
            update.message.reply_text("Cannot add polls to private chats. Try adding a poll to a group or channel instead.")
            return
        if not 'polls' in context.chat_data:
            context.chat_data['polls'] = []
        if not 'polls' in context.user_data:
            context.user_data['polls'] = []
            context.bot.send_message(update.message.from_user.id, "You don't have any open polls.\nDo you want to /create a new one?")
            return
        elif context.user_data['polls'] == []:
            context.bot.send_message(update.message.from_user.id, "You don't have any open polls.\nDo you want to /create a new one?")
            return
        else:
            kbd = []
            for i in range(len(context.user_data['polls'])):
                _poll = self.__poll_data.get(context.user_data['polls'][i])
                if not _poll:
                    continue
                kbd.append([f"{i}: {_poll.get_name()}\n"])
            kbd.append(["/cancel"])
            context.user_data['prompt'] = update.message.reply_text("Which poll would you like to add to this chat?", \
                reply_markup=ReplyKeyboardMarkup(kbd, resize_keyboard=True, one_time_keyboard=True, selective=True))
            context.user_data['conversation_state'] = States.CHOOSING_POLL_ADD
            return

    def __add_poll_to_chat_choice(self, update, context): # CHOOSING_POLL_ADD --> DEFAULT
        """Completes the /add chain. Get poll to be added.
        
        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if not update.message.text.split(':')[0].isdigit():
            update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
            return
        i = int(update.message.text.split(':')[0])
        if i < len(context.user_data['polls']):
            if not context.user_data['polls'][i] in context.chat_data['polls']:
                context.chat_data['polls'].append(context.user_data['polls'][i])
            _poll = self.__poll_data.get(context.user_data['polls'][i])
            if not _poll:
                update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
                return
            _poll.print(context.bot, update.effective_chat)
            self.__persistence.update_poll_data(_poll.id, _poll)
            if 'prompt' in context.user_data:
                context.user_data['prompt'].delete()
                del context.user_data['prompt']
            update.message.reply_text("resetting...", reply_markup=ReplyKeyboardRemove(selective=True)).delete()
            context.user_data['conversation_state'] = States.DEFAULT
            return
        else:
            update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
            return



    def __print_poll(self, update, context):        # DEFAULT --> CHOOSING_POLL_PRINT
        """Start the /print chain.
        
        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == States.DEFAULT:
            self.__default_handler(update, context)
            return
        if update.effective_chat.type == "private":
            if not 'polls' in context.user_data:
                context.user_data['polls'] = []
                context.bot.send_message(update.message.from_user.id, "You are not part of any open polls.\nDid you want to /create a new one?")
                return
            if context.user_data['polls'] == []:
                context.bot.send_message(update.message.from_user.id, "You are not part of any open polls.\nDid you want to /create a new one?")
                return
            data = context.user_data
        else:
            if not 'polls' in context.chat_data:
                context.chat_data['polls'] = []
                context.bot.send_message(update.message.from_user.id, "There are no open polls in that chat.\nDid you mean to /add one?")
                return
            if context.chat_data['polls'] == []:
                context.bot.send_message(update.message.from_user.id, "There are no open polls in that chat.\nDid you mean to /add one?")
                return
            data = context.chat_data
        kbd = []
        for i in range(len(data['polls'])):
            _poll = self.__poll_data.get(data['polls'][i])
            if not _poll:
                continue
            kbd.append([f"{i}: {_poll.get_name()}\n"])
        if kbd == []:
            context.bot.send_message(update.message.from_user.id, "There are no open polls in that chat.\nDid you mean to /add one?")
            return
        kbd.append(["/cancel"])
        update.message.reply_text("Which poll would you like to print again?", reply_markup=ReplyKeyboardMarkup(kbd, resize_keyboard=True, \
            one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = States.CHOOSING_POLL_PRINT

    def __print_poll_choice(self, update, context): # CHOOSING_POLL_PRINT --> DEFAULT
        """Complete the /print chain. Get poll to be printed.
        
        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if update.effective_chat.type == "private":
            data = context.user_data
        else:
            data = context.chat_data
        if not update.message.text.split(':')[0].isdigit():
            update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
            return
        i = int(update.message.text.split(':')[0])
        if i < len(data['polls']):
            _poll = self.__poll_data.get(data['polls'][i])
            if not _poll:
                update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
                return
            _poll.print(context.bot, update.effective_chat)
            self.__persistence.update_poll_data(_poll.id, _poll)
            update.message.reply_text("resetting...", reply_markup=ReplyKeyboardRemove(selective=True)).delete()
            context.user_data['conversation_state'] = States.DEFAULT
            return
        else:
            update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
            return



    def __vote(self, update, context):
        """Start the vote chain.
        
        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if update.effective_chat.type != "private":
            self.__default_handler(update, context)
            return
        poll_id = context.args[0]
        _poll = self.__poll_data.get(poll_id)
        if not _poll:
            context.bot.send_message(update.effective_user.id, "Sorry, something went wrong. Try adding the poll to the chat again.")
            self.__reset(update, context)
            return
        if not 'polls' in context.user_data:
            context.user_data['polls'] = []
        if not poll_id in context.user_data['polls']:
            context.user_data['polls'].append(poll_id)
        _poll.print(context.bot, update.effective_chat, votable=False)
        self.__persistence.update_poll_data(_poll.id, _poll)
        prompt = context.bot.send_message(update.effective_user.id, f"Please enter your votes for \"{_poll.get_name()}\":\n\n(Write a '+' for a column you want to agree to, a '-' for one you disagree with or a '?' for one you are not sure about. Everything alse gets ignored. Omitting votes will fill the remainder with '?'s, superfluous votes are discarded.\nYou can always correct your vote as long as the poll is still open.\n/cancel to cancel voting") #pylint: disable=line-too-long
        context.user_data['active_poll'] = poll_id
        context.user_data['prompt'] = prompt
        context.user_data['conversation_state'] = States.TYPING_VOTE
        return

    def __vote_enter(self, update, context): # TYPING_VOTE --> DEFAULT
        """Complete the vote chain. Get votes to cast.
        
        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        if update.effective_chat.type == "private":
            if 'active_poll' in context.user_data:
                _poll = self.__poll_data.get(context.user_data['active_poll'])
                if not _poll:
                    context.bot.send_message(update.effective_user.id, "Sorry, something went wrong. Try adding the poll to the chat again.")
                    self.__reset(update, context)
                    return
                _poll.vote(update.message.from_user.name, update.message.text)
                _poll.update(context.bot)
                self.__persistence.update_poll_data(_poll.id, _poll)
                del context.user_data['active_poll']
                context.user_data['prompt'].delete()
                del context.user_data['prompt']
                context.user_data['conversation_state'] = States.DEFAULT
                return
            else:
                self.__reset(update, context)
                return
        else:
            if 'active_poll' in context.user_data:
                context.user_data['prompt'].delete()
                _poll = self.__poll_data.get(context.user_data['active_poll'])
                if not _poll:
                    context.bot.send_message(update.effective_user.id, "Sorry, something went wrong. Try adding the poll to the chat again.")
                    self.__reset(update, context)
                    return
                context.user_data['prompt'] = context.bot.send_message(update.effective_user.id, f"Please enter your votes for \"{_poll.get_name()}\":\n\n(Write a '+' for a column you want to agree to, a '-' for one you disagree with or a '?' for one you are not sure about. Everything alse gets ignored. Omitting votes will fill the remainder with '?'s, superfluous votes are discarded.\nYou can always correct your vote as long as the poll is still open.\n/cancel to cancel voting") #pylint: disable=line-too-long
                context.user_data['conversation_state'] = States.TYPING_VOTE
                return
            else:
                self.__reset(update, context)
                return



    def __default_handler(self, update, context):
        """Determine which handler to call depending on conversation state.
        
        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_update(update, context)
        if 'conversation_state' in context.user_data:
            switch = {
                States.TYPING_NAME:                    self.__create_name,
                States.TYPING_LENGTH:                  self.__create_length,
                States.TYPING_DESCRIPTION:             self.__create_description,
                States.CHOOSING_POLL_ADD:              self.__add_poll_to_chat_choice,
                States.CHOOSING_POLL_CLOSE:            self.__close_choice,
                States.CHOOSING_POLL_PRINT:            self.__print_poll_choice,
                States.CHOOSING_POLL_EDIT_NAME:        self.__edit_name_choice,
                States.TYPING_POLL_EDIT_NAME:          self.__edit_name_final,
                States.CHOOSING_POLL_EDIT_DESCRIPTION: self.__edit_description_choice,
                States.TYPING_POLL_EDIT_DESCRIPTION:   self.__edit_description_final,
                States.TYPING_VOTE:                    self.__vote_enter,
                States.DEFAULT:                        self.__help
            }
            func = switch.get(context.user_data['conversation_state'], self.__help)
            func(update, context)
            return
        else:
            context.user_data['conversation_state'] = States.DEFAULT
            return



    def __error(self, update, context):
        """Log any error that the dispatcher can catch.
        
        Args:
            update (telegram.Update): The update that triggered this action.
            context (telegram.ext.CallbackContext): Context for this update.
        """
        self.__log_error(update, context.error)


def main():
    """Initiate and start a bot.
    """
    myself = sys.argv[0]
    if myself[-3:] == '.py':
        myself = myself[:-3]
    parser = argparse.ArgumentParser(description="A simple scheduling bot for Telegram groups\n\nExpects your bot API token in an environment variable called SCHEDUBOT_TOKEN", formatter_class=argparse.RawTextHelpFormatter) #pylint: disable=line-too-long
    parser.add_argument("--debug", help="Log every update.", action='store_true')
    parser.add_argument("--version", help="Show version information and exit.", action='version', version=VERSION)
    parser.add_argument("--logfile", help=f"Where to store debugging info. Defaults to {myself}_debug.", \
        default=f'{sys.argv[0]}_debug')
    parser.add_argument("--savefile", help=f"Where to store data neccesary for persistence. Defaults to {myself}_persistence.", \
        default=f'{sys.argv[0]}_persistence')
    args = parser.parse_args()
    try:
        token = os.environ['SCHEDUBOT_TOKEN']
    except KeyError:
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    if args.debug:
        verbosity = logging.DEBUG
    else:
        verbosity = logging.INFO

    persistence = PollPicklePersistence(filename=args.savefile)

    schedubot = Schedubot(token, persistence, args.logfile, verbosity=verbosity)
    schedubot.start()



if __name__ == '__main__':
    main()
