import os
import time

from PIL import Image
from flask import Flask, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class, UploadNotAllowed
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, FileField
from wtforms.validators import DataRequired

app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes_base.db'
app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(os.getcwd(), 'static/images')
db = SQLAlchemy(app)

photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
patch_request_class(app, None)


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
        return redirect('/view_form')
    return render_template('new_form.html', form=form)


@app.route('/view_form', methods=['GET', 'POST'])
def view_form():
    return render_template('view_forms.html', view_data=Notes.query.all())


@app.route('/delete_form/<int:id>')
def delete_form(id):
    form_to_delete = Notes.query.filter_by(id=id).first()
    db.session.delete(form_to_delete)
    db.session.commit()
    return redirect('/view_form')


@app.route('/view_images', methods=["POST", "GET"])
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
def delete_image(path):
    img_path_orig = eval(path)
    img_path_min = '/'.join(eval(path))
    os.remove('static/images/' + img_path_orig[-1])
    os.remove(img_path_min)
    return redirect('/view_images')


@app.route('/detalied_image/<string:path>')
def detailed_image(path):
    res_img_path = eval(path)
    res_img_path[1] = 'images'
    orig_image_path = '/'.join(res_img_path)
    about = {}
    about['Название'] = res_img_path[-1]
    about["Время создания"] = time.ctime(os.path.getctime(orig_image_path))
    about['Разрешение'] = Image.open(orig_image_path).size
    about["Размер"] = str(round(os.stat(orig_image_path).st_size / 1024)) + 'КБ'
    print(about)
    return render_template('detalied_img.html', orig_image_path=orig_image_path, res_img_path=res_img_path, about=about)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8808)
