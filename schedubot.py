#!/usr/bin/env python3.6

import sys
import pickle
import logging
import inspect, pprint

import parser, poll

from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, Filters, PicklePersistence
from telegram import ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove, Chat, ForceReply
from codecs import open
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

PERSISTENCE_FILE = 'schedubot_persistence'

DEBUG = False
DEBUG_FILE = 'schedubot_debug'

DEFAULT = -1
TYPING_NAME, TYPING_LENGTH, TYPING_DESCRIPTION, CHOOSING_POLL_ADD, CHOOSING_POLL_CLOSE, CHOOSING_POLL_PRINT, CHOOSING_POLL_EDIT_NAME, TYPING_POLL_EDIT_NAME, CHOOSING_POLL_EDIT_DESCRIPTION, TYPING_POLL_EDIT_DESCRIPTION, TYPING_VOTE = range(11)
states = {
    TYPING_NAME:                    "TYPING_NAME", 
    TYPING_LENGTH:                  "TYPING_LENGTH", 
    TYPING_DESCRIPTION:             "TYPING_DESCRIPTION",
    CHOOSING_POLL_ADD:              "CHOOSING_POLL_ADD",
    CHOOSING_POLL_CLOSE:            "CHOOSING_POLL_CLOSE",
    CHOOSING_POLL_PRINT:            "CHOOSING_POLL_PRINT",
    CHOOSING_POLL_EDIT_NAME:        "CHOOSING_POLL_EDIT_NAME",
    TYPING_POLL_EDIT_NAME:          "TYPING_POLL_EDIT_NAME",
    CHOOSING_POLL_EDIT_DESCRIPTION: "CHOOSING_POLL_EDIT_DESCRIPTION",
    TYPING_POLL_EDIT_DESCRIPTION:   "TYPING_POLL_EDIT_DESCRIPTION",
    TYPING_VOTE:                    "TYPING_VOTE",
    DEFAULT:                        "DEFAULT"
}

def log_update(update, context):
    if not DEBUG:
        return False
    with open(DEBUG_FILE, 'a', 'utf-8') as dbf:
        dbf.write("\n" + "-"*24 + "\n")
        dbf.write(f">  {datetime.now()}\n")
        try:
            dbf.write(f"> {update.message.from_user.name} called {inspect.currentframe().f_back.f_code.co_name} by sending the following:\n")
            dbf.write(update.message.text)
        except AttributeError:
            try:
                dbf.write(f"> {update.callback_query.from_user.name} called {inspect.currentframe().f_back.f_code.co_name} by clicking a button.\n")
            except AttributeError:
                dbf.write(f"> {update.effective_user.name} called {inspect.currentframe().f_back.f_code.co_name} via unknown means.\n")
        try:
            dbf.write(f"\n> (conversation_state: {context.user_data['conversation_state']} - {states.get(context.user_data['conversation_state'], 'unknown')})\n")
        except KeyError:
            dbf.write(f"\n> (conversation_state: unknown)\n")
        try:
            dbf.write("\n> chat_data:\n")
            dbf.write(pprint.pformat(context.chat_data))
        except AttributeError:
            dbf.write(f"\n> Could not find chat_data.")
        try:
            dbf.write("\n> user_data:\n")
            dbf.write(pprint.pformat(context.user_data))
        except AttributeError:
            dbf.write(f"\n> Could not find user_data.")
        dbf.write("\n> raw update:\n")
        dbf.write(str(update))
        dbf.write("\n\n\n")
    return True

def log_text(str):
    if not DEBUG:
        return False
    with open(DEBUG_FILE, 'a', 'utf-8') as dbf:
        dbf.write("\n" + "-"*24 + "\n")
        dbf.write(f">  {datetime.now()}\n")
        dbf.write(str)
        dbf.write("\n\n\n")
    return True

def debug(update, context):
    log_update(update, context)
    context.bot.send_message(Chat(update.message.from_user.id, "private")., "To reduce spam, please edit your polls here.")

def start(update, context):  # * --> DEFAULT
    log_update(update, context)
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
    if(not 'polls' in context.chat_data):
        context.chat_data['polls'] = []
    help(update, context)
    context.user_data['conversation_state'] = DEFAULT

def help(update, context):   # * --> *
    log_update(update, context)
    update.message.reply_text('Welcome to *schedubot* (v0.0.1)!\n\nCurrently, this bot supports the following commands:\n\n/create Create a new poll.\n/add Add a poll you have created or participated in to current chat.\n/print Send a new message for a poll already added to this chat.\n/close Close a poll you created.\n/help Print this message.\n/reset Send this if the bot seems stuck or unresponsive.\n\nIf there are problems with voting, make sure the user has allowed this bot to contact him by sending it a /start in a direct message. This is due to Telegrams spam prevention and cannot be circumvented by us.', parse_mode=ParseMode.MARKDOWN)

def reset(update, context):  # * --> DEFAULT
    log_update(update, context)
    if 'active_poll' in context.user_data:
        del context.user_data['active_poll']
    if 'active_poll_prompt' in context.user_data:
        del context.user_data['active_poll_prompt']
    context.user_data['conversation_state'] = DEFAULT
    if 'create_description' in context.user_data:
        del context.user_data['create_description']
    if 'create_length' in context.user_data:
        del context.user_data['create_length']
    if 'create_name' in context.user_data:
        del context.user_data['create_name']
    if 'edit_poll' in context.user_data:
        del context.user_data['edit_poll']
    if 'prompt' in context.user_data:
        context.user_data['prompt'].delete()
        del context.user_data['prompt']
    context.bot.send_message(update.effective_user.id, "resetting...", reply_markup=ReplyKeyboardRemove(selective=True)).delete()

def cancel(update, context): # * --> DEFAULT
    reset(update, context)



def create(update, context):             # DEFAULT            --> TYPING_NAME
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
        return
    if(update.effective_chat.type != "private"):
        context.bot.send_message(update.message.from_user.id, "To reduce spam, please /create polls here first and then add them to your group(s).")
        context.user_data['conversation_state'] =  DEFAULT
        return
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
    update.message.reply_text("Please enter the name for your poll:", reply_markup=ReplyKeyboardRemove(selective=True))
    context.user_data['conversation_state'] = TYPING_NAME

def create_name(update, context):        # TYPING_NAME        --> TYPING_LENGTH
    log_update(update, context)
    context.user_data['create_name'] = update.message.text
    update.message.reply_text("Please enter how many columns your poll should include:")
    context.user_data['conversation_state'] = TYPING_LENGTH

def create_length(update, context):      # TYPING_LENGTH      --> TYPING_DESCRIPTION
    log_update(update, context)
    context.user_data['create_length'] = update.message.text
    if(not context.user_data['create_length'].isdigit() or int(context.user_data['create_length']) <= 0):
        update.message.reply_text("Please enter a number.")
        return
    update.message.reply_text("Please enter a description for your poll:")
    context.user_data['conversation_state'] = TYPING_DESCRIPTION

def create_description(update, context): # TYPING_DESCRIPTION --> DEFAULT
    log_update(update, context)
    context.user_data['create_description'] = update.message.text
    new_poll = poll.Poll(context.user_data['create_name'], context.user_data['create_description'], update.message.from_user.id, context.user_data['create_length'])
    context.user_data['polls'].append(new_poll)
    new_poll.print(context.bot, update.effective_chat)
    update.message.reply_text(f"Created poll named {context.user_data['create_name']} with {context.user_data['create_length']} columns.\nYou can now /add this poll to whichever chat(s) you want to use it in.", reply_markup=ReplyKeyboardRemove(selective=True))
    context.user_data['conversation_state'] = DEFAULT



def edit_name(update, context):        # DEFAULT                 --> CHOOSING_POLL_EDIT_NAME
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
        return
    if(update.effective_chat.type != "private"):
        context.bot.send_message(update.message.from_user.id, "To reduce spam, please edit your polls here.")
        return
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
        return
    elif(context.user_data['polls'] == []):
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
        return
    else:
        kbd = []
        ctr = 0
        for _poll in context.user_data['polls']:
            if(_poll.get_creator_id() == update.message.from_user.id):
                kbd.append([f"{ctr}: {_poll.get_name()}\n"])
            ctr += 1
        if(kbd == []):
            update.message.reply_text("You don't have any open polls.")
            return DEFAULT
        kbd.append(["/cancel"])
        context.user_data['prompt'] = update.message.reply_text("Which of your polls would you like to edit?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_EDIT_NAME

def edit_name_choice(update, context): # CHOOSING_POLL_EDIT_NAME --> TYPING_POLL_EDIT_NAME
    log_update(update, context)
    i = int(update.message.text.split(':')[0])
    if context.user_data['polls'][i]:
        if not context.user_data['polls'][i].get_creator_id() == update.message.from_user.id:
            update.message.reply_text(f"ERROR:\n{i} ({update.message.text}): You don't have permission to modify that poll. Chose another one or /cancel.")
            return
        if 'prompt' in context.user_data:
            context.user_data['prompt'].delete()
            del context.user_data['prompt']
        context.user_data['edit_poll'] = context.user_data['polls'][i]
        context.user_data['prompt'] = update.message.reply_text(f"What would you like the new name for {context.user_data['polls'][i].get_name()} to be?", reply_markup=ReplyKeyboardRemove(selective=True))
        context.user_data['conversation_state'] = TYPING_POLL_EDIT_NAME
        return
    else:
        update.message.reply_text(f"ERROR:\n{i} ({update.message.text}): No such poll. Chose another one or /cancel.")
        return

def edit_name_final(update, context):  # TYPING_POLL_EDIT_NAME   --> DEFAULT
    log_update(update, context)
    context.user_data['edit_poll'].set_name(update.message.text)
    context.user_data['edit_poll'].update(context.bot)
    del context.user_data['edit_poll']
    context.user_data['prompt'].delete()
    del context.user_data['prompt']
    context.user_data['conversation_state'] = DEFAULT



def edit_description(update, context):        # DEFAULT                        --> CHOOSING_POLL_EDIT_DESCRIPTION
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
        return
    if(update.effective_chat.type != "private"):
        context.bot.send_message(update.message.from_user.id, "To reduce spam, please edit your polls here.")
        return
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
        return
    elif(context.user_data['polls'] == []):
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
        return
    else:
        kbd = []
        ctr = 0
        for _poll in context.user_data['polls']:
            if(_poll.get_creator_id() == update.message.from_user.id):
                kbd.append([f"{ctr}: {_poll.get_name()}\n"])
            ctr += 1
        if(kbd == []):
            update.message.reply_text("You don't have any open polls.")
            return DEFAULT
        kbd.append(["/cancel"])
        context.user_data['prompt'] = update.message.reply_text("Which of your polls would you like to edit?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_EDIT_DESCRIPTION

def edit_description_choice(update, context): # CHOOSING_POLL_EDIT_DESCRIPTION --> TYPING_POLL_EDIT_DESCRIPTION
    log_update(update, context)
    i = int(update.message.text.split(':')[0])
    if context.user_data['polls'][i]:
        if not context.user_data['polls'][i].get_creator_id() == update.message.from_user.id:
            update.message.reply_text(f"ERROR:\n{i} ({update.message.text}): You don't have permission to modify that poll. Chose another one or /cancel.")
            return
        if 'prompt' in context.user_data:
            context.user_data['prompt'].delete()
            del context.user_data['prompt']
        context.user_data['edit_poll'] = context.user_data['polls'][i]
        context.user_data['prompt'] = update.message.reply_text(f"What would you like the new description for {context.user_data['polls'][i].get_name()} to be?", reply_markup=ReplyKeyboardRemove(selective=True))
        context.user_data['conversation_state'] = TYPING_POLL_EDIT_DESCRIPTION
        return
    else:
        update.message.reply_text(f"ERROR:\n{i} ({update.message.text}): No such poll. Chose another one or /cancel.")
        return

def edit_description_final(update, context):  # TYPING_POLL_EDIT_DESCRIPTION   --> DEFAULT
    log_update(update, context)
    context.user_data['edit_poll'].set_description(update.message.text)
    context.user_data['edit_poll'].update(context.bot)
    del context.user_data['edit_poll']
    context.user_data['prompt'].delete()
    del context.user_data['prompt']
    context.user_data['conversation_state'] = DEFAULT
    


def close(update, context):        # DEFAULT --> CHOOSING_POLL_CLOSE
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
        return
    if(update.effective_chat.type != "private"):
        context.bot.send_message(update.message.from_user.id, "To reduce spam, please /close your polls here.")
        return
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
        return
    elif(context.user_data['polls'] == []):
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
        return
    else:
        kbd = []
        ctr = 0
        for _poll in context.user_data['polls']:
            if(_poll.get_creator_id() == update.message.from_user.id):
                kbd.append([f"{ctr}: {_poll.get_name()}\n"])
            ctr += 1
        if(kbd == []):
            update.message.reply_text("You don't have any open polls.")
            return DEFAULT
        kbd.append(["/cancel"])
        context.user_data['prompt'] = update.message.reply_text("Which of your polls would you like to close?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_CLOSE

def close_choice(update, context): # CHOOSING_POLL_CLOSE --> DEFAULT
    log_update(update, context)
    if not update.message.text.split(':')[0].isdigit():
        update.message.reply_text(f"ERROR:\n{i} ({update.message.text}): No such poll. Try again or /cancel.")
        return
    i = int(update.message.text.split(':')[0])
    if i < len(context.user_data['polls']):
        if not context.user_data['polls'][i].get_creator_id() == update.message.from_user.id:
            update.message.reply_text(f"ERROR:\n{i} {update.message.text} --- You don't have permission to close that poll. Chose another one or /cancel.")
            return
        if('polls' in context.chat_data and context.user_data['polls'][i] in context.chat_data['polls']):
            context.chat_data['polls'].remove(context.user_data['polls'][i])
        if 'prompt' in context.user_data:
            context.user_data['prompt'].delete()
            del context.user_data['prompt']
        context.user_data['polls'][i].close(update.message.from_user, context.bot)
        context.user_data['polls'].remove(context.user_data['polls'][i])
        update.message.reply_text(update.effective_user.id, "resetting...", reply_markup=ReplyKeyboardRemove(selective=True)).delete()
        context.user_data['conversation_state'] = DEFAULT
        return
    else:
        update.message.reply_text(f"ERROR:\n{i} {update.message.text} --- No such poll. Chose another one or /cancel.")
        return



def add_poll_to_chat(update, context):        # DEFAULT --> CHOOSING_POLL_ADD
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
        return
    if(update.effective_chat.type == "private"):
        update.message.reply_text("Cannot add polls to private chats. Try adding a poll to a group or channel instead.")
        return
    if(not 'polls' in context.chat_data):
        context.chat_data['polls'] = []
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.\nDo you want to /create a new one?")
        return
    elif(context.user_data['polls'] == []):
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.\nDo you want to /create a new one?")
        return
    else:
        kbd = []
        ctr = 0
        for _poll in context.user_data['polls']:
            kbd.append([f"{ctr}: {_poll.get_name()}\n"])
            ctr += 1
        kbd.append(["/cancel"])
        context.user_data['prompt'] = update.message.reply_text("Which poll would you like to add to this chat?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_ADD
        return

def add_poll_to_chat_choice(update, context): # CHOOSING_POLL_ADD --> DEFAULT
    log_update(update, context)
    if not update.message.text.split(':')[0].isdigit():
        update.message.reply_text(f"ERROR:\n{i} {update.message.text} --- No such poll. Try again or /cancel.")
        return
    i = int(update.message.text.split(':')[0])
    if i < len(context.user_data['polls']):
        if not context.user_data['polls'][i] in context.chat_data['polls']:
            context.chat_data['polls'].append(context.user_data['polls'][i])
        context.user_data['polls'][i].print(context.bot, update.effective_chat)
        if 'prompt' in context.user_data:
            context.user_data['prompt'].delete()
            del context.user_data['prompt']
        update.message.reply_text(update.effective_user.id, "resetting...", reply_markup=ReplyKeyboardRemove(selective=True)).delete()
        context.user_data['conversation_state'] = DEFAULT
        return
    else:
        update.message.reply_text(f"ERROR:\n{i}: {update.message.text} --- No such poll. Try again or /cancel.")
        return



def print_poll(update, context):        # DEFAULT --> CHOOSING_POLL_PRINT
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
        return
    if(update.effective_chat.type == "private"):
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
    ctr = 0
    for _poll in data['polls']:
        if(_poll.is_open()):
            kbd.append([f"{ctr}: {_poll.get_name()}\n"])
            ctr += 1
        else:
            data['polls'].remove(poll)
    if(ctr == 0):
        context.bot.send_message(update.message.from_user.id, "There are no open polls in that chat.\nDid you mean to /add one?")
        return
    kbd.append(["/cancel"])
    update.message.reply_text("Which poll would you like to print again?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
    context.user_data['conversation_state'] = CHOOSING_POLL_PRINT

def print_poll_choice(update, context): # CHOOSING_POLL_PRINT --> DEFAULT
    log_update(update, context)
    if(update.effective_chat.type == "private"):
        data = context.user_data
    else:
        data = context.chat_data
    if not update.message.text.split(':')[0].isdigit():
        update.message.reply_text(f"ERROR:\n{i} {update.message.text} --- No such poll. Try again or /cancel.")
        return
    i = int(update.message.text.split(':')[0])
    if i < len(data['polls']):
        data['polls'][i].print(context.bot, update.effective_chat)
        update.message.reply_text(update.effective_user.id, "resetting...", reply_markup=ReplyKeyboardRemove(selective=True)).delete()
        context.user_data['conversation_state'] = DEFAULT
        return
    else:
        update.message.reply_text(f"ERROR:\n{i}: {update.message.text} --- No such poll. Try again or /cancel.")
        return



"""def vote(update, context):       # DEFAULT --> TYPING_VOTE
    log_update(update, context)
    if not 'polls' in context.user_data:
        context.user_data['polls'] = []
    if not 'polls' in context.chat_data:
        context.chat_data['polls'] = []
    for _poll in context.chat_data['polls']:
        if _poll.knows_msg(update.callback_query.message):
            if not _poll.is_open():
                context.chat_data['polls'].remove(_poll)
                if _poll in context.user_data['polls']:
                    context.user_data['polls'].remove(_poll)
                context.bot.send_message(update.callback_query.from_user.id, "Voting for that poll has ended.")
                return
            if not _poll in context.user_data['polls']:
                context.user_data['polls'].append(_poll)
            context.user_data['active_poll'] = _poll
            if not update.effective_chat.type == "private":
                _poll.print(context.bot, Chat(update.callback_query.from_user.id, "private"), votable=False)
            log_text(context.bot.get_me().link)
            prompt = context.bot.send_message(update.callback_query.from_user.id, f"Please enter your votes for \"{_poll.get_name()}\":\n\n(Write a '+' for a column you want to agree to, a '-' for one you disagree with or a '?' for one you are not sure about. Everything alse gets ignored. Omitting votes will fill the remainder with '?'s, superfluous votes are discarded.\nYou can always correct your vote as long as the poll is still open.\n/cancel to cancel voting")
            context.user_data['active_poll_prompt'] = prompt
            context.user_data['conversation_state'] = TYPING_VOTE
            return
    for _poll in context.user_data['polls']:
        if _poll.knows_msg(update.callback_query.message):
            if not _poll.is_open():
                context.user_data['polls'].remove(_poll)
                if _poll in context.chat_data['polls']:
                    context.chat_data['polls'].remove(_poll)
                context.bot.send_message(update.callback_query.from_user.id, "Voting for that poll has ended.")
                return
            if not _poll in context.chat_data['polls']:
                context.chat_data['polls'].append(_poll)
            context.user_data['active_poll'] = _poll
            if not update.effective_chat.type == "private":
                poll.print(context.bot, Chat(update.callback_query.from_user.id, "private"), votable=False)
            prompt = context.bot.send_message(update.callback_query.from_user.id, f"Please enter your votes for \"{_poll.get_name()}\":\n\n(Write a '+' for a column you want to agree to, a '-' for one you disagree with or a '?' for one you are not sure about. Everything alse gets ignored. Omitting votes will fill the remainder with '?'s, superfluous votes are discarded.\nYou can always correct your vote as long as the poll is still open.\n/cancel to cancel voting")
            context.user_data['active_poll_prompt'] = prompt
            context.user_data['conversation_state'] = TYPING_VOTE
            return
    context.bot.send_message(update.callback_query.from_user.id, "Something went wrong. Try adding this poll to the chat again.\nSorry for the inconvenience.")
    return"""

def vote_enter(update, context): # TYPING_VOTE --> DEFAULT
    if update.effective_chat.type == "private":
        if 'active_poll' in context.user_data:
            context.user_data['active_poll'].vote(update.message.from_user.name, update.message.text)
            context.user_data['active_poll'].update(context.bot)
            del context.user_data['active_poll']
            context.user_data['active_poll_prompt'].delete()
            del context.user_data['active_poll_prompt']
            context.user_data['conversation_state'] = DEFAULT
            return
        else:
            reset(update, context)
            return
    else:
        if 'active_poll' in context.user_data:
            context.user_data['active_poll_prompt'].delete()
            context.user_data['active_poll_prompt'] = context.bot.send_message(update.effective_user.id, f"Please enter your votes for \"{poll.get_name()}\":\n\n(Write a '+' for a column you want to agree to, a '-' for one you disagree with or a '?' for one you are not sure about. Everything alse gets ignored. Omitting votes will fill the remainder with '?'s, superfluous votes are discarded.\nYou can always correct your vote as long as the poll is still open.\n/cancel to cancel voting")
            context.user_data['conversation_state'] = TYPING_VOTE
            return
        else:
            reset(update, context)
            return



def default_handler(update, context):
    log_update(update, context)
    if 'conversation_state' in context.user_data:
        switch = {
            TYPING_NAME:                    create_name, 
            TYPING_LENGTH:                  create_length, 
            TYPING_DESCRIPTION:             create_description,
            CHOOSING_POLL_ADD:              add_poll_to_chat_choice,
            CHOOSING_POLL_CLOSE:            close_choice,
            CHOOSING_POLL_PRINT:            print_poll_choice,
            CHOOSING_POLL_EDIT_NAME:        edit_name_choice,
            TYPING_POLL_EDIT_NAME:          edit_name_final,
            CHOOSING_POLL_EDIT_DESCRIPTION: edit_description_choice,
            TYPING_POLL_EDIT_DESCRIPTION:   edit_description_final,
            TYPING_VOTE:                    vote_enter,
            DEFAULT:                        help
        }
        f = switch.get(context.user_data['conversation_state'], help)
        f(update, context)
        return
    else:
        context.user_data['conversation_state'] = DEFAULT
        return
        


def error(update, context):
    log_update(update, context)
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def err(update, context):
    log_update(update, context)
    update.message.reply_text("You should never see this message. If you do, please contact @Entropy0")


def main():
    global DEBUG
    if len(sys.argv) < 2:
        print(f"Usage:\n' {sys.argv[0]} <TOKEN> (<DEBUG>)")
        quit(1)
    TOKEN = sys.argv[1]
    if len(sys.argv) >= 3:
        if sys.argv[2] == "--debug":
            DEBUG = True

    pp = PicklePersistence(filename=PERSISTENCE_FILE)
    updater = Updater(TOKEN, persistence=pp, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))                       # *       --> DEFAULT
    dp.add_handler(CommandHandler("init", start))                        # *       --> DEFAULT
    dp.add_handler(CommandHandler("help", help))                         # *       --> *
    dp.add_handler(CommandHandler("create", create))                     # DEFAULT --> TYPING_NAME
    dp.add_handler(CommandHandler("vote", vote))                         # *       --> TYPING_VOTE
    dp.add_handler(CommandHandler("add", add_poll_to_chat))              # DEFAULT --> CHOOSING_POLL_ADD
    dp.add_handler(CommandHandler("print", print_poll))                  # DEFAULT --> CHOOSING_POLL_PRINT
    dp.add_handler(CommandHandler("close", close))                       # DEFAULT --> CHOOSING_POLL_CLOSE
    dp.add_handler(CommandHandler("edit_description", edit_description)) # DEFAULT --> CHOOSING_POLL_EDIT_DESCRIPTION
    dp.add_handler(CommandHandler("edit_name", edit_name))               # DEFAULT --> CHOOSING_POLL_EDIT_NAME
    dp.add_handler(CommandHandler("cancel", reset))                      # *       --> DEFAULT
    dp.add_handler(CommandHandler("reset", reset))                       # *       --> DEFAULT
    dp.add_handler(CommandHandler("debug", debug))                       # *       --> *

    dp.add_handler(MessageHandler(Filters.text, default_handler))

    #dp.add_handler(CallbackQueryHandler(vote))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()