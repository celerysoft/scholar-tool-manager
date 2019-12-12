# -*- coding: utf-8 -*-
from enum import Enum

from sqlalchemy import Column
from sqlalchemy.dialects.mysql import VARCHAR, DECIMAL, TINYINT

from application.model.base_model import Base, BaseModelMixin


class ScholarPaymentAccount(Base, BaseModelMixin):
    __tablename__ = 'scholar_payment_account_log'
    __comment__ = '学术积分账户流水'

    account_uuid = Column(VARCHAR(36), nullable=False, comment='学术积分账户UUID')
    former_balance = Column(DECIMAL(12, 2), nullable=False, comment='账户余额')
    balance = Column(DECIMAL(12, 2), nullable=False, comment='账户余额')
    type = Column(TINYINT, nullable=False, comment='0 - 减少，1 - 增加')
    purpose_type = Column(TINYINT, nullable=False,
                          comment='0 - 消费(-)，1 - 充值(+)，2 - 转出(-)，3 - 转入(+)，4 - 补缴(-)，5 - 补偿(+)')

    class Type(Enum):
        DECREASE = 0
        INCREASE = 1

    class PurposeType(Enum):
        CONSUME = 0
        RECHARGE = 1

    class Status(Enum):
        INITIALIZATION = 0
        VALID = 1
        DELETED = 2

    def __init__(self, account_uuid: str, former_balance, balance, log_type, purpose_type, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.account_uuid = account_uuid
        self.former_balance = former_balance
        self.balance = balance
        self.type = log_type
        self.purpose_type = purpose_type
        self.status = 1


cacheable = ScholarPaymentAccount
