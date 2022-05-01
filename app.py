import base64
import os
import time

from PIL import Image
from flask import Flask
from flask import render_template, redirect
from flask_login import login_required, login_user, current_user, logout_user, UserMixin, LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import UploadSet, IMAGES, AUDIO, configure_uploads, UploadNotAllowed
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import StringField, SubmitField, TextAreaField, FileField, PasswordField, BooleanField
from wtforms.validators import DataRequired, EqualTo

app = Flask(__name__)
db = SQLAlchemy(app)
app.config['SECRET_KEY'] = 'key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes_base.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(os.getcwd(), 'static/images/')
app.config['UPLOADED_AUDIOS_DEST'] = os.path.join(os.getcwd(), 'static/audio/')
login_manager = LoginManager(app)
login_manager.login_view = 'login'

photos = UploadSet('photos', IMAGES)
audios = UploadSet('audios', AUDIO)
configure_uploads(app, (photos, audios))
try:
    os.mkdir('static/images')
    os.mkdir('static/resized_images')
except FileExistsError:
    pass


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String())
    email = db.Column(db.String())
    phone = db.Column(db.String())
    avatar = db.Column(db.String())
    password_hash = db.Column(db.String())
    user_notes = db.relationship('Notes')
    user_images = db.relationship('Images')
    user_audios = db.relationship('Audios')

    def __repr__(self):
        return "<{}:{}>".format(self.id, self.login)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


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


class Audios(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    audio_data = db.Column(db.String())
    name = db.Column(db.String())
    size_on_disk = db.Column(db.String())
    time = db.Column(db.String())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return "<Audios {}r".format(self.id)


class Form(FlaskForm):
    title = StringField("Заголовок", validators=[DataRequired()])
    text = TextAreaField("Текст", validators=[DataRequired()])
    submit = SubmitField("Сохранить")


class ImageForm(FlaskForm):
    image = FileField()
    submit = SubmitField("Сохранить")


class AvatarForm(FlaskForm):
    image = FileField()
    submit = SubmitField("Загрузить")


class LoginForm(FlaskForm):
    login = StringField("Ваш логин: ", validators=[DataRequired()])
    password = PasswordField("Пароль: ", validators=[DataRequired()])
    remember = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class RegistrtionForm(FlaskForm):
    login = StringField("Логин: ", validators=[DataRequired()])
    email = StringField("Email: ", validators=[DataRequired()])
    phone = StringField("Номер телефона: ", validators=[DataRequired()])
    password = PasswordField('Пароль: ', validators=[DataRequired()])
    repeat_password = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField("Зарегестрироваться")


class EditUser(FlaskForm):
    login = StringField("Логин: ", validators=[DataRequired()])
    email = StringField("Email: ", validators=[DataRequired()])
    phone = StringField("Номер телефона: ", validators=[DataRequired()])
    submit = SubmitField("Изменить")


class AudioForm(FlaskForm):
    audio = FileField()
    submit = SubmitField("Сохранить")


@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(user_id)


@app.route('/')
@login_required
def main():
    if len(os.listdir('static/images')) or len(os.listdir('static/resized_images')) > 5:
        list(map(lambda x: os.remove('static/images/' + x), os.listdir('static/images')))
        list(map(lambda x: os.remove('static/resized_images/' + x), os.listdir('static/resized_images')))
    if len(os.listdir('static/audio')) > 5:
        list(map(lambda x: os.remove('static/audio/' + x), os.listdir('static/audio')))
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
            list_orig = sorted(os.listdir('static/images'), key=lambda x: os.path.getctime('static/images/' + x),
                               reverse=True)
            with open('static/images/' + list_orig[0], 'rb') as f:
                image = base64.b64encode(f.read()).decode('utf-8')
            mini_img = Image.open('static/images/' + list_orig[0])
            mini_img.thumbnail((200, 200))
            mini_img.save('static/resized_images/' + list_orig[0])
            list_mini = sorted(os.listdir('static/resized_images'),
                               key=lambda x: os.path.getctime('static/resized_images/' + x), reverse=True)
            with open('static/resized_images/' + list_mini[0], 'rb') as f:
                res_img = base64.b64encode(f.read()).decode('utf-8')
            images = Images(original=image,
                            minimal=res_img,
                            time=time.ctime(os.path.getctime('static/images/' + list_orig[0])),
                            name=os.path.basename('static/images/' + list_orig[0]),
                            size=str(Image.open('static/images/' + list_mini[0]).size),
                            size_on_disk=str(round(
                                os.stat('static/images/' + list_orig[0]).st_size / 1024)) + "КБ",
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


@app.route('/audio', methods=["GET", "POST"])
@login_required
def audio():
    form = AudioForm()
    if form.validate_on_submit():
        audios.save(form.audio.data)
        audio_list = sorted(os.listdir('static/audio'), key=lambda x: os.path.getctime('static/audio/' + x),
                            reverse=True)
        with open('static/audio/' + audio_list[0], 'rb') as f:
            audio_code = base64.b64encode(f.read()).decode('utf-8')
        audios_base = Audios(audio_data=audio_code,
                             name=os.path.basename('static/audio/' + audio_list[0]),
                             size_on_disk=str(round(os.stat('static/audio/' + audio_list[0]).st_size / 1024)) + "КБ",
                             time=time.ctime(os.path.getctime('static/audio/' + audio_list[0])),
                             user_id=current_user.id)
        db.session.add(audios_base)
        db.session.commit()
    return render_template('view_audios.html', form=form, user_audios=current_user.user_audios)


@app.route('/delete_audio/<int:id>')
def delete_audio(id):
    audio_to_delete = Audios.query.filter_by(id=id).first()
    db.session.delete(audio_to_delete)
    db.session.commit()
    return redirect('/audio')


@app.route('/detalied_audio/<int:id>')
def detalied_audio(id):
    audio_to_show = Audios.query.filter_by(id=id).first()
    about_audio = {}
    about_audio["Имя"] = audio_to_show.name
    about_audio["Время"] = audio_to_show.time
    about_audio["Размер"] = audio_to_show.size_on_disk
    return render_template('detalied_audio.html', audio=audio_to_show, about=about_audio)


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
        user = User(login=form.login.data, email=form.email.data, phone=form.phone.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        return redirect('/')
    return render_template('registration.html', form=form)


@app.route('/about', methods=["GET", "POST"])
def about():
    about_user = {}
    about_user["Логин"] = current_user.login
    about_user["Почта"] = current_user.email
    about_user["Номер телефона"] = current_user.phone
    form = AvatarForm()
    if form.validate_on_submit():
        try:
            photos.save(form.image.data)
            orig_list = sorted(os.listdir('static/images'), key=lambda x: os.path.getctime('static/images/' + x),
                               reverse=True)
            avatar_img = Image.open('static/images/' + orig_list[0])
            avatar_img.thumbnail((150, 150))
            avatar_img.save('static/resized_images/' + orig_list[0])
            avatar_list = sorted(os.listdir('static/resized_images'),
                                 key=lambda x: os.path.getctime('static/resized_images/' + x), reverse=True)
            with open('static/resized_images/' + avatar_list[0], 'rb') as f:
                avatar = base64.b64encode(f.read()).decode('utf-8')
            current_user.avatar = avatar
            db.session.commit()
        except UploadNotAllowed:
            pass
    return render_template('about.html', user=current_user, about_user=about_user, form=form,
                           user_avatar=current_user.avatar)


@app.route('/edit_user/', methods=["GET", "POST"])
@login_required
def edit_user():
    form = EditUser()
    if form.validate_on_submit:
        current_user.login = form.login.data
        current_user.phone = form.phone.data
        current_user.email = form.email.data
        db.session.commit()
    return render_template("edit_user.html", form=form)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get('PORT', 5500)))
