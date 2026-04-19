from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


class RegForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(3, 20)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(4, 20)])
    confirm = PasswordField('Повтор', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')


class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class PollForm(FlaskForm):
    title = StringField('Название опроса', validators=[DataRequired()])
    opt1 = StringField('Вариант 1', validators=[DataRequired()])
    opt2 = StringField('Вариант 2', validators=[DataRequired()])
    opt3 = StringField('Вариант 3')
    submit = SubmitField('Создать')