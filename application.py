from flask import Flask, request, render_template

app = Flask(__name__)
app.config.from_object(__name__)

@app.route('/')
def front():
	return render_template('front.html')

@app.route('/category')
def category():
	return render_template('category.html')

@app.route('/item')
def category():
	return render_template('item.html')

if __name__=='__main__':
	app.run()