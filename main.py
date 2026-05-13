import os
from flask import Flask, render_template, redirect, url_for, flash, session, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_restful import Api
from functools import wraps
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_wtf import FlaskForm

from data import db
from data.models import User, Poll, Option, Vote
from data.forms import RegForm, LoginForm, PollConfigForm
from data.api import PollListResource, VoteResource

login_manager = LoginManager()
api = Api()


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Доступ запрещён')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_ENABLED'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    api.init_app(app)

    api.add_resource(PollListResource, '/api/polls')
    api.add_resource(VoteResource, '/api/vote/<int:poll_id>')

    @login_manager.user_loader
    def load_user(uid):
        return db.session.get(User, int(uid))

    @app.route('/')
    def index():
        return render_template('index.html', polls=Poll.query.all())

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegForm()
        if form.validate_on_submit():
            if User.query.filter_by(username=form.username.data).first():
                flash('Логин уже занят')
                return redirect(url_for('register'))
            is_first = User.query.count() == 0
            u = User(username=form.username.data, is_admin=is_first)
            u.set_password(form.password.data)
            db.session.add(u)
            db.session.commit()
            flash('Регистрация успешна' +
                  (' ✅ Вы администратор!' if is_first else ''))
            return redirect(url_for('login'))
        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            u = User.query.filter_by(username=form.username.data).first()
            if u and u.check_password(form.password.data):
                login_user(u)
                return redirect(url_for('index'))
            flash('Неверный логин или пароль')
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/admin')
    @admin_required
    def admin():
        return render_template('admin.html', users=User.query.all(), polls=Poll.query.all())

    @app.route('/admin/delete_user/<int:id>', methods=['POST'])
    @admin_required
    def delete_user(id):
        if id == current_user.id:
            flash('Нельзя удалить себя')
            return redirect(url_for('admin'))
        u = db.session.get(User, id)
        if u:
            db.session.delete(u)
            db.session.commit()
            flash('Пользователь удалён')
        return redirect(url_for('admin'))

    @app.route('/admin/delete_poll/<int:id>', methods=['POST'])
    @admin_required
    def delete_poll(id):
        p = db.session.get(Poll, id)
        if p:
            db.session.delete(p)
            db.session.commit()
            flash('Опрос удалён')
        return redirect(url_for('admin'))

    # 2-шаговое создание опроса
    @app.route('/create/config', methods=['GET', 'POST'])
    @login_required
    def create_config():
        form = PollConfigForm()
        if form.validate_on_submit():
            session['poll_title'] = form.title.data
            session['poll_num'] = form.num_options.data
            return redirect(url_for('create_options'))
        return render_template('create_config.html', form=form)

    @app.route('/create/options', methods=['GET', 'POST'])
    @login_required
    def create_options():
        if 'poll_title' not in session or 'poll_num' not in session:
            return redirect(url_for('create_config'))
        num = session['poll_num']

        class TempPollForm(FlaskForm):
            pass
        for i in range(num):
            setattr(TempPollForm, f'opt{i}', StringField(
                f'Вариант {i+1}', validators=[DataRequired()]))
        setattr(TempPollForm, 'submit', SubmitField('Создать опрос'))
        form = TempPollForm()
        if form.validate_on_submit():
            p = Poll(title=session['poll_title'], creator_id=current_user.id)
            db.session.add(p)
            db.session.flush()
            for i in range(num):
                db.session.add(
                    Option(poll_id=p.id, text=getattr(form, f'opt{i}').data))
            db.session.commit()
            session.pop('poll_title', None)
            session.pop('poll_num', None)
            flash('Опрос успешно создан')
            return redirect(url_for('index'))
        return render_template('create_options.html', form=form, num=num)

    @app.route('/poll/<int:id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_poll(id):
        p = db.session.get(Poll, id)
        if not p or p.creator_id != current_user.id:
            flash('Доступ запрещён')
            return redirect(url_for('index'))

        class EditPollForm(FlaskForm):
            pass
        setattr(EditPollForm, 'title', StringField(
            'Название', validators=[DataRequired(), Length(3, 100)]))
        for i, opt in enumerate(p.options):
            setattr(EditPollForm, f'opt{i}', StringField(
                f'Вариант {i+1}', validators=[DataRequired()]))
        setattr(EditPollForm, 'submit', SubmitField('Сохранить'))

        form = EditPollForm()
        # Заполняем форму текущими данными при первом заходе (GET)
        if request.method == 'GET':
            form.title.data = p.title
            for i, opt in enumerate(p.options):
                getattr(form, f'opt{i}').data = opt.text

        if form.validate_on_submit():
            p.title = form.title.data
            for i, opt in enumerate(p.options):
                opt.text = getattr(form, f'opt{i}').data
            db.session.commit()
            flash('Опрос обновлён')
            return redirect(url_for('poll', id=p.id))
        return render_template('edit_poll.html', form=form, poll=p)

    @app.route('/poll/<int:id>/delete', methods=['POST'])
    @login_required
    def delete_poll_user(id):
        p = db.session.get(Poll, id)
        if not p or p.creator_id != current_user.id:
            flash('Доступ запрещён')
            return redirect(url_for('index'))
        db.session.delete(p)
        db.session.commit()
        flash('Опрос удалён')
        return redirect(url_for('index'))

    @app.route('/poll/<int:id>')
    def poll(id):
        p = db.session.get(Poll, id)
        if not p:
            abort(404)
        voted = False
        if current_user.is_authenticated:
            for opt in p.options:
                if Vote.query.filter_by(user_id=current_user.id, option_id=opt.id).first():
                    voted = True
                    break
        return render_template('poll.html', poll=p, voted=voted)

    @app.route('/vote/<int:id>', methods=['POST'])
    @login_required
    def vote_web(id):
        p = db.session.get(Poll, id)
        if not p:
            abort(404)
        opt_id = request.form.get('option')
        if not opt_id:
            return redirect(url_for('poll', id=id))
        if Vote.query.filter_by(user_id=current_user.id, option_id=opt_id).first():
            flash('Вы уже голосовали')
            return redirect(url_for('poll', id=id))
        db.session.add(Vote(user_id=current_user.id, option_id=int(opt_id)))
        db.session.commit()
        return redirect(url_for('results', id=id))

    @app.route('/results/<int:id>')
    def results(id):
        p = db.session.get(Poll, id)
        if not p:
            abort(404)
        total = sum(opt.votes.count() for opt in p.options)
        return render_template('results.html', poll=p, total=total)

    with app.app_context():
        db.create_all()
    return app


if __name__ == '__main__':
    create_app().run(host='0.0.0.0', port=5000)
