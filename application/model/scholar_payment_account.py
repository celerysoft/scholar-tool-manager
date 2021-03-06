# -*- coding: utf-8 -*-
from enum import Enum

from sqlalchemy import Column
from sqlalchemy.dialects.mysql import VARCHAR, DECIMAL

from application.model.base_model import Base, BaseModelMixin


class ScholarPaymentAccount(Base, BaseModelMixin):
    __tablename__ = 'scholar_payment_account'
    __comment__ = '学术积分账户'

    user_uuid = Column(VARCHAR(36), nullable=False, comment='账户持有人UUID')
    balance = Column(DECIMAL(12, 2), default=0, comment='账户余额')

    class STATUS(Enum):
        INITIALIZATION = 0
        VALID = 1
        DELETED = 2

    def __init__(self, user_uuid, balance, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.user_uuid = user_uuid
        self.balance = balance
        self.status = 1


cacheable = ScholarPaymentAccount
