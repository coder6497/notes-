from flask import Flask, render_template, redirect
from flask_wtf import FlaskForm
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from wtforms import StringField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
import os
import time


app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes_base.db'
app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(os.getcwd(), 'images')
db = SQLAlchemy(app)

photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
patch_request_class(app, None)


class Form(FlaskForm):
    title = StringField("Заголовок", validators=[DataRequired()])
    text = TextAreaField("Текст", validators=[DataRequired()])
    image = FileField()
    submit = SubmitField("Сохранить")


class Notes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    text = db.Column(db.String())
    image_path = db.Column(db.String())

    def __repr__(self):
        return "<Notes {}r>".format(self.id)


@app.route('/')
def main():
    return render_template('main.html')


@app.route('/new_form', methods=['POST', 'GET'])
def new_form():
    form = Form()
    if form.validate_on_submit():
        title = form.title.data
        text = form.text.data
        data = Notes(title=title, text=text)
        db.session.add(data)
        db.session.commit()
        photo_save()
        return redirect('/view_form')
    return render_template('new_form.html', form=form)


def photo_save():
    try:
        form = Form()
        if form.validate_on_submit():
            photos.save(form.image.data)
            img_dir = list(map(lambda x: 'images/' + x, os.listdir('images')))
            sorted_by_time = sorted(img_dir, key=lambda x: os.path.getctime(x), reverse=True)
            print(sorted_by_time)
    except Exception:
        pass


@app.route('/view_form', methods=['GET', 'POST'])
def view_form():
    return render_template('view_forms.html', view_data=Notes.query.all())


@app.route('/delete_form/<int:id>')
def delete_form(id):
    form_to_delete = Notes.query.filter_by(id=id).first()
    db.session.delete(form_to_delete)
    db.session.commit()
    return redirect('/view_form')


if __name__ == '__main__':
    app.run(debug=True)
