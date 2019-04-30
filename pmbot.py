import pm
import random
import requests
import subprocess
import telebot
from telebot import types
import tempfile
from decouple import config
from shutil import copyfile

# general strings
OK_MESSAGES = ["Understood", "I'm on it!", "Let's do this, ok"]
DONE_MENU = "\u2705 Done!"

API_TOKEN = config('API_TOKEN')
R_SCRIPT = config('R_SCRIPT')
R_SCRIPTS_FOLDER = config('R_SCRIPTS_FOLDER')

STATUS_TYPING = "typing"
STATUS_UPLOAD_PICTURE = "upload_photo"

bot = telebot.TeleBot(API_TOKEN)
lock = dict()


def start_processing(message, no_positive_message=False):
    chat_id = message.chat.id
    if chat_id in lock and lock[chat_id]:
        bot.reply_to(message, "I'm already busy right now!\nPlease wait for the previous command to complete \u23F3")
        return True
    if not no_positive_message:
        bot.send_message(chat_id, random.choice(OK_MESSAGES))
    lock[chat_id] = True
    return False


def end_processing(message):
    lock[message.chat.id] = False


@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Hi, and welcome to the Process Mining Bot!")
    bot.send_message(chat_id, "Let me start our conversation by sharing a dummy log that you can use to test my capabilities...")
    bot.send_document(chat_id, open("logs/firstLog.xes.gz", "rb"))
    copyfile("logs/firstLog.xes.gz", pm.get_log_filename(chat_id))
    pm.set_property(chat_id, "current_log", pm.get_log_filename(chat_id))
    pm.set_property(chat_id, "log_original_name", "firstLog.xes.gz")
    bot.send_message(chat_id, "If you want, you can also share another log with me, simply by uploading it here")


@bot.message_handler(content_types=['document'])
def new_log_file(message):
    if message.document.mime_type == "application/gzip" or message.document.mime_type == "application/x-gzip":
        bot.send_chat_action(message.chat.id, STATUS_TYPING)
        file_info = bot.get_file(message.document.file_id)
        file = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(API_TOKEN, file_info.file_path))
        pm.set_log(message.chat.id, file.content, message.document.file_name)
        bot.send_message(message.chat.id, "Thanks, I received the new log!")
    else:
        bot.reply_to(message, "Currently, I support only <code>.xes.gz</code> files, sorry!", parse_mode="html")


@bot.message_handler(commands=['describelog'])
def describe_log(message):
    if start_processing(message): return
    bot.send_chat_action(message.chat.id, STATUS_TYPING)
    description = pm.describe_log(message.chat.id)
    textual_description = "<b>Total number of traces:</b> " + str(description["traces"]) + "\n"
    textual_description += "<b>Activities with frequencies</b>:\n"
    for a in description["acts_freq"]:
        textual_description += " - " + a + ": " + str(description["acts_freq"][a]) + "\n"
    bot.send_message(message.chat.id, textual_description, parse_mode="html")
    bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
    if description["case_duration"] is not None:
        bot.send_photo(message.chat.id, open(description["case_duration"], "rb"))
    if description["events_over_time"] is not None:
        bot.send_photo(message.chat.id, open(description["events_over_time"], "rb"))
    end_processing(message)


@bot.message_handler(commands=['alpha'])
def alpha_miner(message):
    if start_processing(message): return
    bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
    model = pm.bot_alpha_miner(message.chat.id)
    bot.send_photo(message.chat.id, open(model, "rb"))
    end_processing(message)


@bot.message_handler(commands=['dfg'])
def dependency_graph(message):
    if start_processing(message): return
    bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
    model = pm.bot_dfg(message.chat.id)
    bot.send_photo(message.chat.id, open(model, "rb"))
    end_processing(message)


@bot.message_handler(commands=['hm'])
def hm(message):
    if start_processing(message): return
    args = message.text.split()
    dep_threshold = 0.99
    if len(args) == 2:
        try:
            dep_threshold = float(args[1])
        except ValueError:
            pass
    bot.send_chat_action(message.chat.id, STATUS_UPLOAD_PICTURE)
    models = pm.bot_hm(message.chat.id, dependency_threshold=dep_threshold)
    for m in models:
        bot.send_photo(message.chat.id, open(m, "rb"))
    end_processing(message)


@bot.message_handler(commands=['dottedchart'])
def dotted_chart(message):
    if start_processing(message): return
    new_file, filename = tempfile.mkstemp(suffix="png")
    subprocess.run([R_SCRIPT,
                    R_SCRIPTS_FOLDER + "static_dotted_chart.R",
                    pm.get_property(message.chat.id, "current_log"),
                    filename])
    bot.send_photo(message.chat.id, open(filename, "rb"))
    end_processing(message)


@bot.message_handler(commands=['relativedottedchart'])
def relative_dotted_chart(message):
    if start_processing(message): return
    new_file, filename = tempfile.mkstemp(suffix="png")
    subprocess.run([R_SCRIPT,
                    R_SCRIPTS_FOLDER + "relative_dotted_chart.R",
                    pm.get_property(message.chat.id, "current_log"),
                    filename])
    bot.send_photo(message.chat.id, open(filename, "rb"))
    end_processing(message)


@bot.message_handler(commands=['precedencematrix'])
def precedence_matrix(message):
    if start_processing(message): return
    new_file, filename = tempfile.mkstemp(suffix="png")
    subprocess.run([R_SCRIPT,
                    R_SCRIPTS_FOLDER + "precedence_matrix.R",
                    pm.get_property(message.chat.id, "current_log"),
                    filename])
    bot.send_photo(message.chat.id, open(filename, "rb"))
    end_processing(message)


@bot.message_handler(commands=['keepactivities'])
def filter_per_activities_to_keep(message):

    def _filter(msg):
        if msg.text == DONE_MENU:
            if start_processing(message, no_positive_message=True): return
            bot.send_message(chat_id, random.choice(OK_MESSAGES), reply_markup=types.ReplyKeyboardRemove(selective=False))
            pm.filter_per_activities_to_keep(replied_message.chat.id, activities_to_keep)
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
    replied_message = bot.send_message(chat_id, "Select which activities you want to keep:", reply_markup=markup)
    bot.register_next_step_handler(replied_message, _filter)
    end_processing(message)


@bot.message_handler(commands=['removefilters'])
def revert_filter(message):
    if start_processing(message, no_positive_message=True): return
    chat_id = message.chat.id
    pm.set_property(chat_id, "current_log", pm.get_log_filename(chat_id, False))
    bot.send_message(message.chat.id, "I restored the log to its original form")
    end_processing(message)


print("Started")
bot.polling()
