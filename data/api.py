from flask import request
from flask_login import current_user
from flask_restful import Resource
from . import db
from .models import Poll, Vote


class PollListResource(Resource):
    def get(self):
        polls = Poll.query.all()
        return [{'id': p.id, 'title': p.title, 'creator': p.author.username} for p in polls]


class VoteResource(Resource):
    def post(self, poll_id):
        if not current_user.is_authenticated:
            return {'error': 'Требуется авторизация'}, 401
        data = request.get_json()
        opt_id = data.get('option_id')
        if not opt_id:
            return {'error': 'Не указан вариант'}, 400
        if Vote.query.filter_by(user_id=current_user.id, option_id=opt_id).first():
            return {'error': 'Вы уже голосовали'}, 400
        db.session.add(Vote(user_id=current_user.id, option_id=int(opt_id)))
        db.session.commit()
        return {'message': 'Голос принят'}, 200
