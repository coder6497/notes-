import os
import time

from PIL import Image
from flask import Flask, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import UploadSet, configure_uploads, IMAGES, UploadNotAllowed
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, FileField, PasswordField, BooleanField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user, logout_user

app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes_base.db'
app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(os.getcwd(), 'static/images')
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)


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

    def __repr__(self):
        return "<Notes %sr>".format(self.id)


class LoginForm(FlaskForm):
    login = StringField("Ваш логин: ", validators=[DataRequired()])
    password = PasswordField("Пароль: ", validators=[DataRequired()])
    remember = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String())
    email = db.Column(db.String())
    password_hash = db.Column(db.String())

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
    sorted_img_lst = sorted(list(map(lambda x: 'static/resized_images/' + x, os.listdir('static/resized_images'))),
                            key=lambda x: os.path.getctime(x), reverse=True)
    return render_template('main.html', sorted_img_lst=sorted_img_lst)


@app.route('/new_form', methods=['POST', 'GET'])
@login_required
def new_form():
    form = Form()
    if form.validate_on_submit():
        title = form.title.data
        text = form.text.data
        data = Notes(title=title, text=text)
        db.session.add(data)
        db.session.commit()
        return redirect('/view_form')
    return render_template('new_form.html', form=form)


@app.route('/view_form', methods=['GET', 'POST'])
@login_required
def view_form():
    return render_template('view_forms.html', view_data=Notes.query.all())


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
            return redirect('/view_images')
        except UploadNotAllowed:
            pass
    img_lst = list(map(lambda x: x, os.listdir('static/images')))
    for img in img_lst:
        image = Image.open('static/images/' + img)
        image.thumbnail((200, 200))
        image.save('static/resized_images/' + img)
    min_lst = list(map(lambda x: 'static/resized_images/' + x, os.listdir('static/resized_images')))
    name_lst = os.listdir('static/images')
    return render_template('view_images.html', image_form=image_form, min_lst=min_lst, name_lst=name_lst)


@app.route('/delete_image/<string:path>')
@login_required
def delete_image(path):
    img_path_orig = eval(path)
    img_path_min = '/'.join(eval(path))
    os.remove('static/images/' + img_path_orig[-1])
    os.remove(img_path_min)
    return redirect('/view_images')


@app.route('/detalied_image/<string:path>')
@login_required
def detailed_image(path):
    res_img_path = eval(path)
    res_img_path[1] = 'images'
    orig_image_path = '/'.join(res_img_path)
    about = {}
    about['Название'] = res_img_path[-1]
    about["Время создания"] = time.ctime(os.path.getctime(orig_image_path))
    about['Разрешение'] = Image.open(orig_image_path).size
    about["Размер"] = str(round(os.stat(orig_image_path).st_size / 1024)) + 'КБ'
    return render_template('detalied_img.html', orig_image_path=orig_image_path, res_img_path=res_img_path, about=about)


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


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
