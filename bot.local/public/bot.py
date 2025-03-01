import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder,  Updater, CommandHandler, CallbackContext, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from sqlalchemy import create_engine, Column, Integer, String, Sequence, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import WebAppInfo
import requests
import urllib.request
from dotenv import load_dotenv 

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not os.path.exists('data'):
    os.makedirs('data')

engine = create_engine('sqlite:///data/users.db', echo=True)
Base = declarative_base()

class Achievement(Base):
    __tablename__ = 'achievements'
    id = Column(Integer, Sequence('achievement_id_seq'), primary_key=True)
    title = Column(String(100))
    description = Column(String(500))
    icon = Column(String(100))

class UserAchievement(Base):
    __tablename__ = 'user_achievements'
    id = Column(Integer, Sequence('user_achievement_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    achievement_id = Column(Integer, ForeignKey('achievements.id'))
    achieved_at = Column(DateTime, default=datetime.utcnow)  # Дата получения

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    username = Column(String(50))
    first_name = Column(String(50))
    last_name = Column(String(50))
    chat_id = Column(Integer)
    role = Column(String(50), default="employee")
    point = Column(Integer, default=0)
    achievements = relationship('Achievement', secondary='user_achievements', backref='users')


class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, Sequence('task_id_seq'), primary_key=True)
    title = Column(String(100))
    description = Column(String(500))
    reward = Column(Integer)
    assigned_to = Column(Integer)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_by = Column(Integer, default=0)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

class TaskState:
    TITLE = 1
    DESCRIPTION = 2
    REWARD = 3

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user = update.message.from_user
        chat_id = update.message.chat_id
    elif update.callback_query:
        user = update.callback_query.from_user
        chat_id = update.callback_query.message.chat_id
        profile_button = InlineKeyboardButton(
        text="Профиль",
        web_app=WebAppInfo(url=f"https://bot.local/web/profile.html?username={user.username}"))
    else:
        return

    existing_user = session.query(User).filter_by(chat_id=chat_id).first()
    if existing_user:
        profile_button = InlineKeyboardButton(text="Профиль", web_app=WebAppInfo(url=f"https://bot.local/web/profile.html?username={user.username}"))
        if existing_user.role == "manager":
            keyboard = [
                [InlineKeyboardButton("Открыть мини-приложение Motivation B8oost", web_app=WebAppInfo(url=f"https://bot.local/web/profile.html?username={user.username}"))],
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("Открыть мини-приложение Motivation B8oost", web_app=WebAppInfo(url=f"https://bot.local/web/profile.html?username={user.username}"))],
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.message:
            await update.message.reply_text(f'Здравствуйте, {user.first_name}', reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(f'Здравствуйте, {user.first_name}', reply_markup=reply_markup)
    else:
        if update.message:
            await update.message.reply_text(f'Здравствуйте, {user.first_name}! Вижу вас впервые. Используйте /register чтобы зарегистрироваться.')
        elif update.callback_query:
            await update.callback_query.edit_message_text(f'Здравствуйте, {user.first_name}! Вижу вас впервые. Используйте /register чтобы зарегистрироваться.')

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'add_task':
        keyboard = [[InlineKeyboardButton("Назад", callback_data='start')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Придумайте название задачи:", reply_markup=reply_markup)
        context.user_data['task_state'] = TaskState.TITLE
    elif query.data == 'start':
        await start(update, context)
    elif query.data == 'my_tasks':
        chat_id = query.message.chat_id
        user = session.query(User).filter_by(chat_id=chat_id).first()
        if user and user.role == "manager":
            tasks = session.query(Task).filter_by(created_by=user.username).all()
            if tasks:
                keyboard = [[InlineKeyboardButton("Назад", callback_data='start')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                tasks_list = "\n".join([f"Задача: {task.title}, Описание: {task.description}, Награда: {task.reward}" for task in tasks])
                await query.edit_message_text(f"Ваши задачи:\n{tasks_list}", reply_markup=reply_markup)
            else:
                await query.edit_message_text("У вас пока нет задач.")
        else:
            await query.edit_message_text("Эта функция доступна только менеджерам.")

async def handle_task_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user_data = context.user_data
    if 'task_state' in user_data:
        if user_data['task_state'] == TaskState.TITLE:
            user_data['task_title'] = update.message.text
            keyboard = [[InlineKeyboardButton("Назад", callback_data='start')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Придумайте описание задачи:", reply_markup=reply_markup)
            user_data['task_state'] = TaskState.DESCRIPTION
        elif user_data['task_state'] == TaskState.DESCRIPTION:
            user_data['task_description'] = update.message.text
            keyboard = [[InlineKeyboardButton("Назад", callback_data='start')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Укажите стоимость награды:", reply_markup=reply_markup)
            user_data['task_state'] = TaskState.REWARD
        elif user_data['task_state'] == TaskState.REWARD:
            user_data['task_reward'] = int(update.message.text)
            user = session.query(User).filter_by(chat_id=chat_id).first()
            if user:
                new_task = Task(
                    title=user_data['task_title'],
                    description=user_data['task_description'],
                    reward=user_data['task_reward'],
                    assigned_to=None,
                    created_by=user.username,
                    created_at=datetime.utcnow(),
                    completed_by=0
                )
                session.add(new_task)
                session.commit()
                await update.message.reply_text("Задача успешно добавлена")
                del user_data['task_state']
                await start(update, context)


async def register(update: Update, context: CallbackContext):
    profile_photos = await context.bot.get_user_profile_photos(update.message.chat.id)
    if profile_photos.total_count > 0:
        photo_size = profile_photos.photos[0][-1]
        photo_file = await context.bot.get_file(photo_size.file_id)
        photo_url = photo_file.file_path
        #print(update)
        photo = f"web/photo/{update.message.chat.username}.jpg"
        urllib.request.urlretrieve(photo_url, photo)
    else:
        pass
    user = update.message.from_user
    chat_id = update.message.chat_id
    existing_user = session.query(User).filter_by(chat_id=chat_id).first()
    
    if existing_user:
        await update.message.reply_text('Вы уже зарегистрированы')
        return

    new_user = User(
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        chat_id=chat_id,
        role="employee",
        point=0
    )
    session.add(new_user)
    session.commit()

    await update.message.reply_text('Вы успешно зарегистрированы как сотрудник!')
    await start(update, context)

async def check_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    user = session.query(User).filter_by(chat_id=chat_id).first()
    if user:
        await update.message.reply_text(f'Ваша роль: {user.role}')
    else:
        await update.message.reply_text('Вы не зарегистрированы')

def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    start_handler = CommandHandler('start', start)
    register_handler = CommandHandler('register', register)
    check_role_handler = CommandHandler('check_role', check_role)
    button_handler = CallbackQueryHandler(button)
    task_info_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_task_info)
    application.add_handler(start_handler)
    application.add_handler(register_handler)
    application.add_handler(check_role_handler)
    application.add_handler(button_handler)
    application.add_handler(task_info_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
