import pm
import random
import rexecutor
import requests
import telebot
from telebot import types
from decouple import config
from shutil import copyfile

# general strings
OK_MESSAGES = [
    "Understood",
    "I'm on it!",
    "Let's do this, ok",
    "Sure, no problem...",
    "Great idea! Let me do this...",
    "Seems doable, let me do it...",
    "I'll give this a try...",
    "Seems legit \u263A, I'm on it"]
DONE_MENU = "\u2705 Done!"

API_TOKEN = config('API_TOKEN')
R_SCRIPT = config('R_SCRIPT')
R_SCRIPTS_FOLDER = config('R_SCRIPTS_FOLDER')
MAX_FILE_SIZE_IN_MB = int(config('MAX_FILE_SIZE_IN_MB'))

STATUS_TYPING = "typing"
STATUS_UPLOAD_PICTURE = "upload_photo"

bot = telebot.TeleBot(API_TOKEN)
lock = dict()


def check_registration(message):
    if pm.get_property(message.chat.id, "registered"):
        return True
    else:
        bot.send_chat_action(message.chat.id, STATUS_TYPING)
        bot.reply_to(message, "This session is not started, please start it with the /start command")
        return False


def start_processing(message, no_positive_message=False):
    chat_id = message.chat.id
    if chat_id in lock and lock[chat_id]:
        bot.send_chat_action(message.chat.id, STATUS_TYPING)
        bot.reply_to(message, "I'm already busy right now!\nPlease wait for the previous command to complete \u23F3")
        return True
    if not no_positive_message:
        bot.send_chat_action(message.chat.id, STATUS_TYPING)
        bot.send_message(chat_id, random.choice(OK_MESSAGES))
    lock[chat_id] = True
    return False


def end_processing(message):
    lock[message.chat.id] = False


@bot.message_handler(commands=['start'])
def send_welcome(message):
    def _registration(message):
        if message.text == "1":
            bot.send_chat_action(message.chat.id, STATUS_TYPING)
            bot.send_message(chat_id, "Excellent, thanks!")
            bot.send_message(chat_id, "Let me start our conversation by sharing a dummy log that you can use to test my capabilities...")
            bot.send_document(chat_id, open("logs/firstLog.xes", "rb"))
            copyfile("logs/firstLog.xes", pm.get_log_filename(chat_id))
            pm.set_property(chat_id, "current_log", pm.get_log_filename(chat_id))
            pm.set_property(chat_id, "log_original_name", "firstLog.xes")
            bot.send_message(chat_id, "If you want, you can also share another log with me, simply by uploading it here")
            pm.set_property(chat_id, "registered", True)
        else:
            bot.send_chat_action(message.chat.id, STATUS_TYPING)
            bot.reply_to(message, "I'm sorry, this license code is not correct \u2639")
            pm.set_property(chat_id, "registered", False)

    chat_id = message.chat.id
    bot.send_chat_action(message.chat.id, STATUS_TYPING)
    bot.send_message(chat_id, "Hi " + message.from_user.first_name + ", and welcome to the Process Mining Bot!")
    markup = types.ForceReply(selective=False)
    license = bot.send_message(chat_id, "I need to know your license code: (a valid code is \"1\")", reply_markup=markup)
    bot.register_next_step_handler(license, _registration)


@bot.message_handler(content_types=['document'])
def new_log_file(message):
    if check_registration(message):
        if message.document.mime_type == "application/xml" and message.document.file_name.split(".")[-1] == "xes":
            if int(message.document.file_size) <= (MAX_FILE_SIZE_IN_MB * 1000000):
                file_info = bot.get_file(message.document.file_id)
                file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(API_TOKEN, file_info.file_path))
                pm.set_log(message.chat.id, file.content, message.document.file_name)
                bot.send_chat_action(message.chat.id, STATUS_TYPING)
                bot.send_message(message.chat.id, "Thanks, I received the new log!")
            else:
                bot.send_chat_action(message.chat.id, STATUS_TYPING)
                bot.reply_to(message, "Ops, currently, I support only files smaller than " + str(MAX_FILE_SIZE_IN_MB) + "MB")
        else:
            bot.send_chat_action(message.chat.id, STATUS_TYPING)
            bot.reply_to(message, "Currently, I support only <code>.xes</code> files, sorry!", parse_mode="html")


@bot.message_handler(commands=['describelog'])
def describe_log(message):
    if check_registration(message):
        if start_processing(message): return
        description = pm.describe_log(message.chat.id)
        textual_description = "<b>Total number of traces:</b> " + str(description["traces"]) + "\n"
        textual_description += "<b>Activities with frequencies</b>:\n"
        for a in description["acts_freq"]:
            textual_description += " - " + a + ": " + str(description["acts_freq"][a]) + "\n"
        bot.send_chat_action(message.chat.id, STATUS_TYPING)
        bot.send_message(message.chat.id, textual_description, parse_mode="html")
        if description["case_duration"] is not None:
            bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
            bot.send_photo(message.chat.id, open(description["case_duration"], "rb"))
        if description["events_over_time"] is not None:
            bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
            bot.send_photo(message.chat.id, open(description["events_over_time"], "rb"))
        end_processing(message)


@bot.message_handler(commands=['alpha'])
def alpha_miner(message):
    if check_registration(message):
        if start_processing(message): return
        bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
        model = pm.bot_alpha_miner(message.chat.id)
        bot.send_photo(message.chat.id, open(model, "rb"))
        end_processing(message)


@bot.message_handler(commands=['dfg'])
def dependency_graph(message):
    if check_registration(message):
        if start_processing(message): return
        bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
        model = pm.bot_dfg(message.chat.id)
        bot.send_photo(message.chat.id, open(model, "rb"))
        end_processing(message)


@bot.message_handler(commands=['hm'])
def hm(message):
    if check_registration(message):
        if start_processing(message): return
        args = message.text.split()
        dep_threshold = 0.99
        if len(args) == 2:
            try:
                dep_threshold = float(args[1])
            except ValueError:
                pass
        models = pm.bot_hm(message.chat.id, dependency_threshold=dep_threshold)
        for m in models:
            bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
            bot.send_photo(message.chat.id, open(m, "rb"))
        end_processing(message)


@bot.message_handler(commands=['dottedchart'])
def dotted_chart(message):
    if check_registration(message):
        if start_processing(message): return
        pic = rexecutor.run_r_code(R_SCRIPT,
                                   R_SCRIPTS_FOLDER + "static_dotted_chart.R",
                                   pm.get_property(message.chat.id, "current_log"))
        bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
        bot.send_photo(message.chat.id, open(pic, "rb"))
        end_processing(message)


@bot.message_handler(commands=['relativedottedchart'])
def relative_dotted_chart(message):
    if check_registration(message):
        if start_processing(message): return
        pic = rexecutor.run_r_code(R_SCRIPT,
                                   R_SCRIPTS_FOLDER + "relative_dotted_chart.R",
                                   pm.get_property(message.chat.id, "current_log"))
        bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
        bot.send_photo(message.chat.id, open(pic, "rb"))
        end_processing(message)


@bot.message_handler(commands=['precedencematrix'])
def precedence_matrix(message):
    if check_registration(message):
        if start_processing(message): return
        pic = rexecutor.run_r_code(R_SCRIPT,
                                   R_SCRIPTS_FOLDER + "precedence_matrix.R",
                                   pm.get_property(message.chat.id, "current_log"))
        bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
        bot.send_photo(message.chat.id, open(pic, "rb"))
        end_processing(message)


@bot.message_handler(commands=['resources'])
def precedence_matrix(message):
    if check_registration(message):
        if start_processing(message): return
        pic = rexecutor.run_r_code(R_SCRIPT,
                                   R_SCRIPTS_FOLDER + "resource_frequencies.R",
                                   pm.get_property(message.chat.id, "current_log"))
        bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
        bot.send_photo(message.chat.id, open(pic, "rb"))
        end_processing(message)


@bot.message_handler(commands=['keepactivities'])
def filter_per_activities_to_keep(message):
    if check_registration(message):
        def _filter(msg):
            if msg.text == DONE_MENU:
                if start_processing(message, no_positive_message=True): return
                bot.send_chat_action(message.chat.id, STATUS_TYPING)
                bot.send_message(chat_id, random.choice(OK_MESSAGES), reply_markup=types.ReplyKeyboardRemove(selective=False))
                pm.filter_per_activities_to_keep(replied_message.chat.id, activities_to_keep)
                bot.send_chat_action(message.chat.id, STATUS_TYPING)
                bot.send_message(message.chat.id, "I applied the filter")
                end_processing(message)
            else:
                activities_to_keep.append(msg.text)
                bot.register_next_step_handler(msg, _filter)

        if start_processing(message, no_positive_message=True): return
        activities_to_keep = []
        chat_id = message.chat.id
        activities = pm.get_all_activities(chat_id)
        markup = types.ReplyKeyboardMarkup(row_width=1)
        for a in activities:
            markup.add(a)
        markup.add(DONE_MENU)
        bot.send_chat_action(message.chat.id, STATUS_TYPING)
        replied_message = bot.send_message(chat_id, "Select which activities you want to keep:", reply_markup=markup)
        bot.register_next_step_handler(replied_message, _filter)
        end_processing(message)


@bot.message_handler(commands=['removefilters'])
def revert_filter(message):
    if check_registration(message):
        if start_processing(message, no_positive_message=True): return
        chat_id = message.chat.id
        pm.reset_filter(chat_id)
        bot.send_chat_action(chat_id, STATUS_TYPING)
        bot.send_message(chat_id, "I restored the log to its original form")
        end_processing(message)


print("Started")
bot.polling()
