import base64
import os
import time

from PIL import Image
from flask import Flask, render_template, redirect
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import UploadSet, configure_uploads, IMAGES, UploadNotAllowed
from flask_wtf import FlaskForm
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import StringField, SubmitField, TextAreaField, FileField, PasswordField, BooleanField
from wtforms.validators import DataRequired, EqualTo

app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes_base.db'
app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(os.getcwd(), f'static/images/')
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
try:
    os.mkdir('static/images')
    os.mkdir('static/resized_images')
except FileExistsError:
    pass


class Form(FlaskForm):
    title = StringField("Заголовок", validators=[DataRequired()])
    text = TextAreaField("Текст", validators=[DataRequired()])
    submit = SubmitField("Сохранить")


class ImageForm(FlaskForm):
    image = FileField()
    submit = SubmitField("Сохранить")


class Notes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    text = db.Column(db.String())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return "<Notes {}r>".format(self.id)


class Images(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original = db.Column(db.String())
    minimal = db.Column(db.String())
    time = db.Column(db.String())
    name = db.Column(db.String())
    size = db.Column(db.String())
    size_on_disk = db.Column(db.String())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return "<Images {}r>".format(self.id)


class LoginForm(FlaskForm):
    login = StringField("Ваш логин: ", validators=[DataRequired()])
    password = PasswordField("Пароль: ", validators=[DataRequired()])
    remember = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class RegistrtionForm(FlaskForm):
    login = StringField("Логин: ", validators=[DataRequired()])
    email = StringField("Email: ", validators=[DataRequired()])
    password = PasswordField('Пароль: ', validators=[DataRequired()])
    repeat_password = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField("Зарегестрироваться")


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String())
    email = db.Column(db.String())
    password_hash = db.Column(db.String())
    user_notes = db.relationship('Notes')
    user_images = db.relationship('Images')

    def __repr__(self):
        return "<{}:{}>".format(self.id, self.login)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)


@app.route('/')
@login_required
def main():
    if len(os.listdir('static/images')) or len(os.listdir('static/resized_images')) > 5:
        list(map(lambda x: os.remove('static/images/' + x), os.listdir('static/images')))
        list(map(lambda x: os.remove('static/resized_images/' + x), os.listdir('static/resized_images')))
    return render_template('main.html')


@app.route('/new_form/', methods=['POST', 'GET'])
@login_required
def new_form():
    form = Form()
    if form.validate_on_submit():
        data = Notes(title=form.title.data, text=form.text.data, user_id=current_user.id)
        db.session.add(data)
        db.session.commit()
        return redirect('/view_form')
    return render_template('new_form.html', form=form)


@app.route('/view_form', methods=['GET', 'POST'])
@login_required
def view_form():
    return render_template('view_forms.html', user=current_user)


@app.route('/delete_form/<int:id>')
@login_required
def delete_form(id):
    form_to_delete = Notes.query.filter_by(id=id).first()
    db.session.delete(form_to_delete)
    db.session.commit()
    return redirect('/view_form')


@app.route('/view_images', methods=["POST", "GET"])
@login_required
def view_images():
    image_form = ImageForm()
    if image_form.validate_on_submit():
        try:
            photos.save(image_form.image.data)
            with open('static/images/' + os.listdir('static/images')[0], 'rb') as f:
                image = base64.b64encode(f.read()).decode('utf-8')
            mini_img = Image.open('static/images/' + os.listdir('static/images')[0])
            mini_img.thumbnail((200, 200))
            mini_img.save('static/resized_images/' + os.listdir('static/images')[0])
            with open('static/resized_images/' + os.listdir('static/resized_images')[0], 'rb') as f:
                res_img = base64.b64encode(f.read()).decode('utf-8')
            images = Images(original=image,
                            minimal=res_img,
                            time=time.ctime(os.path.getctime('static/images/' + os.listdir('static/images')[0])),
                            name=os.path.basename('static/images/' + os.listdir('static/images')[0]),
                            size=str(Image.open('static/images/' + os.listdir('static/images')[0]).size),
                            size_on_disk=str(round(
                                os.stat('static/images/' + os.listdir('static/images')[0]).st_size / 1024)) + "КБ",
                            user_id=current_user.id)
            db.session.add(images)
            db.session.commit()
            return redirect('/view_images')
        except UploadNotAllowed:
            pass
    return render_template('view_images.html', image_form=image_form, user_images=current_user.user_images)


@app.route('/delete_image/<int:id>')
@login_required
def delete_image(id):
    img_to_delete = Images.query.filter_by(id=id).first()
    db.session.delete(img_to_delete)
    db.session.commit()
    return redirect('/view_images')


@app.route('/detalied_image/<int:id>')
@login_required
def detailed_image(id):
    img_to_show = Images.query.filter_by(id=id).first()
    about = {}
    about["Имя"] = img_to_show.name
    about["Разрешение"] = img_to_show.size
    about["Размер"] = img_to_show.size_on_disk
    about["Время создания"] = img_to_show.time
    return render_template('detalied_img.html', images=img_to_show, about=about)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter(User.login == form.login.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect('/')
    if current_user.is_authenticated:
        return redirect('/')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


@app.route('/regist', methods=["GET", "POST"])
def registration():
    form = RegistrtionForm()
    if form.validate_on_submit():
        login = form.login.data
        email = form.email.data
        password = form.password.data
        user = User(login=login, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect('/')
    return render_template('registration.html', form=form)


@app.route('/about', methods=["GET", "POST"])
def about():
    about_user = {}
    about_user["Логин"] = current_user.login
    about_user["Почта"] = current_user.email
    return render_template('about.html', user=current_user, about_user=about_user)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get('PORT', 5500)))
