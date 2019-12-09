# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from application import exception
from application.model.service import Service
from application.model.service_template import ServiceTemplate
from application.model.subscribe_service_snapshot import SubscribeServiceSnapshot
from application.model.trade_order import TradeOrder
from application.model.user_account import UserAccount
from application.util.database import session_scope
from application.views.base_api import BaseNeedLoginAPI, ApiResult


class ServiceOrderAPI(BaseNeedLoginAPI):
    methods = ['GET', 'POST', 'PUT', 'DELETE']

    def get(self):
        uuid = self.get_data('uuid')
        if self.valid_data(uuid):
            return self.get_order_by_uuid(uuid)
        else:
            return self.get_orders()

    def get_order_by_uuid(self, uuid: str):
        with session_scope() as session:
            order = session.query(TradeOrder) \
                .filter(TradeOrder.uuid == uuid,
                        TradeOrder.status != TradeOrder.STATUS.DELETED).first()  # type:
            if order is None:
                raise exception.api.NotFound('订单不存在')

    def get_orders(self):
        with session_scope() as session:
            order_list = []
            orders = self.derive_query_for_get_method(session, TradeOrder) \
                .filter(TradeOrder.user_uuid == self.user_uuid).all()
            for order in orders:  # type: TradeOrder
                order_list.append(order.to_dict())

            result = ApiResult('获取订单信息成功', payload={
                'orders': order_list,
            })
            return result.to_response()

    def post(self):
        service_uuid = self.get_post_data('service_uuid')
        if self.valid_data(service_uuid):
            return self.generate_renew_order(service_uuid)

        service_template_uuid = self.get_post_data('template_uuid')
        if self.valid_data(service_template_uuid):
            return self.generate_creation_order(service_template_uuid)

        raise exception.api.InvalidRequest('非法请求')

    def generate_renew_order(self, service_uuid: str):
        raise exception.api.ServiceUnavailable('接口建设中')

    def generate_creation_order(self, service_template_uuid: str):
        self.check_is_order_conflict(service_template_uuid)

        password = self.get_post_data('password', require=True, error_message='缺少password字段')
        auto_renew = self.get_post_data('auto_renew')

        with session_scope() as session:
            service_template = session.query(ServiceTemplate) \
                .filter(ServiceTemplate.uuid == service_template_uuid,
                        ServiceTemplate.status != ServiceTemplate.STATUS.DELETED).first()  # type: ServiceTemplate
            if service_template is None:
                raise exception.api.NotFound('套餐不存在，无法办理')
            if service_template.status == ServiceTemplate.STATUS.SUSPEND:
                raise exception.api.Forbidden('该套餐已下架，故无法办理')

            total_payment = service_template.initialization_fee + service_template.price

            order = TradeOrder(
                user_uuid=self.user_uuid,
                order_type=TradeOrder.TYPE.CONSUME.value,
                amount=total_payment,
                description='开通学术服务，服务模板UUID：{}'.format(service_template.uuid)
            )
            session.add(order)
            session.flush()

            auto_renew = auto_renew if self.valid_data(auto_renew) else 0
            snapshot = SubscribeServiceSnapshot(
                trade_order_uuid=order.uuid,
                user_uuid=self.user_uuid,
                service_password=password,
                auto_renew=auto_renew,
                service_template_uuid=service_template_uuid,
                service_type=service_template.type,
                title=service_template.title,
                subtitle=service_template.subtitle,
                description=service_template.description,
                package=service_template.package,
                price=service_template.price,
                initialization_fee=service_template.initialization_fee
            )
            session.add(snapshot)

            result = ApiResult('订单创建成功', 201, {
                'uuid': order.uuid,
            })
            return result.to_response()

    def check_is_order_conflict(self, service_template_uuid: str):
        with session_scope() as session:
            threshold_in_minutes = 30
            critical_time = datetime.now() - timedelta(minutes=threshold_in_minutes)
            print(critical_time)
            orders = session.query(TradeOrder) \
                .filter(TradeOrder.user_uuid == self.user_uuid,
                        TradeOrder.status.in_([TradeOrder.STATUS.INITIALIZATION.value, TradeOrder.STATUS.PAYING.value]),
                        TradeOrder.created_at > critical_time).all()
            for order in orders:  # type: TradeOrder
                snapshot = session.query(SubscribeServiceSnapshot) \
                    .filter(SubscribeServiceSnapshot.trade_order_uuid == order.uuid,
                            SubscribeServiceSnapshot.status != SubscribeServiceSnapshot.STATUS.DELETED) \
                    .first()  # type: SubscribeServiceSnapshot
                if snapshot.service_template_uuid == service_template_uuid:
                    raise exception.api.Conflict('有尚未支付的{}的订单，请勿重复下单'.format(snapshot.title))

    def put(self):
        pass


view = ServiceOrderAPI
