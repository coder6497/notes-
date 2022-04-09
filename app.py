from flask import Flask, render_template, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes_base.db'
db = SQLAlchemy(app)


class Form(FlaskForm):
    title = StringField("Заголовок", validators=[DataRequired()])
    text = TextAreaField("Текст", validators=[DataRequired()])
    submit = SubmitField("Сохранить")


class Notes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    text = db.Column(db.String(120))

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


if __name__ == '__main__':
    app.run(debug=True)
