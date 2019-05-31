#!/usr/bin/python3

import logging
import parser, poll

from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, CallbackQueryHandler, Filters, PicklePersistence
from telegram import ParseMode, ReplyKeyboardMarkup, Chat

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "<your-token-here>"

TYPING_NAME, TYPING_LENGTH, CHOOSING_POLL_ADD, CHOOSING_POLL_CLOSE, CHOOSING_POLL_PRINT = range(5)




def start(update, context):
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
    if(not 'polls' in context.chat_data):
        context.chat_data['polls'] = []

def help(update, context):
    update.message.reply_text('Welcome to *schedubot* (barebones version)!\n\nCurrently, this bot supports the following commands:\n\n/create Create a new poll.\n/add Add a poll you have created or participated in to current chat.\n/print Send a new message for a poll already added to this chat.\n/close Close a poll you created.\n/help Print this message.', parse_mode=ParseMode.MARKDOWN)



def create(update,context):
    if(update.effective_chat.type != "private"):
        context.bot.send_message(update.message.from_user.id, "To reduce spam, please create polls here first and then add them to your group(s).")
        return ConversationHandler.END
    if(not 'polls' in context.user_data):
        context.user_data['polls'] = []
    update.message.reply_text("Please enter the name for your poll:")
    context.user_data['conversation_state'] = TYPING_NAME
    return TYPING_NAME

def create_name(update,context):
    context.user_data['create_name'] = update.message.text
    update.message.reply_text("Please enter how many columns your poll should include:")
    context.user_data['conversation_state'] = TYPING_LENGTH
    return TYPING_LENGTH

def create_length(update,context):
    context.user_data['create_length'] = update.message.text
    if(not context.user_data['create_length'].isdigit() or int(context.user_data['create_length']) <= 0):
        update.message.reply_text("Please enter a number.")
        return TYPING_LENGTH
    _poll = poll.Poll(context.user_data['create_name'], update.message.from_user, context.user_data['create_length'])
    context.user_data['polls'].append(_poll)
    _poll.print(context.bot, update.effective_chat)
    update.message.reply_text(f"Created poll named {context.user_data['create_name']} with {context.user_data['create_length']} columns.\nYou can now use /add this poll to whichever chat(s) you want to use it in.")
    del context.user_data['conversation_state']
    return ConversationHandler.END

def create_cancel(update,context):
    update.message.reply_text("Stopped creating new poll.")
    del context.user_data['conversation_state']
    return ConversationHandler.END



def close(update,context):
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
        msg = "Which of your polls would you like to close?"
        polls = []
        kbd = []
        ctr = 0
        for poll in context.user_data['polls']:
            if(poll.get_creator().id == update.message.from_user.id):
                msg += f"{ctr}: {poll.get_name()}\n"
                kbd.append([f"{ctr}: {poll.get_name()}\n"])
            ctr += 1
        if(kbd == []):
            update.message.reply_text("You don't have any open polls.")
            del context.user_data['conversation_state']
            return ConversationHandler.END
        kbd.append(["/cancel"])
        context.user_data['prompt'] = update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_CLOSE
        return CHOOSING_POLL_CLOSE

def close_choice(update,context):
    if context.user_data['prompt']:
        context.user_data['prompt'].delete()
        del context.user_data['prompt']
    i = int(update.message.text.split(':')[0])
    if context.user_data['polls'][i]:
        if not context.user_data['polls'][i].get_creator().id == update.message.from_user.id:
            update.message.reply_text(f"ERROR:\n{i} ({update.message.text}): You don't have permission to close that poll. Try again or /cancel.")
            return CHOOSING_POLL_CLOSE
        if('polls' in context.chat_data and context.user_data['polls'][i] in context.chat_data['polls']):
            context.chat_data['polls'].remove(context.user_data['polls'][i])
        context.user_data['polls'][i].close(update.message.from_user)
        context.user_data['polls'].remove(context.user_data['polls'][i])
        del context.user_data['conversation_state']
        return ConversationHandler.END
    else:
        update.message.reply_text(f"ERROR:\n{i} ({update.message.text}): No such poll. Try again or /cancel.")
        context.user_data['conversation_state'] = CHOOSING_POLL_CLOSE
        return CHOOSING_POLL_CLOSE

def close_cancel(update,context):
    if context.user_data['prompt']:
        context.user_data['prompt'].delete()
        del context.user_data['prompt']
    del context.user_data['conversation_state']
    return ConversationHandler.END



def add_poll_to_chat(update,context):
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
        msg = "Which poll would you like to add to this chat?\n"
        polls = []
        kbd = []
        ctr = 0
        for poll in context.user_data['polls']:
            msg += f"{ctr}: {poll.get_name()}\n"
            kbd.append([f"{ctr}: {poll.get_name()}\n"])
            ctr += 1
        kbd.append(["/cancel"])
        context.user_data['prompt'] = update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True))
        context.user_data['conversation_state'] = CHOOSING_POLL_ADD
        return CHOOSING_POLL_ADD

def add_poll_to_chat_choice(update,context):
    if context.user_data['prompt']:
        context.user_data['prompt'].delete()
        del context.user_data['prompt']
    i = int(update.message.text.split(':')[0])
    if context.user_data['polls'][i]:
        if(context.user_data['polls'][i] in context.chat_data['polls']):
            context.user_data['polls'][i].print(context.bot, update.effective_chat)
        else:
            context.chat_data['polls'].append(context.user_data['polls'][i])
            context.user_data['polls'][i].print(context.bot, update.effective_chat)
        del context.user_data['conversation_state']
        return ConversationHandler.END
    else:
        update.message.reply_text(f"ERROR:\n{i}: {update.message.text} --- No such poll. Try again or /cancel.")
        return CHOOSING_POLL_ADD

def add_poll_to_chat_cancel(update,context):
    if context.user_data['prompt']:
        context.user_data['prompt'].delete()
        del context.user_data['prompt']
    del context.user_data['conversation_state']
    return ConversationHandler.END



def print_poll(update,context):
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
    
    msg = "Which poll would you like to print again?\n"
    polls = []
    kbd = []
    ctr = 0
    for poll in data['polls']:
        if(poll.is_open()):
            msg += f"{ctr}: {poll.get_name()}\n"
            kbd.append([f"{ctr}: {poll.get_name()}\n"])
            ctr += 1
        else:
            data['polls'].remove(poll)
    if(ctr == 0):
        context.bot.send_message(update.message.from_user.id, "There are no open polls in that chat.\nDid you mean to /add one?")
        return ConversationHandler.END
    kbd.append(["/cancel"])
    update.message.reply_text(msg, reply_markup=ReplyKeyboardMarkup(kbd, one_time_keyboard=True))
    context.user_data['conversation_state'] = CHOOSING_POLL_PRINT
    return CHOOSING_POLL_PRINT

def print_poll_choice(update,context):
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

def print_poll_cancel(update,context):
    update.message.reply_text("print_poll_cancel")
    del context.user_data['conversation_state']
    return ConversationHandler.END



def vote(update,context):
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
                return False
            if(not poll in context.user_data['polls']):
                context.user_data['polls'].append(poll)
            context.user_data['active_poll'] = poll
            if(not update.effective_chat.type == "private"):
                poll.print(context.bot, Chat(update.callback_query.from_user.id, "private"), votable=False)
            prompt = context.bot.send_message(update.callback_query.from_user.id, f"Please enter your votes for \"{poll.get_name()}\":\n\n(Write a '+' for a column you want to agree to, a '-' for one you disagree with or a '?' for one you are not sure about. Everything alse gets ignored. Omitting votes will fill the remainder with '?'s, superfluous votes are discarded.\nYou can always correct your vote as long as the poll is still open.")
            context.user_data['active_poll_prompt'] = prompt
            return True
    for poll in context.user_data['polls']:
        if poll.knows_msg(update.callback_query.message):
            if(not poll.is_open()):
                context.user_data['polls'].remove(poll)
                if(poll in context.chat_data['polls']):
                    context.chat_data['polls'].remove(poll)
                context.bot.send_message(update.callback_query.from_user.id, "Voting for that poll has ended.")
                return False
            if(not poll in context.chat_data['polls']):
                context.chat_data['polls'].append(poll)
            context.user_data['active_poll'] = poll
            if(not update.effective_chat.type == "private"):
                poll.print(context.bot, Chat(update.callback_query.from_user.id, "private"), votable=False)
            prompt = context.bot.send_message(update.callback_query.from_user.id, f"Please enter your votes for \"{poll.get_name()}\":\n\n(Write a '+' for a column you want to agree to, a '-' for one you disagree with or a '?' for one you are not sure about. Everything alse gets ignored. Omitting votes will fill the remainder with '?'s, superfluous votes are discarded.\nYou can always correct your vote as long as the poll is still open.")
            context.user_data['active_poll_prompt'] = prompt
            return True
    context.bot.send_message(update.callback_query.from_user.id, "Something went wrong. Try adding this poll to the chat again.\nSorry for the inconvenience.")
    return False



def default_handler(update, context):
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
            return
        else:
            help(update,context)


def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def err(update,context):
    update.message.reply_text("You should never see this message. If you do, please contact @Entropy0")


def main():
    pp = PicklePersistence(filename='schedubot_persistence')
    updater = Updater(TOKEN, persistence=pp, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("init", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("print", print_poll))
    dp.add_handler(CommandHandler("close", close))

    dp.add_handler(MessageHandler(Filters.text, default_handler))

    create_handler = ConversationHandler(
        entry_points = [CommandHandler('create', create)],
        states = {
            TYPING_NAME:   [MessageHandler(Filters.text, create_name)],
            TYPING_LENGTH: [MessageHandler(Filters.text, create_length)]
        },
        fallbacks = [CommandHandler("cancel", create_cancel),
                     MessageHandler(Filters.text, err)],
        name = "creating_poll",
        persistent = False
    )
    dp.add_handler(create_handler)

    closing_handler = ConversationHandler(
        entry_points = [CommandHandler('close', close)],
        states = {
            CHOOSING_POLL_CLOSE:  [MessageHandler(Filters.text, close_choice)]
        },
        fallbacks = [CommandHandler("cancel", close_cancel),
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
        fallbacks = [CommandHandler("cancel", add_poll_to_chat_cancel),
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
        fallbacks = [CommandHandler("cancel", print_poll_cancel),
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
