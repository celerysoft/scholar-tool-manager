#!/usr/bin/python3
# -*-coding:utf-8 -*-
import random
import time
from datetime import datetime, date

from sqlalchemy import Table, Column, Integer, String, Date, Float, Boolean, LargeBinary,DATETIME
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def to_dict(model):
    return {c.name: getattr(model, c.name) for c in model.__table__.columns}


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String)
    password = Column(String)
    name = Column(String)
    image = Column(String)
    created_at = Column(Float)
    last_login_at = Column(Float)
    available = Column(Boolean)
    total_usage = Column(Integer)

    def __init__(self, username=None, email=None, password=None, name=None, image=None, admin=False, created_at=None,
                 last_login_at=None, available=True):
        self.username = username
        self.email = email
        self.password = password
        self.name = name
        self.image = image
        self.admin = admin
        self.created_at = created_at if created_at else time.time()
        self.last_login_at = last_login_at if last_login_at else time.time()
        self.available = available
        self.total_usage = 0

    def __repr__(self):
        return '<User %s: %s>' % (self.username, self.email)


class Role(Base):
    __tablename__ = 'role'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    label = Column(String)
    description = Column(String)

    def __init__(self, name, label, description=None):
        self.name = name
        self.label = label
        self. description = description

    def __repr__(self):
        return '<Role %s: %s>' % (self.name, self.description)

    # role_id list
    # 超级管理员, root
    ROOT = 1
    # 注册用户, user
    USER = 2
    # 小黑屋，ban
    BAN = 3


class UserRole(Base):
    __tablename__ = 'user_role'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    role_id = Column(Integer)

    def __init__(self, user_id, role_id):
        self.user_id = user_id
        self.role_id = role_id

    def __repr__(self):
        return '<UserRole %s: user_id = %s, role_id = %s>' % (self.id, self.user_id, self.role_id)


class Permission(Base):
    __tablename__ = 'permission'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    label = Column(String)
    description = Column(String)

    def __init__(self, name, label, description=None):
        self.name = name
        self.label = label
        self. description = description

    def __repr__(self):
        return '<Permission %s(%s): %s>' % (self.name, self.label, self.description)

    # permission_id list
    # 登录，login
    LOGIN = 1
    # 后台管理，manage
    MANAGE = 2
    # 邀请码管理，manage_invitation_code
    MANAGE_INVITATION_CODE = 3
    # 公告管理, manage_event
    MANAGE_EVENT = 4
    # 用户管理，manage_user
    MANAGE_USER = 5
    # 角色管理，manage_role
    MANAGE_ROLE = 6
    # 套餐模板管理 manage_service_template
    MANAGE_SERVICE_TEMPLATE = 7


class RolePermission(Base):
    __tablename__ = 'role_permission'

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer)
    permission_id = Column(Integer)

    def __init__(self, role_id, permission_id):
        self.role_id = role_id
        self.permission_id = permission_id


class InvitationCode(Base):
    __tablename__ = 'invitation_code'

    id = Column(Integer, primary_key=True)
    code = Column(String)
    inviter_id = Column(Integer)
    invitee_id = Column(Integer)
    available = Column(Boolean)
    created_at = Column(Float)
    invited_at = Column(Float)

    def __init__(self, code, inviter_id, invitee_id=None, available=None, created_at=None,
                 invited_at=None):
        self.code = code
        self.inviter_id = inviter_id
        self.invitee_id = invitee_id
        self.available = available if available else True
        self.created_at = created_at if created_at else time.time()
        self.invited_at = invited_at

    def __repr__(self):
        return '<InvitationCode %s %s %s>' % (self.id, self.code, self.available)


class Event(Base):
    __tablename__ = 'event'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    name = Column(String)
    tag = Column(String)
    summary = Column(String)
    content = Column(String)
    created_at = Column(Float)
    available = Column(Boolean)

    def __init__(self, user_id=None, name=None, tag=None, summary=None, content=None, created_at=None,
                 available=True):
        self.user_id = user_id
        self.name = name
        self.tag = tag
        self.summary = summary
        self.content = content
        self.created_at = created_at if created_at else time.time()
        self.available = available

    def __repr__(self):
        return '<Event %s %s>' % (self.name, self.tag)


class ServiceTemplate(Base):
    __tablename__ = 'service_template'

    id = Column(Integer, primary_key=True)
    type = Column(Integer)
    title = Column(String)
    subtitle = Column(String)
    description = Column(String)
    balance = Column(Integer)
    price = Column(Integer)

    def __init__(self, type=None, title=None, subtitle=None, description=None, balance=None, price=None):
        self.type = type
        self.title = title
        self.subtitle = subtitle
        self.description = description
        self.balance = balance
        self.price = price

    def __repr__(self):
        return '<ServiceTemplate %s %s>' % (self.title, self.balance)
