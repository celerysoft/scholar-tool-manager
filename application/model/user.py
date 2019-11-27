# -*- coding: utf-8 -*-
import uuid

from sqlalchemy import Column, String

from application.model.base_model import Base, BaseModelMixin


class User(Base, BaseModelMixin):
    __tablename__ = 'user'
    __comment__ = '用户'

    username = Column(String(32), nullable=False, comment='用户名')
    email = Column(String(64), nullable=False, comment='电子邮箱')
    password = Column(String(256), nullable=False, comment='密码')

    def __init__(self, username, email, password, *args, **kwargs):
        super().__init__()

        self.username = username
        self.email = email
        self.password = password
        self.status = 0


cacheable = User