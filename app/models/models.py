from flask import Flask
from datetime import datetime, date, timezone
from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

users_cases = db.Table('users_cases',
    db.Column('user_id', db.Integer, db.ForeignKey('user.user_id')),
    db.Column('case_id', db.Integer, db.ForeignKey('cases.case_id'))
)

class User(db.Model):
    __tablename__ = 'user'

    user_id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(120), unique=True, nullable=False)
    user_role = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = db.Column(db.Boolean, default= True)

    assigned_cases = db.relationship(
    'Case',
    secondary=users_cases,
    back_populates='assigned_users'
)   
          
    def serialize(self):
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "user_role": self.user_role,
            "user_email": self.user_email,
            "created_at": str(self.created_at)
        }


class Case(db.Model):
    __tablename__ = 'cases'

    case_id = db.Column(db.Integer, primary_key =True)
    case_type =  db.Column(db.String(120), unique=False, nullable=False)
    case_status= db.Column(db.String(120), unique=False, nullable=False)
    case_stage = db.Column(db.String(120), unique=False, nullable=False) 
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    updated_by = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=True)
    is_deleted = db.Column(db.Boolean, default = False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=True)     
    
    client_id = db.Column(db.Integer, db.ForeignKey('client.client_id'), nullable= False)

    assigned_users = db.relationship(
    'User',
    secondary=users_cases,
    back_populates='assigned_cases'
)
    tasks = db.relationship('Task', backref='Case')
    notes = db.relationship('Note', backref='Case')
    #auditlog = db.relationship('AuditLog', backref='Case')

    def serialize(self):
        return {
            "case_id": self.case_id,
            "case_type": self.case_type,
            "case_status": self.case_status,
            "case_stage": self.case_stage,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "assigned_users": [user.serialize() for user in self.assigned_users],
            "client": self.client.serialize() if self.client else None,
            "is_deleted" : self.is_deleted,
            "deleted_at": self.deleted_at,
            "deleted_by": self.deleted_by,
            "updated_by" : self.updated_by
        }

class AuditLog(db.Model):
    __tablename__ = 'audit_log'

    log_id = db.Column(db.Integer, primary_key =True)
    case_id = db.Column(db.Integer,db.ForeignKey("cases.case_id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    action = db.Column(db.String(120), unique =False, nullable=False)
    new_value = db.Column(db.String(120), unique =False, nullable=True)
    old_value = db.Column(db.String(120), unique =False, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


    case = db.relationship('Case', backref='audit_log')
    user = db.relationship('User', backref='audit_log')

    def serialize(self):
        return {
            "log_id": self.log_id,
            "case_id": self.case_id,
            "user_id": self.user_id,
            "action": self.action,
            "new_value": self.new_value,
            "old_value": self.old_value,
            "created_at": str(self.created_at)
        }

class Client(db.Model):
    __tablename__ = 'client'

    client_id = db.Column(db.Integer, primary_key =True)
    client_first_name = db.Column(db.String(120), unique=False, nullable=False)
    client_lastname = db.Column(db.String(120), unique=False, nullable=False)
    client_phone = db.Column(db.String(20), unique=False, nullable=False)
    client_email = db.Column(db.String(120), unique=True, nullable=False)
    client_address = db.Column(db.String(240), unique=False, nullable=False)
    client_date_of_birth = db.Column(db.Date, unique=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    cases = db.relationship("Case", backref="client")
    
    def serialize(self):
        return {
            "client_id": self.client_id,
            "client_first_name": self.client_first_name,
            "client_lastname": self.client_lastname,
            "client_phone": self.client_phone,
            "client_email": self.client_email,
            "client_date_of_birth": str(self.client_date_of_birth),
            "client_address": self.client_address,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at)
        }



class Note(db.Model):
    __tablename__ = 'notes'

    note_id = db.Column(db.Integer, primary_key =True, autoincrement=True)
    note_title = db.Column(db.String(120), unique=False, nullable=False)
    note_content = db.Column(db.String(500),unique=False, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
       
    
    
    case_id = db.Column(db.Integer, db.ForeignKey('cases.case_id'))
    created_by = db.Column(db.Integer, db.ForeignKey('user.user_id'))

    def serialize(self):
        return {
            "note_id": self.note_id,
            "note_title": self.note_title,
            "note_content": self.note_content,
            "created_at": str(self.created_at),
            "case_id": self.case_id,
            "created_by": self.created_by

        }


class Task(db.Model):
    __tablename__ = 'tasks'

    task_id = db.Column(db.Integer, primary_key =True, autoincrement=True)
    task_title= db.Column(db.String(120), unique=False, nullable=False)
    task_description = db.Column(db.String(500), unique=False, nullable=False)
    task_priority = db.Column(db.String(120), unique=False, nullable=False)
    task_status = db.Column(db.String(120), unique=False, nullable=False)
    due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    assigned_to = db.Column(db.Integer, db.ForeignKey("user.user_id"), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.case_id'), nullable= False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable= False)

    def serialize(self):
        return {
            "task_id": self.task_id,
            "task_title": self.task_title,
            "task_description": self.task_description,
            "task_priority": self.task_priority,
            "task_status": self.task_status,
            "due_date": str(self.due_date),
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "assigned_to": self.assigned_to,
            "case_id": self.case_id,
            "created_by": self.created_by

        }


    
    