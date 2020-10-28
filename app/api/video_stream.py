from flask_rest_jsonapi import ResourceDetail, ResourceList
from flask_rest_jsonapi.exceptions import ObjectNotFound
from flask_rest_jsonapi.resource import ResourceRelationship

from app.api.helpers.db import safe_query_kwargs
from app.api.helpers.errors import ForbiddenError
from app.api.helpers.permission_manager import has_access
from app.api.helpers.permissions import jwt_required
from app.api.helpers.utilities import require_relationship
from app.api.schema.video_stream import VideoStreamSchema
from app.models import db
from app.models.microlocation import Microlocation
from app.models.video_stream import VideoStream


class VideoStreamList(ResourceList):

    # decorators = (api.has_permission('is_admin', methods="POST"),)

    def before_post(self, args, kwargs, data):
        require_relationship(['rooms'], data)
        rooms = Microlocation.query.filter(Microlocation.id.in_(data['rooms'])).all()
        event_ids = set()
        for room in rooms:
            event_ids.add(room.event_id)
            if len(event_ids) > 1:
                raise ForbiddenError(
                    {'pointer': '/data/relationships/rooms'},
                    'Video Stream can only be created with rooms of a single event',
                )
        if not has_access('is_coorganizer', event_id=event_ids.pop()):
            raise ForbiddenError(
                {'pointer': '/data/relationships/rooms'},
                "You don't have access to the event of provided rooms",
            )

    def query(self, view_kwargs):
        query_ = self.session.query(VideoStream)

        if view_kwargs.get('room_id'):
            room = safe_query_kwargs(Microlocation, view_kwargs, 'room_id')
            query_ = query_.join(Microlocation).filter(Microlocation.id == room.id)

        return query_

    schema = VideoStreamSchema
    data_layer = {
        'session': db.session,
        'model': VideoStream,
        'methods': {'query': query},
    }


class VideoStreamDetail(ResourceDetail):
    def before_get_object(self, view_kwargs):
        if view_kwargs.get('room_id'):
            room = safe_query_kwargs(Microlocation, view_kwargs, 'room_id')
            view_kwargs['id'] = room.video_stream and room.video_stream.id

    def after_get_object(self, stream, view_kwargs):
        if not stream.user_can_access:
            raise ObjectNotFound(
                {'parameter': 'id'}, f"Video Stream: {stream.id} not found"
            )

    schema = VideoStreamSchema
    decorators = (jwt_required,)
    # decorators = (api.has_permission('is_admin', methods="PATCH,DELETE"),)
    data_layer = {
        'session': db.session,
        'model': VideoStream,
        'methods': {
            'before_get_object': before_get_object,
            'after_get_object': after_get_object,
        },
    }


class VideoStreamRelationship(ResourceRelationship):
    schema = VideoStreamSchema
    methods = ['GET']
    data_layer = {'session': db.session, 'model': VideoStream}
