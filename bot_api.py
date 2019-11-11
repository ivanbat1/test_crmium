import logging
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, RegexHandler
import odoorpc
import itertools
import sqlite3

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

MONITORING, CHANGE_DATA, UPDATE_DATA = range(3)

start_message = """This bot is monitoring Odoo leads
pleas enter you data in this format:
db_name, login, password
and i connect to you account"""

start_message_v2 = """This bot is monitoring Odoo leads
Your information is already stored in the database:
db_name = {},
login = {},
password = {}
Do you want to change it?"""

db_name_prj = 'TestDB.db'

# Prepare the connection to the server
# odoo = odoorpc.ODOO('localhost', port=8069)
# bot TOKEN to connect
TOKEN = "733869210:AAGp_7UWMW-7HWdj78zRqY3DAFL9ZW_4tnk"
# data = ['api', 'baturin.ivan9@gmail.com', 'Ivanbaturin1999']


class Monitor():
    crm = []
    odoo = None
    search = []

    def __init__(self, db, login, pasw):
        self.db, self.login, self.pasw = db, login, pasw

    def log(self):
        """profile authorization odoo"""
        self.odoo = odoorpc.ODOO('localhost', port=8069)
        self.odoo.login(self.db, self.login, self.pasw)

    def find(self):
        """search settings"""
        self.search = self.odoo.execute_kw('crm.lead', 'search',
                                           [[['active', '=', True], ['stage_id', '=', 'completed']]])

    def once_crm(self):
        self.crm = self.odoo.execute_kw('crm.lead', 'read', [self.search]
                                        , {
                                            'fields': ['display_name', 'partner_address_email', 'stage_id',
                                                       'team_id',
                                                       'type',
                                                       'user_email', 'write_uid', 'create_date',
                                                       "date_last_stage_update"]
                                        }
                                        )

    def monitor(self, update):
        """monitoring completed task"""
        print('tyt')
        print(self.search)
        new_crm = self.odoo.execute_kw('crm.lead', 'read', [self.search]
                                       , {
                                           'fields': ['display_name', 'partner_address_email', 'stage_id',
                                                      'team_id',
                                                      'type',
                                                      'user_email', 'write_uid', 'create_date',
                                                      "date_last_stage_update"]
                                       }
                                       )
        if len(new_crm) > len(self.crm):
            res = list(itertools.filterfalse(lambda i: i in self.crm, new_crm)) \
                  + list(itertools.filterfalse(lambda j: j in new_crm, self.crm))
            message = f'the task {res[0]["display_name"]} was completed at {res[0]["date_last_stage_update"]}'
            print(message)
            update.message.reply_text(message)
        self.crm = new_crm


def start(bot, update):
    """the first step is to check if the user is in db"""
    global start_message
    conn = sqlite3.connect(db_name_prj)
    cur = conn.cursor()
    if [i for i in cur.execute("SELECT login, password, db_name FROM CLIENTS WHERE chat_id=?",
                               (str(update.message.chat_id),))]:
        print('user have')
        login, password, db_name = \
            [i for i in cur.execute("SELECT login, password, db_name FROM CLIENTS WHERE chat_id=?",
                                    (str(update.message.chat_id),))][0]
        update.message.reply_text(start_message_v2.format(db_name, login, password), reply_markup=ReplyKeyboardMarkup(
            [['/monitoring'], ['/set']]))
        conn.commit()
        return MONITORING
    else:
        update.message.reply_text(start_message, reply_markup=ReplyKeyboardMarkup(
            [['/set']]))
        return CHANGE_DATA


def set_data(bot, update):
    """if after the first step user print any text
     the program will offer to change the data or add to the db if the data is correct"""
    conn = sqlite3.connect(db_name_prj)
    cur = conn.cursor()
    if not [i for i in cur.execute("SELECT login, password, db_name FROM CLIENTS WHERE chat_id=?",
                                   (str(update.message.chat_id),))]:
        db_name, login, password = update.message.text.split(', ')
        cur.execute("INSERT INTO CLIENTS(chat_id, login, password, db_name) values (?, ?, ?, ?)",
                    (str(update.message.chat_id), login, password, db_name,))
        conn.commit()
        print(db_name, login, password)
        update.message.reply_text('Data was added')
        return MONITORING
    else:
        login, password, db_name = \
            [i for i in cur.execute("SELECT login, password, db_name FROM CLIENTS WHERE chat_id=?",
                                    (str(update.message.chat_id),))][0]
        update.message.reply_text(
            f"""Your information is already stored in the database:
            db_name = {db_name},
            login = {login},
            password = {password},
            Do you want to change it?""",
            reply_markup=ReplyKeyboardMarkup(
                [['/yes'], ['/no']]))
        conn.commit()
        return CHANGE_DATA


def take_data(bot, update):
    """the program requests user data"""
    update.message.reply_text('''Enter your data in this format:
    db_name, login, password''')
    return UPDATE_DATA


def change_data(bot, update):
    """change if there is no user or come in if the user was"""
    conn = sqlite3.connect(db_name_prj)
    cur = conn.cursor()
    db_name, login, password = update.message.text.split(', ')
    if [i for i in cur.execute("SELECT login, password, db_name FROM CLIENTS WHERE chat_id=?",
                               (str(update.message.chat_id),))]:
        cur.execute("UPDATE CLIENTS SET login=?, password=?, db_name=? WHERE chat_id=?",
                    (login, password, db_name, str(update.message.chat_id)))
        conn.commit()
    else:
        cur.execute("INSERT INTO CLIENTS(chat_id, login, password, db_name) values (?, ?, ?, ?)",
                    (str(update.message.chat_id), login, password, db_name,))
        conn.commit()
    update.message.reply_text('Data updated, you can start monitoring', reply_markup=ReplyKeyboardMarkup(
        [['/monitoring'], ['/set']]))
    return MONITORING


def stay_data(bot, update):
    """user refused changes"""
    update.message.reply_text('Data was not updated', reply_markup=ReplyKeyboardMarkup(
            [['/monitoring'], ['/set']]))
    return MONITORING


def stop(bot, update, job_queue):
    """stop monitoring"""
    job_queue.stop()
    update.message.reply_text('stop', reply_markup=ReplyKeyboardMarkup(
        [['/monitoring'], ['/set']]))
    return MONITORING


def monitoring(bot, job):
    """loop monitoring"""
    job.context['m'].find()
    job.context['m'].monitor(job.context['update'])


def time(bot, update, job_queue):
    """start monitoring"""
    print(update.message.chat_id)
    conn = sqlite3.connect(db_name_prj)
    cur = conn.cursor()
    if [i for i in cur.execute("SELECT login, password, db_name FROM CLIENTS WHERE chat_id=?",
                               (str(update.message.chat_id),))]:
        login, password, db_name = \
            [i for i in cur.execute("SELECT login, password, db_name FROM CLIENTS WHERE chat_id=?",
                                    (str(update.message.chat_id),))][0]
        print(login, password, db_name)
        m = Monitor(db_name, login, password)
        try:
            m.log()

        except odoorpc.error.RPCError as ex:
            update.message.reply_text(f'{ex} stop monitoring and set correct data')
            return MONITORING
        m.find()
        m.once_crm()
        job_queue.start()
        job_queue.run_repeating(monitoring, 1,
                                      context={"update": update, 'm': m})
        update.message.reply_text('start', reply_markup=ReplyKeyboardMarkup(
            [['/stop']]))
    return MONITORING


def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            MONITORING: [MessageHandler(Filters.text, set_data),
                         CommandHandler('monitoring', time, pass_job_queue=True),
                         CommandHandler('stop', stop, pass_job_queue=True),
                         CommandHandler(['yes', 'set'], take_data)
                         ],
            CHANGE_DATA: [CommandHandler(['yes', 'set'], take_data),
                          CommandHandler('no', stay_data),
                          ],
            UPDATE_DATA: [MessageHandler(Filters.text, change_data), ]
        },
        fallbacks=[]
    )
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
