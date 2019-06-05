#!/usr/bin/env python3.6

import sys
import logging
import inspect, pprint
from codecs import open
from datetime import datetime

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ParseMode, ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply

import poll
from pollpicklepersistence import PollPicklePersistence

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

PERSISTENCE_FILE = 'schedubot_persistence'
pp = PollPicklePersistence(filename=PERSISTENCE_FILE)

DEBUG = False
DEBUG_FILE = 'schedubot_debug'

DEFAULT = -1
TYPING_NAME, TYPING_LENGTH, TYPING_DESCRIPTION, CHOOSING_POLL_ADD, CHOOSING_POLL_CLOSE, CHOOSING_POLL_PRINT, CHOOSING_POLL_EDIT_NAME, TYPING_POLL_EDIT_NAME, CHOOSING_POLL_EDIT_DESCRIPTION, TYPING_POLL_EDIT_DESCRIPTION, TYPING_VOTE = range(11)
STATES = {
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

VERSION = "0.0.2"

poll_data = dict()

def log_update(update, context):
    if not DEBUG:
        return False
    st = ""
    try:
        st += f"> {update.message.from_user.name} called {inspect.currentframe().f_back.f_code.co_name} by sending the following:\n"
        st += update.message.text
        st += "\n"
    except AttributeError:
        try:
            st += f"> {update.callback_query.from_user.name} called {inspect.currentframe().f_back.f_code.co_name} by clicking a button.\n"
        except AttributeError:
            st += f"> {update.effective_user.name} called {inspect.currentframe().f_back.f_code.co_name} via unknown means.\n"
    try:
        st += f"> (conversation_state: {context.user_data['conversation_state']} - {STATES.get(context.user_data['conversation_state'], 'unknown')})\n"
    except KeyError:
        st += f"> (conversation_state: unknown)\n"
    try:
        st += "\n> chat_data:\n"
        st += pprint.pformat(context.chat_data)
        st += "\n"
    except AttributeError:
        st += f"> Could not find chat_data.\n"
    try:
        st += "> user_data:\n"
        st += pprint.pformat(context.user_data)
        st += "\n"
    except AttributeError:
        st += f"> Could not find user_data.\n"
    st += "> poll_data:\n"
    st += pprint.pformat(poll_data)
    st += "\n"
    try:
        st += "> args:\n"
        st += pprint.pformat(context.args)
        st += "\n"
    except AttributeError:
        st += f"> Could not find args.\n"
    st += "> raw update:\n"
    st += str(update)
    st += "\n"
    log_text(st)
    return True

def log_error(update, error):
    if not DEBUG:
        return
    st = f"> ERROR: {error}\n"
    st += f"> raw update:\n{str(update)}\n"
    log_text(st)

def log_text(st):
    if not DEBUG:
        return False
    with open(DEBUG_FILE, 'a', 'utf-8') as dbf:
        dbf.write("\n" + "-"*24 + "\n")
        dbf.write(f">  {datetime.now()}\n")
        dbf.write(st)
        dbf.write("\n\n\n")
    return True

def debug(update, context):
    log_update(update, context)

def start(update, context):  # * --> DEFAULT
    log_update(update, context)
    if not 'polls' in context.user_data:
        context.user_data['polls'] = []
    if not 'polls' in context.chat_data:
        context.chat_data['polls'] = []
    try:
        vote(update, context)
    except (AttributeError, IndexError):
        help(update, context)
        context.user_data['conversation_state'] = DEFAULT

def help(update, context):   # * --> *
    log_update(update, context)
    update.message.reply_text(f'Welcome to *schedubot* (v{VERSION})!\n\nCurrently, this bot supports the following commands:\n\n/create Create a new poll.\n/name Edit the name of one of your polls.\n/desc Edit the description of one of your polls.\n/add Add one of your polls or a poll you have participated in to a chat.\n/print Send a new message for a poll already added to this chat.\n/close Close one of your polls.\n/help Print this message.\n/reset Send this if the bot seems stuck or unresponsive.', parse_mode=ParseMode.MARKDOWN)

def link(update, context):   # * --> *
    log_update(update, context)
    update.message.reply_text(context.bot.get_me().link)

def reset(update, context):  # * --> DEFAULT
    log_update(update, context)
    if 'active_poll' in context.user_data:
        _poll = poll_data.get(context.user_data['active_poll'])
        if _poll:
            _poll.update(context.bot)
            global pp
            pp.update_poll_data(_poll.id, _poll)
        del context.user_data['active_poll']
    context.user_data['conversation_state'] = DEFAULT
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

def cancel(update, context): # * --> DEFAULT
    reset(update, context)



def create(update, context):             # DEFAULT            --> TYPING_NAME
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
        return
    if update.effective_chat.type != "private":
        context.bot.send_message(update.message.from_user.id, "To reduce spam, please /create polls here first and then add them to your group(s).")
        context.user_data['conversation_state'] = DEFAULT
        return
    if not 'polls' in context.user_data:
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
    global poll_data
    while new_poll.get_id() in poll_data: # UUID(4) collisions? Really?
        new_poll.new_id()
    poll_data[new_poll.get_id()] = new_poll
    global pp
    pp.update_poll_data(new_poll.get_id(), new_poll)

    context.user_data['polls'].append(new_poll.get_id())
    new_poll.print(context.bot, update.effective_chat)
    update.message.reply_text(f"Created poll named {context.user_data['create_name']} with {context.user_data['create_length']} columns.\nYou can now /add this poll to whichever chat(s) you want to use it in.", reply_markup=ReplyKeyboardRemove(selective=True))
    context.user_data['conversation_state'] = DEFAULT



def edit_name(update, context):        # DEFAULT                 --> CHOOSING_POLL_EDIT_NAME
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
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
            _poll = poll_data.get(context.user_data['polls'][i])
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
        context.user_data['prompt'] = update.message.reply_text("Which of your polls would you like to edit?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_EDIT_NAME

def edit_name_choice(update, context): # CHOOSING_POLL_EDIT_NAME --> TYPING_POLL_EDIT_NAME
    log_update(update, context)
    if not update.message.text.split(':')[0].isdigit():
        update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
        return
    i = int(update.message.text.split(':')[0])
    if i < len(context.user_data['polls']):
        _poll = poll_data.get(context.user_data['polls'][i])
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
        context.user_data['prompt'] = update.message.reply_text(f"What would you like the new name for {_poll.get_name()} to be?", reply_markup=ReplyKeyboardRemove(selective=True))
        context.user_data['conversation_state'] = TYPING_POLL_EDIT_NAME
        return
    else:
        update.message.reply_text(f"ERROR:{update.message.text} --- No such poll. Chose another one or /cancel.")
        return

def edit_name_final(update, context):  # TYPING_POLL_EDIT_NAME   --> DEFAULT
    log_update(update, context)
    _poll = poll_data.get(context.user_data['active_poll'])
    _poll.set_name(update.message.text)
    _poll.update(context.bot)
    global pp
    pp.update_poll_data(_poll.id, _poll)
    del context.user_data['active_poll']
    context.user_data['prompt'].delete()
    del context.user_data['prompt']
    context.user_data['conversation_state'] = DEFAULT



def edit_description(update, context):        # DEFAULT                        --> CHOOSING_POLL_EDIT_DESCRIPTION
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
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
            _poll = poll_data.get(context.user_data['polls'][i])
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
        context.user_data['prompt'] = update.message.reply_text("Which of your polls would you like to edit?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_EDIT_DESCRIPTION

def edit_description_choice(update, context): # CHOOSING_POLL_EDIT_DESCRIPTION --> TYPING_POLL_EDIT_DESCRIPTION
    log_update(update, context)
    if not update.message.text.split(':')[0].isdigit():
        update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
        return
    i = int(update.message.text.split(':')[0])
    if i < len(context.user_data['polls']):
        _poll = poll_data.get(context.user_data['polls'][i])
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
        context.user_data['prompt'] = update.message.reply_text(f"What would you like the new description for {_poll.get_name()} to be?", reply_markup=ReplyKeyboardRemove(selective=True))
        context.user_data['conversation_state'] = TYPING_POLL_EDIT_DESCRIPTION
        return
    else:
        update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Chose another one or /cancel.")
        return

def edit_description_final(update, context):  # TYPING_POLL_EDIT_DESCRIPTION   --> DEFAULT
    log_update(update, context)
    _poll = poll_data.get(context.user_data['active_poll'])
    _poll.set_description(update.message.text)
    _poll.update(context.bot)
    global pp
    pp.update_poll_data(_poll.id, _poll)
    del context.user_data['active_poll']
    context.user_data['prompt'].delete()
    del context.user_data['prompt']
    context.user_data['conversation_state'] = DEFAULT



def close(update, context):        # DEFAULT --> CHOOSING_POLL_CLOSE
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
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
            _poll = poll_data.get(context.user_data['polls'][i])
            if not _poll:
                continue
            if _poll.get_creator_id() != update.message.from_user.id:
                continue
            kbd.append([f"{i}: {_poll.get_name()}\n"])
        if kbd == []:
            update.message.reply_text("You don't have any open polls.")
            return
        kbd.append(["/cancel"])
        context.user_data['prompt'] = update.message.reply_text("Which of your polls would you like to close?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_CLOSE

def close_choice(update, context): # CHOOSING_POLL_CLOSE --> DEFAULT
    log_update(update, context)
    if not update.message.text.split(':')[0].isdigit():
        update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
        return
    i = int(update.message.text.split(':')[0])
    if i < len(context.user_data['polls']):
        _poll = poll_data.get(context.user_data['polls'][i])
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
        global pp
        pp.update_poll_data(_poll.id, _poll)
        update.message.reply_text("resetting...", reply_markup=ReplyKeyboardRemove(selective=True)).delete()
        context.user_data['conversation_state'] = DEFAULT
        return
    else:
        update.message.reply_text(f"ERROR:\n {update.message.text} --- No such poll. Chose another one or /cancel.")
        return



def add_poll_to_chat(update, context):        # DEFAULT --> CHOOSING_POLL_ADD
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
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
            _poll = poll_data.get(context.user_data['polls'][i])
            if not _poll:
                continue
            kbd.append([f"{i}: {_poll.get_name()}\n"])
        kbd.append(["/cancel"])
        context.user_data['prompt'] = update.message.reply_text("Which poll would you like to add to this chat?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_ADD
        return

def add_poll_to_chat_choice(update, context): # CHOOSING_POLL_ADD --> DEFAULT
    log_update(update, context)
    if not update.message.text.split(':')[0].isdigit():
        update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
        return
    i = int(update.message.text.split(':')[0])
    if i < len(context.user_data['polls']):
        if not context.user_data['polls'][i] in context.chat_data['polls']:
            context.chat_data['polls'].append(context.user_data['polls'][i])
        _poll = poll_data.get(context.user_data['polls'][i])
        if not _poll:
            update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
            return
        _poll.print(context.bot, update.effective_chat)
        global pp
        pp.update_poll_data(_poll.id, _poll)
        if 'prompt' in context.user_data:
            context.user_data['prompt'].delete()
            del context.user_data['prompt']
        update.message.reply_text("resetting...", reply_markup=ReplyKeyboardRemove(selective=True)).delete()
        context.user_data['conversation_state'] = DEFAULT
        return
    else:
        update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
        return



def print_poll(update, context):        # DEFAULT --> CHOOSING_POLL_PRINT
    log_update(update, context)
    if 'conversation_state' in context.user_data and not context.user_data['conversation_state'] == DEFAULT:
        default_handler(update, context)
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
        _poll = poll_data.get(data['polls'][i])
        if not _poll:
            continue
        kbd.append([f"{i}: {_poll.get_name()}\n"])
    if kbd == []:
        context.bot.send_message(update.message.from_user.id, "There are no open polls in that chat.\nDid you mean to /add one?")
        return
    kbd.append(["/cancel"])
    update.message.reply_text("Which poll would you like to print again?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
    context.user_data['conversation_state'] = CHOOSING_POLL_PRINT

def print_poll_choice(update, context): # CHOOSING_POLL_PRINT --> DEFAULT
    log_update(update, context)
    if update.effective_chat.type == "private":
        data = context.user_data
    else:
        data = context.chat_data
    if not update.message.text.split(':')[0].isdigit():
        update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
        return
    i = int(update.message.text.split(':')[0])
    if i < len(data['polls']):
        _poll = poll_data.get(data['polls'][i])
        if not _poll:
            update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
            return
        _poll.print(context.bot, update.effective_chat)
        global pp
        pp.update_poll_data(_poll.id, _poll)
        update.message.reply_text("resetting...", reply_markup=ReplyKeyboardRemove(selective=True)).delete()
        context.user_data['conversation_state'] = DEFAULT
        return
    else:
        update.message.reply_text(f"ERROR:\n{update.message.text} --- No such poll. Try again or /cancel.")
        return



def vote(update, context):
    log_update(update, context)
    if update.effective_chat.type != "private":
        default_handler(update, context)
        return
    poll_id = context.args[0]
    _poll = poll_data.get(poll_id)
    if not _poll:
        context.bot.send_message(update.effective_user.id, "Sorry, something went wrong. Try adding the poll to the chat again.")
        reset(update, context)
        return
    if not 'polls' in context.user_data:
        context.user_data['polls'] = []
    if not poll_id in context.user_data['polls']:
        context.user_data['polls'].append(poll_id)
    _poll.print(context.bot, update.effective_chat, votable=False)
    global pp
    pp.update_poll_data(_poll.id, _poll)
    prompt = context.bot.send_message(update.effective_user.id, f"Please enter your votes for \"{_poll.get_name()}\":\n\n(Write a '+' for a column you want to agree to, a '-' for one you disagree with or a '?' for one you are not sure about. Everything alse gets ignored. Omitting votes will fill the remainder with '?'s, superfluous votes are discarded.\nYou can always correct your vote as long as the poll is still open.\n/cancel to cancel voting")
    context.user_data['active_poll'] = poll_id
    context.user_data['prompt'] = prompt
    context.user_data['conversation_state'] = TYPING_VOTE
    return

def vote_enter(update, context): # TYPING_VOTE --> DEFAULT
    if update.effective_chat.type == "private":
        if 'active_poll' in context.user_data:
            _poll = poll_data.get(context.user_data['active_poll'])
            if not _poll:
                context.bot.send_message(update.effective_user.id, "Sorry, something went wrong. Try adding the poll to the chat again.")
                reset(update, context)
                return
            _poll.vote(update.message.from_user.name, update.message.text)
            _poll.update(context.bot)
            global pp
            pp.update_poll_data(_poll.id, _poll)
            del context.user_data['active_poll']
            context.user_data['prompt'].delete()
            del context.user_data['prompt']
            context.user_data['conversation_state'] = DEFAULT
            return
        else:
            reset(update, context)
            return
    else:
        if 'active_poll' in context.user_data:
            context.user_data['prompt'].delete()
            _poll = poll_data.get(context.user_data['active_poll'])
            if not _poll:
                context.bot.send_message(update.effective_user.id, "Sorry, something went wrong. Try adding the poll to the chat again.")
                reset(update, context)
                return
            context.user_data['prompt'] = context.bot.send_message(update.effective_user.id, f"Please enter your votes for \"{_poll.get_name()}\":\n\n(Write a '+' for a column you want to agree to, a '-' for one you disagree with or a '?' for one you are not sure about. Everything alse gets ignored. Omitting votes will fill the remainder with '?'s, superfluous votes are discarded.\nYou can always correct your vote as long as the poll is still open.\n/cancel to cancel voting")
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
    log_error(update, context.error)

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

    global pp
    updater = Updater(TOKEN, persistence=pp, use_context=True)

    global poll_data
    poll_data = pp.get_poll_data()

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))                       # *       --> DEFAULT
    dp.add_handler(CommandHandler("init", start))                        # *       --> DEFAULT
    dp.add_handler(CommandHandler("help", help))                         # *       --> *
    dp.add_handler(CommandHandler("link", link))                         # *       --> *
    dp.add_handler(CommandHandler("create", create))                     # DEFAULT --> TYPING_NAME
    dp.add_handler(CommandHandler("vote", vote))                         # *       --> TYPING_VOTE
    dp.add_handler(CommandHandler("add", add_poll_to_chat))              # DEFAULT --> CHOOSING_POLL_ADD
    dp.add_handler(CommandHandler("print", print_poll))                  # DEFAULT --> CHOOSING_POLL_PRINT
    dp.add_handler(CommandHandler("close", close))                       # DEFAULT --> CHOOSING_POLL_CLOSE
    dp.add_handler(CommandHandler("desc", edit_description)) # DEFAULT --> CHOOSING_POLL_EDIT_DESCRIPTION
    dp.add_handler(CommandHandler("name", edit_name))               # DEFAULT --> CHOOSING_POLL_EDIT_NAME
    dp.add_handler(CommandHandler("cancel", reset))                      # *       --> DEFAULT
    dp.add_handler(CommandHandler("reset", reset))                       # *       --> DEFAULT
    dp.add_handler(CommandHandler("debug", debug))                       # *       --> *

    dp.add_handler(MessageHandler(Filters.text, default_handler))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
