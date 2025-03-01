from flask import Flask, jsonify, request
from sqlalchemy import create_engine, Column, Integer, String, Sequence, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from flask_cors import CORS
from math import ceil

app = Flask(__name__)
CORS(app)

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
    achieved_at = Column(DateTime, default=datetime.utcnow) 


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

class ManagerEmployee(Base):
    __tablename__ = 'manager_employee'
    id = Column(Integer, Sequence('manager_employee_id_seq'), primary_key=True)
    manager_id = Column(Integer, ForeignKey('users.id'))  
    employee_id = Column(Integer, ForeignKey('users.id'))

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()


def get_user_rank(user_id):
    users = session.query(User).order_by(User.point.desc()).all()
    for index, user in enumerate(users, start=1):
        if user.id == user_id:
            return index
    return None

@app.route('/api/profile', methods=['GET'])
def get_profile():
    username = request.args.get('username')
    user = session.query(User).filter_by(username=username).first()
    if user:
        
        all_achievements = session.query(Achievement).all()
        
        
        user_achievements = session.query(UserAchievement).filter_by(user_id=user.id).all()
        achieved_ids = [ua.achievement_id for ua in user_achievements]
        
        
        achievements = []
        for achievement in all_achievements:
            achieved = achievement.id in achieved_ids
            achieved_at = None
            if achieved:
                achieved_at = session.query(UserAchievement).filter_by(
                    user_id=user.id, achievement_id=achievement.id
                ).first().achieved_at.strftime('%Y-%m-%d %H:%M:%S')
            
            achievements.append({
                'id': achievement.id,
                'title': achievement.title,
                'description': achievement.description,
                'icon': achievement.icon,
                'achieved': achieved,
                'achieved_at': achieved_at,
            })

        
        rank = None
        if user.role == 'employee':
            rank = get_user_rank(user.id)

        return jsonify({
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'points': user.point,
            'rank': rank,  
            'achievements': achievements,
            'role': user.role  
        })
    else:
        return jsonify({'error': 'Пользователь не найден'}), 404

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    users = session.query(User).order_by(User.point.desc()).all()
    leaderboard = []
    for index, user in enumerate(users, start=1):
        leaderboard.append({
            'rank': index,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'points': user.point
        })
    
    return jsonify(leaderboard)

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
    if task:
        session.delete(task)
        session.commit()
        return jsonify({'message': 'Задача удалена'})
    else:
        return jsonify({'error': 'Задача не найдена'}), 404

@app.route('/api/tasks/<int:task_id>/edit', methods=['PUT'])
def edit_task(task_id):
    task = session.query(Task).filter_by(id=task_id).first()
    if not task:
        return jsonify({'error': 'Задача не найдена'}), 404

    data = request.json
    #print(data)  
    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'reward' in data:
        task.reward = data['reward']

    session.commit()
    return jsonify({'message': 'Задача обновлена'})

class Reward(Base):
    __tablename__ = 'rewards'
    id = Column(Integer, Sequence('reward_id_seq'), primary_key=True)
    title = Column(String(100))
    description = Column(String(500))
    icon = Column(String(100)) 
    price = Column(Integer)
    
Base.metadata.create_all(engine)

@app.route('/api/rewards', methods=['GET'])
def get_rewards():
    rewards = session.query(Reward).all()
    rewards_list = [{
        'id': reward.id,
        'title': reward.title,
        'description': reward.description,
        'icon': reward.icon,
        'price': reward.price
    } for reward in rewards]
    return jsonify(rewards_list)

@app.route('/api/rewards/<int:reward_id>/buy', methods=['POST'])
def buy_reward(reward_id):
    data = request.json
    username = data.get('username')
    user = session.query(User).filter_by(username=username).first()
    reward = session.query(Reward).filter_by(id=reward_id).first()

    if not user or not reward:
        return jsonify({'error': 'Пользователь или награда не найдены'}), 404

    if user.point < reward.price:
        return jsonify({'error': 'Недостаточно очков для покупки'}), 400

    user.point -= reward.price
    session.commit()

    return jsonify({'message': 'Награда успешно куплена!'})

@app.route('/api/employees', methods=['GET'])
def get_employees():
    manager_username = request.args.get('manager_username')
    manager = session.query(User).filter_by(username=manager_username).first()
    if not manager:
        return jsonify({'error': 'Менеджер не найден'}), 404

    employees = session.query(User).join(ManagerEmployee, ManagerEmployee.employee_id == User.id).filter(ManagerEmployee.manager_id == manager.id).all()
    
    employees_list = [{
        'id': employee.id,
        'username': employee.username,
        'first_name': employee.first_name,
        'last_name': employee.last_name,
        'points': employee.point,
        'role': employee.role
    } for employee in employees]

    return jsonify(employees_list)

@app.route('/api/employees/add', methods=['POST'])
def add_employee():
    data = request.json
    manager_username = data.get('manager_username')
    employee_username = data.get('employee_username')

    manager = session.query(User).filter_by(username=manager_username).first()
    employee = session.query(User).filter_by(username=employee_username).first()

    if not manager or not employee:
        return jsonify({'error': 'Менеджер или сотрудник не найдены'}), 404

    existing_link = session.query(ManagerEmployee).filter_by(manager_id=manager.id, employee_id=employee.id).first()
    if existing_link:
        return jsonify({'error': 'Сотрудник уже прикреплен к менеджеру'}), 400

    new_link = ManagerEmployee(manager_id=manager.id, employee_id=employee.id)
    session.add(new_link)
    session.commit()

    return jsonify({'message': 'Сотрудник успешно добавлен'})

@app.route('/api/employees/<int:employee_id>/edit', methods=['PUT'])
def edit_employee(employee_id):
    data = request.json
    employee = session.query(User).filter_by(id=employee_id).first()
    if not employee:
        return jsonify({'error': 'Сотрудник не найден'}), 404

    if 'first_name' in data:
        employee.first_name = data['first_name']
    if 'last_name' in data:
        employee.last_name = data['last_name']
    if 'points' in data:
        employee.point = data['points']
    if 'role' in data:
        employee.role = data['role']

    session.commit()
    return jsonify({'message': 'Данные сотрудника обновлены'})

@app.route('/api/employees/<int:employee_id>/delete', methods=['DELETE'])
def delete_employee(employee_id):
    employee = session.query(User).filter_by(id=employee_id).first()
    if not employee:
        return jsonify({'error': 'Сотрудник не найден'}), 404

    session.query(ManagerEmployee).filter_by(employee_id=employee.id).delete()
    session.commit()

    return jsonify({'message': 'Сотрудник удален'})

if __name__ == '__main__':
    app.run(port=5000)
    
