from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/news')
def news():
    return render_template('news.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/achievements')
def achievements():
    return render_template('achievements.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/ppdb')
def ppdb():
    return render_template('ppdb.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
