#!/usr/bin/env python3.6

import sys
import logging
import parser, poll
import inspect, pprint

from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, Filters, PicklePersistence
from telegram import ParseMode, ReplyKeyboardMarkup, Chat
from codecs import open
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = ""
PERSISTENCE_FILE = 'schedubot_persistence'

DEBUG = False
DEBUG_FILE = 'schedubot_debug'


TYPING_NAME, TYPING_LENGTH, TYPING_DESCRIPTION, CHOOSING_POLL_ADD, CHOOSING_POLL_CLOSE, CHOOSING_POLL_PRINT, CHOOSING_POLL_EDIT_NAME, TYPING_POLL_EDIT_NAME, CHOOSING_POLL_EDIT_DESCRIPTION, TYPING_POLL_EDIT_DESCRIPTION = range(10)


def debug_log(update, context):
    if not DEBUG:
        return False
    with open(DEBUG_FILE, 'a', 'utf-8') as dbf:
        dbf.write("-"*24 + "\n")
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
            dbf.write("\n> chat_data:\n")
            dbf.write(pprint.pformat(context.chat_data))
        except AttributeError:
            dbf.write(f"> Could not find chat_data.")
        try:
            dbf.write("\n> user_data:\n")
            dbf.write(pprint.pformat(context.user_data))
        except AttributeError:
            dbf.write(f"> Could not find user_data.")
        dbf.write("\n> raw update:\n")
        dbf.write(str(update))
        dbf.write("\n\n\n")
        return True


def start(update, context):
    debug_log(update, context)
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
    if(not 'polls' in context.chat_data):
        context.chat_data['polls'] = []
    context.user_data['conversation_state'] = ConversationHandler.END
    help(update, context)
    return ConversationHandler.END

def help(update, context):
    debug_log(update, context)
    update.message.reply_text('Welcome to *schedubot* (barebones version)!\n\nCurrently, this bot supports the following commands:\n\n/create Create a new poll.\n/add Add a poll you have created or participated in to current chat.\n/print Send a new message for a poll already added to this chat.\n/close Close a poll you created.\n/help Print this message.\n/reset Send this if the bot seems stuck or unresponsive.\n\nIf there are problems with voting, make sure the user has allowed this bot to contact him by sending it a /start in a direct message. This is due to Telegrams spam prevention and cannot be circumvented by us.', parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END

def reset(update, context):
    debug_log(update, context)
    if 'active_poll' in context.user_data:
        del context.user_data['active_poll']
    if 'active_poll_prompt' in context.user_data:
        del context.user_data['active_poll_prompt']
    context.user_data['conversation_state'] = ConversationHandler.END
    if 'create_description' in context.user_data:
        del context.user_data['create_description']
    if 'create_length' in context.user_data:
        del context.user_data['create_length']
    if 'create_name' in context.user_data:
        del context.user_data['create_name']
    if 'edit_poll' in context.user_data:
        del context.user_data['edit_poll']
    if 'prompt' in context.user_data:
        del context.user_data['prompt']
    return ConversationHandler.END



def create(update, context):
    debug_log(update, context)
    if(update.effective_chat.type != "private"):
        context.bot.send_message(update.message.from_user.id, "To reduce spam, please create polls here first and then add them to your group(s).")
        return ConversationHandler.END
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
    update.message.reply_text("Please enter the name for your poll:")
    context.user_data['conversation_state'] = TYPING_NAME
    return TYPING_NAME

def create_name(update, context):
    debug_log(update, context)
    context.user_data['create_name'] = update.message.text
    update.message.reply_text("Please enter how many columns your poll should include:")
    context.user_data['conversation_state'] = TYPING_LENGTH
    return TYPING_LENGTH

def create_length(update, context):
    debug_log(update, context)
    context.user_data['create_length'] = update.message.text
    if(not context.user_data['create_length'].isdigit() or int(context.user_data['create_length']) <= 0):
        update.message.reply_text("Please enter a number.")
        return TYPING_LENGTH
    update.message.reply_text("Please enter a description for your poll:")
    context.user_data['conversation_state'] = TYPING_DESCRIPTION
    return TYPING_DESCRIPTION

def create_description(update, context):
    debug_log(update, context)
    context.user_data['create_description'] = update.message.text
    _poll = poll.Poll(context.user_data['create_name'], context.user_data['create_description'], update.message.from_user, context.user_data['create_length'])
    context.user_data['polls'].append(_poll)
    _poll.print(context.bot, update.effective_chat)
    update.message.reply_text(f"Created poll named {context.user_data['create_name']} with {context.user_data['create_length']} columns.\nYou can now /add this poll to whichever chat(s) you want to use it in.")
    del context.user_data['conversation_state']
    return ConversationHandler.END

def create_cancel(update, context):
    debug_log(update, context)
    update.message.reply_text("Stopped creating new poll.")
    del context.user_data['conversation_state']
    return ConversationHandler.END



def edit_description(update, context):
    debug_log(update, context)
    if(update.effective_chat.type != "private"):
        context.bot.send_message(update.message.from_user.id, "To reduce spam, please edit your polls here.")
        return ConversationHandler.END
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
        return ConversationHandler.END
    elif(context.user_data['polls'] == []):
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
        return ConversationHandler.END
    else:
        kbd = []
        ctr = 0
        for poll in context.user_data['polls']:
            if(poll.get_creator().id == update.message.from_user.id):
                kbd.append([f"{ctr}: {poll.get_name()}\n"])
            ctr += 1
        if(kbd == []):
            update.message.reply_text("You don't have any open polls.")
            return ConversationHandler.END
        kbd.append(["/cancel"])
        context.user_data['prompt'] = update.message.reply_text("Which of your polls would you like to edit?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_EDIT_NAME
        return CHOOSING_POLL_EDIT_NAME

def edit_description_choice(update, context):
    debug_log(update, context)
    i = int(update.message.text.split(':')[0])
    if context.user_data['polls'][i]:
        if not context.user_data['polls'][i].get_creator().id == update.message.from_user.id:
            update.message.reply_text(f"ERROR:\n{i} ({update.message.text}): You don't have permission to close that poll. Try again or /cancel.")
            return CHOOSING_POLL_EDIT_NAME
        if 'prompt' in context.user_data:
            context.user_data['prompt'].delete()
            del context.user_data['prompt']
        context.user_data['edit_poll'] = poll
        context.user_data['prompt'] = update.message.reply_text(f"What would you like the new name for {context.user_data['polls'][i]}?")
        context.user_data['conversation_state'] = TYPING_POLL_EDIT_NAME
        return TYPING_POLL_EDIT_NAME
    else:
        update.message.reply_text(f"ERROR:\n{i} ({update.message.text}): No such poll. Try again or /cancel.")
        context.user_data['conversation_state'] = CHOOSING_POLL_EDIT_NAME
        return CHOOSING_POLL_EDIT_NAME

def edit_description_final(update, context):
    debug_log(update, context)
    context.user_data['edit_poll'].edit_name(update.message.text)
    context.user_data['edit_poll'].update()
    del context.user_data['edit_poll']
    context.user_data['prompt'].delete()
    del context.user_data['prompt']
    del context.user_data['conversation_state']
    return ConversationHandler.END

def edit_description_cancel(update, context):
    debug_log(update, context)
    context.user_data['prompt'].delete()
    del context.user_data['prompt']
    del context.user_data['conversation_state']
    return ConversationHandler.END
    


def close(update, context):
    debug_log(update, context)
    if(update.effective_chat.type != "private"):
        context.bot.send_message(update.message.from_user.id, "To reduce spam, please close your polls here.")
        return ConversationHandler.END
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
        return ConversationHandler.END
    elif(context.user_data['polls'] == []):
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.")
        return ConversationHandler.END
    else:
        kbd = []
        ctr = 0
        for poll in context.user_data['polls']:
            if(poll.get_creator().id == update.message.from_user.id):
                kbd.append([f"{ctr}: {poll.get_name()}\n"])
            ctr += 1
        if(kbd == []):
            update.message.reply_text("You don't have any open polls.")
            return ConversationHandler.END
        kbd.append(["/cancel"])
        context.user_data['prompt'] = update.message.reply_text("Which of your polls would you like to close?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_CLOSE
        return CHOOSING_POLL_CLOSE

def close_choice(update, context):
    debug_log(update, context)
    i = int(update.message.text.split(':')[0])
    if context.user_data['polls'][i]:
        if not context.user_data['polls'][i].get_creator().id == update.message.from_user.id:
            update.message.reply_text(f"ERROR:\n{i} ({update.message.text}): You don't have permission to close that poll. Try again or /cancel.")
            return CHOOSING_POLL_CLOSE
        if('polls' in context.chat_data and context.user_data['polls'][i] in context.chat_data['polls']):
            context.chat_data['polls'].remove(context.user_data['polls'][i])
        if 'prompt' in context.user_data:
            context.user_data['prompt'].delete()
            del context.user_data['prompt']
        context.user_data['polls'][i].close(update.message.from_user)
        context.user_data['polls'].remove(context.user_data['polls'][i])
        del context.user_data['conversation_state']
        return ConversationHandler.END
    else:
        update.message.reply_text(f"ERROR:\n{i} ({update.message.text}): No such poll. Try again or /cancel.")
        context.user_data['conversation_state'] = CHOOSING_POLL_CLOSE
        return CHOOSING_POLL_CLOSE

def close_cancel(update, context):
    debug_log(update, context)
    if 'prompt' in context.user_data:
        context.user_data['prompt'].delete()
        del context.user_data['prompt']
    del context.user_data['conversation_state']
    return ConversationHandler.END



def add_poll_to_chat(update, context):
    debug_log(update, context)
    if(update.effective_chat.type == "private"):
        update.message.reply_text("Cannot add polls to private chats. Try adding a poll to a group or channel instead.")
        return ConversationHandler.END
    if(not 'polls' in context.chat_data):
        context.chat_data['polls'] = []
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.\nDo you want to /create a new one?")
        return ConversationHandler.END
    elif(context.user_data['polls'] == []):
        context.bot.send_message(update.message.from_user.id, "You don't have any open polls.\nDo you want to /create a new one?")
        return ConversationHandler.END
    else:
        kbd = []
        ctr = 0
        for poll in context.user_data['polls']:
            kbd.append([f"{ctr}: {poll.get_name()}\n"])
            ctr += 1
        kbd.append(["/cancel"])
        context.user_data['prompt'] = update.message.reply_text("Which poll would you like to add to this chat?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_ADD
        return CHOOSING_POLL_ADD

def add_poll_to_chat_choice(update, context):
    debug_log(update, context)
    i = int(update.message.text.split(':')[0])
    if context.user_data['polls'][i]:
        if(context.user_data['polls'][i] in context.chat_data['polls']):
            context.user_data['polls'][i].print(context.bot, update.effective_chat)
        else:
            context.chat_data['polls'].append(context.user_data['polls'][i])
            context.user_data['polls'][i].print(context.bot, update.effective_chat)
        if 'prompt' in context.user_data:
            context.user_data['prompt'].delete()
            del context.user_data['prompt']
        del context.user_data['conversation_state']
        return ConversationHandler.END
    else:
        update.message.reply_text(f"ERROR:\n{i}: {update.message.text} --- No such poll. Try again or /cancel.")
        return CHOOSING_POLL_ADD

def add_poll_to_chat_cancel(update, context):
    debug_log(update, context)
    if 'prompt' in context.user_data:
        context.user_data['prompt'].delete()
        del context.user_data['prompt']
    del context.user_data['conversation_state']
    return ConversationHandler.END



def print_poll(update, context):
    debug_log(update, context)
    if(update.effective_chat.type == "private"):
        if(not 'polls' in context.user_data):
            context.user_data['polls'] = []
            context.bot.send_message(update.message.from_user.id, "You aren't part of any open polls.\nDo you want to /create a new one?")
            return ConversationHandler.END
        if(context.user_data['polls'] == []):
            context.bot.send_message(update.message.from_user.id, "You aren't part of any open polls.\nDo you want to /create a new one?")
            return ConversationHandler.END
        data = context.user_data
    else:
        if(not 'polls' in context.chat_data):
            context.chat_data['polls'] = []
            context.bot.send_message(update.message.from_user.id, "There are no open polls in that chat.\nDid you mean to /add one?")
            return ConversationHandler.END
        if(context.chat_data['polls'] == []):
            context.bot.send_message(update.message.from_user.id, "There are no open polls in that chat.\nDid you mean to /add one?")
            return ConversationHandler.END
        data = context.chat_data
    kbd = []
    ctr = 0
    for poll in data['polls']:
        if(poll.is_open()):
            kbd.append([f"{ctr}: {poll.get_name()}\n"])
            ctr += 1
        else:
            data['polls'].remove(poll)
    if(ctr == 0):
        context.bot.send_message(update.message.from_user.id, "There are no open polls in that chat.\nDid you mean to /add one?")
        return ConversationHandler.END
    kbd.append(["/cancel"])
    update.message.reply_text("Which poll would you like to print again?", reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True, selective=True))
    context.user_data['conversation_state'] = CHOOSING_POLL_PRINT
    return CHOOSING_POLL_PRINT

def print_poll_choice(update, context):
    debug_log(update, context)
    if(update.effective_chat.type == "private"):
        data = context.user_data
    else:
        data = context.chat_data
    i = int(update.message.text.split(':')[0])
    if data['polls'][i]:
        data['polls'][i].print(context.bot, update.effective_chat)
        del context.user_data['conversation_state']
        return ConversationHandler.END
    else:
        update.message.reply_text(f"ERROR:\n{i}: {update.message.text} --- No such poll. Try again or /cancel.")
        return CHOOSING_POLL_PRINT

def print_poll_cancel(update, context):
    debug_log(update, context)
    update.message.reply_text("print_poll_cancel")
    del context.user_data['conversation_state']
    return ConversationHandler.END



def vote(update, context):
    debug_log(update, context)
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
    if(not 'polls' in context.chat_data):
        context.chat_data['polls'] = []
    for poll in context.chat_data['polls']:
        if poll.knows_msg(update.callback_query.message):
            if(not poll.is_open()):
                context.chat_data['polls'].remove(poll)
                if(poll in context.user_data['polls']):
                    context.user_data['polls'].remove(poll)
                context.bot.send_message(update.callback_query.from_user.id, "Voting for that poll has ended.")
                return ConversationHandler.END
            if(not poll in context.user_data['polls']):
                context.user_data['polls'].append(poll)
            context.user_data['active_poll'] = poll
            if(not update.effective_chat.type == "private"):
                poll.print(context.bot, Chat(update.callback_query.from_user.id, "private"), votable=False)
            prompt = context.bot.send_message(update.callback_query.from_user.id, f"Please enter your votes for \"{poll.get_name()}\":\n\n(Write a '+' for a column you want to agree to, a '-' for one you disagree with or a '?' for one you are not sure about. Everything alse gets ignored. Omitting votes will fill the remainder with '?'s, superfluous votes are discarded.\nYou can always correct your vote as long as the poll is still open.")
            context.user_data['active_poll_prompt'] = prompt
            return ConversationHandler.END
    for poll in context.user_data['polls']:
        if poll.knows_msg(update.callback_query.message):
            if(not poll.is_open()):
                context.user_data['polls'].remove(poll)
                if(poll in context.chat_data['polls']):
                    context.chat_data['polls'].remove(poll)
                context.bot.send_message(update.callback_query.from_user.id, "Voting for that poll has ended.")
                return ConversationHandler.END
            if(not poll in context.chat_data['polls']):
                context.chat_data['polls'].append(poll)
            context.user_data['active_poll'] = poll
            if(not update.effective_chat.type == "private"):
                poll.print(context.bot, Chat(update.callback_query.from_user.id, "private"), votable=False)
            prompt = context.bot.send_message(update.callback_query.from_user.id, f"Please enter your votes for \"{poll.get_name()}\":\n\n(Write a '+' for a column you want to agree to, a '-' for one you disagree with or a '?' for one you are not sure about. Everything alse gets ignored. Omitting votes will fill the remainder with '?'s, superfluous votes are discarded.\nYou can always correct your vote as long as the poll is still open.")
            context.user_data['active_poll_prompt'] = prompt
            return ConversationHandler.END
    context.bot.send_message(update.callback_query.from_user.id, "Something went wrong. Try adding this poll to the chat again.\nSorry for the inconvenience.")
    return ConversationHandler.END



def default_handler(update, context):
    debug_log(update, context)
    if('conversation_state' in context.user_data and context.user_data['conversation_state'] == TYPING_NAME ):
        if(update.message.text == "/cancel"):
            create_cancel(update,context)
        else:
            create_name(update,context)
        return
    if('conversation_state' in context.user_data and context.user_data['conversation_state'] == TYPING_LENGTH ):
        if(update.message.text == "/cancel"):
            create_cancel(update,context)
        else:
            create_length(update,context)
        return
    if('conversation_state' in context.user_data and context.user_data['conversation_state'] == TYPING_DESCRIPTION ):
        if(update.message.text == "/cancel"):
            create_cancel(update,context)
        else:
            create_description(update,context)
        return
    if('conversation_state' in context.user_data and context.user_data['conversation_state'] == CHOOSING_POLL_PRINT ):
        if(update.message.text == "/cancel"):
            print_poll_cancel(update,context)
        else:
            print_poll_choice(update,context)
        return
    if('conversation_state' in context.user_data and context.user_data['conversation_state'] == CHOOSING_POLL_CLOSE):
        if(update.message.text == "/cancel"):
            close_cancel(update,context)
        else:
            close_choice(update,context)
        return
    if('conversation_state' in context.user_data and context.user_data['conversation_state'] == CHOOSING_POLL_ADD):
        if(update.message.text == "/cancel"):
            add_poll_to_chat_cancel(update,context)
        else:
            add_poll_to_chat_choice(update,context)
        return
    if(update.effective_chat.type == "private"): 
        if('active_poll' in context.user_data):
            context.user_data['active_poll'].vote(update.message.from_user.name, update.message.text)
            context.user_data['active_poll'].update()
            del context.user_data['active_poll']
            context.user_data['active_poll_prompt'].delete()
            del context.user_data['active_poll_prompt']
            return ConversationHandler.END
        else:
            help(update,context)


def error(update, context):
    debug_log(update, context)
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def err(update, context):
    debug_log(update, context)
    update.message.reply_text("You should never see this message. If you do, please contact @Entropy0")


def main():
    global TOKEN
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

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("init", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("print", print_poll))
    dp.add_handler(CommandHandler("close", close))
    dp.add_handler(CommandHandler("reset", reset))

    dp.add_handler(MessageHandler(Filters.text, default_handler))

    create_handler = ConversationHandler(
        entry_points = [CommandHandler('create', create)],
        states = {
            TYPING_NAME:        [MessageHandler(Filters.text, create_name)],
            TYPING_LENGTH:      [MessageHandler(Filters.text, create_length)],
            TYPING_DESCRIPTION: [MessageHandler(Filters.text, create_description)]
        },
        fallbacks = [CommandHandler("reset", reset),
                     CommandHandler("cancel", create_cancel),
                     MessageHandler(Filters.text, err)],
        name = "creating_poll",
        persistent = False
    )
    dp.add_handler(create_handler)

    """edit_name_handler = ConversationHandler(
        entry_points = [CommandHandler('edit_name', create)],
        states = {
            CHOOSING_POLL_EDIT_NAME: [MessageHandler(Filters.text, edit_name_choice)],
            TYPING_POLL_EDIT_NAME:   [MessageHandler(Filters.text, edit_name_final)]
        },
        fallbacks = [CommandHandler("reset", reset),
                     CommandHandler("cancel", edit_name_cancel),
                     MessageHandler(Filters.text, err)],
        name = "editing_poll_name",
        persistent = False
    )
    dp.add_handler(edit_name_handler)

    edit_description_handler = ConversationHandler(
        entry_points = [CommandHandler('edit_description', create)],
        states = {
            CHOOSING_POLL_EDIT_DESCRIPTION: [MessageHandler(Filters.text, edit_description_choice)],
            TYPING_POLL_EDIT_DESCRIPTION:   [MessageHandler(Filters.text, edit_description_final)]
        },
        fallbacks = [CommandHandler("reset", reset),
                     CommandHandler("cancel", edit_description_cancel),
                     MessageHandler(Filters.text, err)],
        name = "editing_poll_description",
        persistent = False
    )
    dp.add_handler(edit_name_handler)"""

    closing_handler = ConversationHandler(
        entry_points = [CommandHandler('close', close)],
        states = {
            CHOOSING_POLL_CLOSE:  [MessageHandler(Filters.text, close_choice)]
        },
        fallbacks = [CommandHandler("reset", reset),
                     CommandHandler("cancel", close_cancel),
                     MessageHandler(Filters.text, err)],
        name = "closing_poll",
        persistent = False
    )
    dp.add_handler(closing_handler)

    adding_handler = ConversationHandler(
        entry_points = [CommandHandler('add', add_poll_to_chat)],
        states = {
            CHOOSING_POLL_ADD:  [MessageHandler(Filters.text, add_poll_to_chat_choice)]
        },
        fallbacks = [CommandHandler("reset", reset),
                     CommandHandler("cancel", add_poll_to_chat_cancel),
                     MessageHandler(Filters.text, err)],
        name = "adding_poll",
        persistent = False
    )
    dp.add_handler(adding_handler)

    printing_handler = ConversationHandler(
        entry_points = [CommandHandler('print', print_poll)],
        states = {
            CHOOSING_POLL_PRINT:  [MessageHandler(Filters.text, print_poll_choice)]
        },
        fallbacks = [CommandHandler("reset", reset),
                     CommandHandler("cancel", print_poll_cancel),
                     MessageHandler(Filters.text, err)],
        name = "printing_poll",
        persistent = False
    )
    dp.add_handler(printing_handler)

    dp.add_handler(CallbackQueryHandler(vote, pass_user_data=True, pass_chat_data=True))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()