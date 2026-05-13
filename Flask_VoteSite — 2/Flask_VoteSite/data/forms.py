from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange

class RegForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(3,20)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(4,20)])
    confirm = PasswordField('Повтор', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class PollConfigForm(FlaskForm):
    title = StringField('Название опроса', validators=[DataRequired(), Length(3,100)])
    num_options = IntegerField('Количество вариантов', validators=[DataRequired(), NumberRange(min=2, max=10)])
    submit = SubmitField('Далее →')