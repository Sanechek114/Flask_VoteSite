import os
from flask import Flask, render_template, redirect, request, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_restful import Api

from data import db
from data.models import User, Poll, Option, Vote
from data.forms import RegForm, LoginForm, PollForm
from data.api import PollListResource, VoteResource

login_manager = LoginManager()
api = Api()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['WTF_CSRF_ENABLED'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'  # type: ignore
    api.init_app(app)

    api.add_resource(PollListResource, '/api/polls')
    api.add_resource(VoteResource, '/api/vote/<int:poll_id>')

    @login_manager.user_loader
    def load_user(uid):
        return User.query.get(int(uid))

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
            u = User(username=form.username.data)
            u.set_password(form.password.data)
            db.session.add(u)
            db.session.commit()
            flash('Регистрация успешна')
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

    @app.route('/create', methods=['GET', 'POST'])
    @login_required
    def create_poll():
        form = PollForm()
        if form.validate_on_submit():
            p = Poll(title=form.title.data, creator_id=current_user.id)
            db.session.add(p)
            db.session.flush()
            for txt in [form.opt1.data, form.opt2.data, form.opt3.data]:
                if txt:
                    db.session.add(Option(poll_id=p.id, text=txt))
            db.session.commit()
            flash('Опрос создан')
            return redirect(url_for('index'))
        return render_template('create.html', form=form)

    @app.route('/poll/<int:id>')
    def poll(id):
        p = Poll.query.get_or_404(id)
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
        p = Poll.query.get_or_404(id)
        opt_id = request.form.get('option')
        if not opt_id:
            return redirect(url_for('poll', id=id))
        if Vote.query.filter_by(user_id=current_user.id, option_id=opt_id).first():
            flash('Вы уже голосовали')
            return redirect(url_for('poll', id=id))
        print(current_user.username, opt_id)
        db.session.add(Vote(user_id=current_user.id, option_id=int(opt_id)))
        db.session.commit()
        return redirect(url_for('results', id=id))

    @app.route('/results/<int:id>')
    def results(id):
        p = Poll.query.get_or_404(id)
        total = sum(opt.votes.count() for opt in p.options)
        return render_template('results.html', poll=p, total=total)

    with app.app_context():
        db.create_all()
    return app


if __name__ == '__main__':
    create_app().run(port=5000, host='0.0.0.0')
