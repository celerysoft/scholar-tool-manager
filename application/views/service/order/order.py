# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from flask import Blueprint

from app import derive_import_root, add_url_rules_for_blueprint
from application import exception
from application.model.service_template import ServiceTemplate
from application.model.subscribe_service_snapshot import SubscribeServiceSnapshot
from application.model.trade_order import TradeOrder
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
                        TradeOrder.status != TradeOrder.STATUS.DELETED.value).first()  # type: TradeOrder
            if order is None:
                raise exception.api.NotFound('订单不存在')

            result = ApiResult('获取订单信息成功', payload={
                'order': order.to_dict()
            })
            return result.to_response()

    def get_orders(self):
        with session_scope() as session:
            order_list = []
            query = session.query(TradeOrder, SubscribeServiceSnapshot.title)
            orders = self.derive_query_for_get_method(session, TradeOrder, query) \
                .outerjoin(SubscribeServiceSnapshot, SubscribeServiceSnapshot.trade_order_uuid == TradeOrder.uuid) \
                .filter(TradeOrder.user_uuid == self.user_uuid).all()
            for order in orders:
                order_dict = order.TradeOrder.to_dict()
                order_dict['title'] = order.title
                order_list.append(order_dict)

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
            threshold_in_day = 1
            critical_time = datetime.now() - timedelta(days=threshold_in_day)
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

    def delete(self):
        uuid = self.get_data('uuid', require=True, error_message='缺少uuid字段')
        with session_scope() as session:
            order = session.query(TradeOrder) \
                .filter(TradeOrder.uuid == uuid,
                        TradeOrder.status != TradeOrder.STATUS.DELETED.value).first()  # type: TradeOrder

            if order is None:
                raise exception.api.NotFound('订单不存在')

            if order.user_uuid != self.user_uuid:
                raise exception.api.Forbidden('无权修改他人的订单')

            if order.status == TradeOrder.STATUS.CANCEL.value:
                raise exception.api.Conflict('订单已取消，无法重复取消')

            if order.status not in [TradeOrder.STATUS.INITIALIZATION.value, TradeOrder.STATUS.PAYING.value]:
                raise exception.api.InvalidRequest('订单已进入支付流程，无法取消，请完成支付后进行退款操作')

            order.status = TradeOrder.STATUS.CANCEL.value

            result = ApiResult('订单取消成功')
            return result.to_response()


view = ServiceOrderAPI

bp = Blueprint(__name__.split('.')[-1], __name__)
root = derive_import_root(__name__)
add_url_rules_for_blueprint(root, bp)
