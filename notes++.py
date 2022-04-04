from flask import Flask, render_template
from forms import Form

app = Flask(__name__)
app.config['SECRET_KEY'] = 'key'


@app.route('/')
def main():
    return render_template('main.html')


@app.route('/new_form', methods=['POST', 'GET'])
def new_form():
    form = Form()
    if form.validate_on_submit():
        title = form.title.data
        text = form.text.data
        print(title, text)
    return render_template('new_form.html', form=form)


if __name__ == '__main__':
    app.run(debug=True)
