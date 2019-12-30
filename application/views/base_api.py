# -*- coding: utf-8 -*-
import json
import math

from flask import request, Response
from flask import session as flask_session
from flask.views import MethodView
from jwt import PyJWTError

import configs
from application import exception
from application.model.base_model import BaseModelMixin
from application.util import authorization, permission
from application.util.database import session_scope


class ApiResult(object):
    def __init__(self, message, status=200, payload=None):
        self.message = message
        self.status = status
        self.payload = payload

    def to_response(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return Response(json.dumps(rv),
                        status=self.status,
                        mimetype='application/json')


class BaseView(MethodView):
    user_uuid = ''

    @classmethod
    def derive_page_parameter(cls, record_count):
        page = request.args.get('page', 1)
        try:
            page = int(page) if page is not None else 1
        except ValueError:
            raise exception.api.InvalidRequest('Invalid page field.')
        default_items_per_page = 10
        page_size = request.args.get('page_size', 10)
        try:
            page_size = int(page_size) if page_size is not None else default_items_per_page
        except ValueError:
            page_size = default_items_per_page

        offset = (page - 1) * page_size

        if 0 < record_count <= offset:
            # noinspection PyUnresolvedReferences
            raise exception.api.InvalidRequest('Item index is out of bounds, try modify page and page_size.')
        max_page = math.ceil(record_count / page_size)
        max_page = max_page if max_page > 0 else 1

        return page, page_size, offset, max_page

    @classmethod
    def _derive_page_parameter(cls, record_count):
        return cls.derive_page_parameter(record_count)

    @staticmethod
    def _derive_get_method_query_dict(model_class):
        fields = []
        for field in model_class.__table__.columns:
            fields.append(field.name)
        query_dict = {}
        for key, value in request.args.items():
            if key in ['page', 'page_size']:
                continue
            if value in [None, '']:
                continue
            if key in fields:
                query_dict[key] = value
        for key, value in request.args.lists():
            if value in [None, '']:
                continue

            format_key = key.replace('[]', '')
            if format_key in fields:
                query_dict[format_key] = value
        return query_dict

    def derive_query_for_get_method(self, session, model_class, query=None):
        query_dict = self._derive_get_method_query_dict(model_class)
        query = session.query(model_class) if query is None else query
        for key, value in query_dict.items():
            if isinstance(value, list):
                query = query.filter(getattr(model_class, key).in_(value))
            else:
                query = query.filter(getattr(model_class, key) == value)
        return query

    @classmethod
    def get_data(cls, key, require=False, error_message=None, req=request):
        data = req.args.get(key, None)

        if require and not cls.valid_data(data):
            error_message = error_message if error_message is not None else '缺少{}参数'.format(key)
            raise exception.api.InvalidRequest(error_message)

        return data

    @classmethod
    def get_post_data(cls, key, require=False, error_message=None, req=request):
        if req.json is not None:
            post_data = req.json.get(key, None)
        else:
            post_data = req.form.get(key, None)

        if require and not cls.valid_data(post_data):
            error_message = error_message if error_message is not None else '缺少{}参数'.format(key)
            raise exception.api.InvalidRequest(error_message)

        return post_data

    @staticmethod
    def get_file_data(key, req=request):
        file_data = None
        if key in req.files:
            file_data = req.files.get(key, None)
        return file_data

    @classmethod
    def valid_data(cls, data) -> bool:
        if type(data) == str:
            return data is not None and len(data.strip()) > 0
        else:
            return data is not None

    @classmethod
    def delete_model(cls, session, model_class: BaseModelMixin.__class__, delete_status=None,
                     not_found_error_message=None) -> BaseModelMixin:
        model_id = cls.get_data('id')
        model_uuid = cls.get_data('uuid')
        if model_id is None and model_uuid is None:
            raise exception.api.InvalidRequest('条件不足，无法寻找指定数据')

        delete_status = 2 if delete_status is None else delete_status
        if cls.valid_data(model_id):
            model = session.query(model_class) \
                .filter(model_class.id == model_id,
                        model_class.status != delete_status).first()
        elif cls.valid_data(model_uuid):
            model = session.query(model_class) \
                .filter(model_class.uuid == model_uuid,
                        model_class.status != delete_status).first()
        else:
            model = None

        if model is None:
            raise exception.api.NotFound(
                not_found_error_message if not_found_error_message is not None else '需要删除的数据不存在'
            )

        model.status = delete_status

        return model

    @classmethod
    def update_model(cls, session, model_class: BaseModelMixin.__class__, data: dict = None, *args,
                     exclude=None, not_found_error_message=None) -> BaseModelMixin:
        model_id = cls.get_post_data('id')
        model_uuid = cls.get_post_data('uuid')
        if model_id is None and model_uuid is None:
            raise exception.api.InvalidRequest('条件不足，无法寻找指定数据')

        delete_status = 2
        if cls.valid_data(model_id):
            model = session.query(model_class) \
                .filter(model_class.id == model_id,
                        model_class.status != delete_status).first()
        elif cls.valid_data(model_uuid):
            model = session.query(model_class) \
                .filter(model_class.uuid == model_uuid,
                        model_class.status != delete_status).first()
        else:
            model = None

        if model is None:
            raise exception.api.NotFound(
                not_found_error_message if not_found_error_message is not None else '指定的数据不存在'
            )

        if exclude is None:
            exclude = []
        if model_class.__immutable_columns__ is not None:
            exclude.extend(model_class.__immutable_columns__)

        fields = []
        for field in model_class.__table__.columns:
            fields.append(field.name)

        if args is None or len(args) == 0:
            args = fields

        for arg in args:
            if arg in exclude:
                continue

            if data is None:
                value = cls.get_post_data(arg)
            else:
                value = data.get(arg)

            if cls.valid_data(value) and arg in fields:
                setattr(model, arg, value)

        return model

    @classmethod
    def create_model_from_http_post(cls, model_class: BaseModelMixin.__class__, data: dict = None) -> BaseModelMixin:
        model = model_class()

        columns = []
        for column in model_class.__allow_columns_for_creation__:
            columns.append(column)
        for column in model_class.__required_columns_for_creation__:
            columns.append(column)

        for arg in columns:
            if data is None:
                value = cls.get_post_data(arg)
            else:
                value = data.get(arg)

            if cls.valid_data(value):
                setattr(model, arg, value)
            else:
                if arg in model_class.__required_columns_for_creation__:
                    raise exception.api.InvalidRequest('缺少{}字段'.format(arg))

        return model

    @staticmethod
    def models_to_list(models: list):
        model_list = []
        for model in models:  # type: BaseModelMixin
            model_list.append(model.to_dict())
        return model_list


class BaseAPI(BaseView):
    pass
    # methods = ['GET']

    # def get_single_model(self, model_class, uuid, query, not_found_exception_message='不存在'):
    #     model = cache.get_model(model_class, uuid)
    #     # model = None
    #     if model is None:
    #         model = query.first()
    #         if model is None:
    #             raise exception.api.NotFound(not_found_exception_message)
    #         else:
    #             cache.set_model(model)
    #     return model
    #
    # def get_multiple_models(self):
    #     pass


def jwt_api(func):
    def handle_jwt(view: MethodView):
        jwt = request.headers.get('Authorization', None)
        if jwt is None or len(jwt) == 0:
            raise exception.api.Unauthorized('请先登录')

        try:
            decoded_jwt = authorization.toolkit.decode_jwt_token(jwt)
        except PyJWTError:
            raise exception.api.Unauthorized('请先登录')

        view.user_uuid = decoded_jwt['uuid']

    def wrapper(*args, **kwargs):
        for parameter in args:
            if isinstance(parameter, BaseNeedLoginAPI):
                if parameter.need_login_methods is not None and request.method in parameter.need_login_methods:
                    handle_jwt(parameter)
            elif isinstance(parameter, MethodView):
                handle_jwt(parameter)
        return func(*args, **kwargs)

    return wrapper


def session_api(func):
    session_dict = flask_session

    def handle_session(view: MethodView):
        if 'user' not in session_dict.keys():
            raise exception.api.Unauthorized('请先登录')

        try:
            user_id = flask_session['user']['id']
        except KeyError:
            raise exception.api.Unauthorized('请先登录')

        view.user_id = user_id

    def wrapper(*args, **kwargs):
        for parameter in args:
            if isinstance(parameter, BaseNeedLoginAPI):
                if parameter.need_login_methods is not None and request.method in parameter.need_login_methods:
                    handle_session(parameter)
            elif isinstance(parameter, MethodView):
                handle_session(parameter)
        return func(*args, **kwargs)

    return wrapper


class BaseNeedLoginAPI(BaseAPI):
    # 需要理用户登录才能执行的方法
    need_login_methods = ['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE']

    def dispatch_request(self, *args, **kwargs):
        if request.method in self.need_login_methods:
            self.check_login_status()
        return super(BaseNeedLoginAPI, self).dispatch_request(*args, **kwargs)

    def check_login_status(self):
        try:
            self.check_jwt()
        except exception.api.Unauthorized as e:
            if not configs.TEST:
                raise e
            else:
                if request.method in ['GET', 'DELETE']:
                    self.user_uuid = self.get_data('user_uuid')
                elif request.method in ['POST', 'PATCH', 'PUT']:
                    self.user_uuid = self.get_post_data('user_uuid')

                if not self.valid_data(self.user_uuid):
                    raise e

    @session_api
    def check_session(self):
        pass

    @jwt_api
    def check_jwt(self):
        pass


def permission_required_api(func):
    def handle_permission(view: MethodView):
        with session_scope() as session:
            # permission_required = view.get_permission_required
            # if not permission.toolkit.check_permission(view.user_uuid, permission_required):
            #     raise exception.api.Forbidden(view.permission_denied_message)

            if not permission.toolkit.check_manage_permission(session, view.user_uuid):
                raise exception.api.Forbidden(view.permission_denied_message)

    def wrapper(*args, **kwargs):
        for parameter in args:
            if isinstance(parameter, PermissionRequiredAPI):
                handle_permission(parameter)
            elif isinstance(parameter, MethodView):
                handle_permission(parameter)
        return func(*args, **kwargs)

    return wrapper


class PermissionRequiredAPI(BaseNeedLoginAPI):
    permission_denied_message = '当前用户无权进行此操作'
    permission_required_methods = ['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTION']
    permission_required_for_head = None
    permission_required_for_get = None
    permission_required_for_post = None
    permission_required_for_patch = None
    permission_required_for_put = None
    permission_required_for_delete = None
    permission_required_for_option = None

    def get_permission_required_by_http_method(self, http_method_name):
        http_method_name = http_method_name
        if http_method_name == 'HEAD':
            return self.permission_required_for_head
        elif http_method_name == 'GET':
            return self.permission_required_for_get
        elif http_method_name == 'POST':
            return self.permission_required_for_post
        elif http_method_name == 'PATCH':
            return self.permission_required_for_patch
        elif http_method_name == 'PUT':
            return self.permission_required_for_put
        elif http_method_name == 'DELETE':
            return self.permission_required_for_delete
        elif http_method_name == 'OPTION':
            return self.permission_required_for_option
        else:
            return None

    def get_permission_required(self):
        permission_required = self.get_permission_required_by_http_method(request.method)

        if permission_required is None:
            return ()
        if isinstance(permission_required, str):
            perms = (permission_required,)
        else:
            perms = permission_required
        return perms

    @permission_required_api
    def check_permission(self):
        pass

    def dispatch_request(self, *args, **kwargs):
        if request.method in self.need_login_methods:
            self.check_login_status()
        if request.method in self.permission_required_methods:
            self.check_permission()
        return super().dispatch_request(*args, **kwargs)
