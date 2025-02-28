from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, Sequence, DateTime
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from math import ceil

engine = create_engine('sqlite:///data/users.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()
app = Flask(__name__)
CORS(app)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    username = Column(String(50))
    first_name = Column(String(50))
    last_name = Column(String(50))
    chat_id = Column(Integer)
    role = Column(String(50), default="employee")
    point = Column(Integer, default=0)

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

@app.route('/api/profile', methods=['GET'])
def get_profile():
    username = request.args.get('username')
    user = session.query(User).filter_by(username=username).first()
    if user:
        return jsonify({
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'points': user.point,
            'chat_id': user.chat_id
        })
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    username = request.args.get('username')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 5))
    offset = (page - 1) * limit
    tasks = session.query(Task).offset(offset).limit(limit).all()
    total_tasks = session.query(Task).count()
    total_pages = ceil(total_tasks / limit)

    tasks_list = [{
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'reward': task.reward,
        'created_by': task.created_by,
        'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'completed_by': task.completed_by
    } for task in tasks]

    return jsonify({
        'tasks': tasks_list,
        'page': page,
        'total_pages': total_pages,
        'total_tasks': total_tasks
    })

@app.route('/api/tasks/<int:task_id>/delete', methods=['DELETE'])
def delete_task(task_id):
    task = session.query(Task).filter_by(id=task_id).first()
    if not task:
        return jsonify({'error': 'Задача не найдена'}), 404

    user = session.query(User).filter_by(username=task.created_by).first()
    if user.chat_id != request.headers.get('X-User-Id'):
        return jsonify({'error': 'Вы не можете удалить эту задачу'}), 403

    session.delete(task)
    session.commit()
    return jsonify({'message': 'Задача удалена'})

@app.route('/api/tasks/<int:task_id>/edit', methods=['PUT'])
def edit_task(task_id):
    task = session.query(Task).filter_by(id=task_id).first()
    if not task:
        return jsonify({'error': 'Задача не найдена'}), 404

    user = session.query(User).filter_by(username=task.created_by).first()
    if user.chat_id != request.headers.get('X-User-Id'):
        return jsonify({'error': 'Вы не можете редактировать эту задачу'}), 403

    data = request.json
    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'reward' in data:
        task.reward = data['reward']

    session.commit()
    return jsonify({'message': 'Задача обновлена'})


if __name__ == '__main__':
    app.run(port=5000)
