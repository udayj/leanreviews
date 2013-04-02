from flask import Flask, request, render_template, Response, redirect, url_for,flash 
from pymongo import MongoClient
from bson.objectid import ObjectId
import json
import random
from flask.ext.login import (LoginManager, current_user, login_required,
                            login_user, logout_user, UserMixin, AnonymousUser,
                            confirm_login, fresh_login_required)
from flask.ext.mail import Message, Mail
import hashlib
from mongoengine import *

#98744399396 6 core multimode 1000 Mtr.

MAIL_SERVER = 'smtp.googlemail.com'
MAIL_PORT = 465
MAIL_USE_TLS = False
MAIL_USE_SSL = True
MAIL_USERNAME = 'udayj.dev'
MAIL_PASSWORD = 'ud27ay08'
SECRET_KEY='SECRET'
app = Flask(__name__)
app.config.from_object(__name__)


login_manager = LoginManager()

login_manager.login_view = "login"
login_manager.login_message = u"Please log in to access this page."

class User(UserMixin):
    def __init__(self, name, _id, password,email,activation_hash=None,active=True):
        self.name = name
        self.id = _id
        self.active = active
        self.password=password
        self.email=email
        self.activation_hash=activation_hash

    def is_active(self):
        return self.active

@app.route('/')
def front():
	output_review=get_trending_data(3)
	return render_template('front.html',reviews=output_review)

@app.route('/about')
def about():
	
	return render_template('about.html')

@login_manager.user_loader
def load_user(_id):
	client=MongoClient()
	db=client.leanreviews
	user=db.users.find({'_id':ObjectId(_id)})
	try:
		user=user.next()
		ret_user=User(name=user['name'],email=user['email'],password=user['password'],active=user['active'],_id=str(user['_id']))
		return ret_user
	except StopIteration:
		return None

login_manager.setup_app(app)

@app.route('/login',methods=['GET','POST'])
def login():
	if request.method=='GET':
		return render_template('/signup.html')
	data={}
	for name,value in dict(request.form).iteritems():
		data[name]=value[0]
	username=None
	if 'username' in data and 'password' in data:
		username=data['username']
		password=data['password']
	else:
		return render_template('/signup.html')
	client=MongoClient()
	db=client.leanreviews
	user=db.users.find({'name':username,'password':password})
	try:
		user=user.next()
		ret_user=User(name=user['name'],email=user['email'],password=user['password'],active=user['active'],_id=str(user['_id']))
		if login_user(ret_user):
			flash('Logged in!')
			app.logger.debug('logging in user')
			return redirect(url_for('front'))
		else:
			return render_template('/signup.html',error='Cannot login. Account still inactive')
	except StopIteration:
		user=db.users.find({'email':username,'password':password})
		try:
			user=user.next()
			ret_user=User(name=user['name'],email=user['email'],password=user['password'],active=user['active'],_id=str(user['_id']))
			if login_user(ret_user):
				flash('Logged in!')
				app.logger.debug('logging in user')
				return redirect(url_for('front'))
			else:
				return render_template('/signup.html',error='Cannot login. Account still inactive')
		except StopIteration:
			return render_template('/signup.html',error='Cannot login. Wrong credentials')

@app.route("/logout")
@login_required
def logout():
	logout_user()
	flash("Logged out!")
	return redirect(url_for('front'))

@app.route('/activate')
def activate():
	activation_hash=request.args.get('hash')
	if not activation_hash:
		return render_template('activate.html',message='Sorry account not activated')
	client=MongoClient()
	db=client.leanreviews
	user=db.users.find({'activation_hash':activation_hash})
	try:
		user=user.next()
		user['active']=True
		db.users.save(user)
		ret_user=User(name=user['name'],email=user['email'],password=user['password'],active=user['active'],_id=str(user['_id']))
		login_user(ret_user)
		return render_template('activate.html',message='Welcome to Lean Reviews. Your account has been activated')
	except StopIteration:
		return render_template('activate.html',message='Sorry account not activated')

@app.route('/signup',methods=['GET','POST'])
def signup():
	if request.method=='GET':
		return render_template('signup.html')
	else:
		data={}
		for name,value in dict(request.form).iteritems():
			data[name]=value[0].lower().strip()
		username=None
		if 'username' in data:
			username=data['username']
		client=MongoClient()
		db=client.leanreviews
		salt='leanreviewactivateusingtoken'
		activation_hash=hashlib.sha512(salt+data['email']).hexdigest()[10:30]
		if username:
			exist_user=db.users.find({'name':username})
			try:
				exist_user.next()
				return render_template('signup.html',signup_error='Username already exists',username=username,email=data['email'])
			except StopIteration:
				pass
		exist_user=db.users.find({'email':data['email']})
		try:
			exist_user.next()
			app.logger.debug(username)
			app.logger.debug(data['email'])
			return render_template('signup.html',signup_error='Email already exists',username=username,email=data['email'])
		except StopIteration:
			pass

		_id=db.users.save({'name':username,
					   'email':data['email'],
					   'password':data['password'],
					   'activation_hash':activation_hash,
					   'active':False})
		#user=User(name=username,email=data['email'],password=data['password'],active=False,id=str(_id))
		msg = Message('Welcome to Lean Reviews', sender = 'udayj.dev@gmail.com', recipients = [data['email']])
		mail=Mail(app)
		
		msg.body = 'Click this link to activate your account http://localhost:5000/activate?hash='+activation_hash
		
		app.logger.debug(activation_hash)

		mail.send(msg)
		return render_template('checkmail.html')


@app.route('/add_new')
@login_required
def add_new():
	return render_template('add_new.html')

@app.route('/browse/<category>')
def category(category):
	page=request.args.get('p')
	app.logger.debug(request.path)
	if not page:
		page=1
	else:
		try:
			page=int(page)
		except ValueError:
			page=1
	client=MongoClient()
	db=client.leanreviews
	collection=db.categories
	present_category=collection.find({'name':category})
	try:
		present_category=present_category.next()
	except StopIteration:
		return render_template('error.html')
	review_ids=present_category['review_ids']
	active_categories=['books','movies','places','people','trending']
	active={}
	for active_category in active_categories:
		active[active_category]="inactive"
	active[category]="active"
	
	display={'books':'Book Reviews','movies':'Movie Reviews','places':'Place Reviews','people':'People Reviews'}

	app.logger.debug(str(review_ids))
	start=(page-1)*9
	if start>len(review_ids)-1:
		start=0
		page=1
	end=start+9
	if start+9>=len(review_ids):
		end=len(review_ids)
	output_review=[]
	for count in range(start,end):
		review=db.reviews.find({'_id':review_ids[count]})
		review=review.next()
		data=[]
		for word,value in review['words'].iteritems():
			data.append({'text':word,'size':value})
		output_review.append({'name':review['display_name'],'data':json.dumps(data),
							  'url':'/item?name='+review['name']+'&id='+str(review['_id'])})
	left=None
	left_ellipses=None
	prev=None
	next=None
	right_ellipses=None
	right=None
	if page>1:
		prev=page-1
		left=page-1
	if page>=3:
		left_ellipses=True
	if end<len(review_ids)-1:
		next=page+1
		right=page+1
	if end+18<len(review_ids)-1:
		right_ellipses=True
	pagination=[]
	pagination.append(left)
	pagination.append(left_ellipses)
	pagination.append(prev)
	pagination.append(page)
	pagination.append(next)
	pagination.append(right_ellipses)
	pagination.append(right)

	return render_template('category.html',display_message=display[category],reviews=output_review,length=len(output_review),pagination=pagination,url=request.path,active=active)

@app.route('/item')
def item():
	client=MongoClient()
	db=client.leanreviews
	collection=db.reviews
	_id=request.args.get('id')
	review=None
	cursor=None
	if _id:
		review=collection.find({'_id':ObjectId(_id)})
		cursor=review
		try:
			
			review=review.next()
			app.logger.debug('find by id')
		except StopIteration:
			name=request.args.get('name')
			if not name:
				return render_template('error.html')
			name=name.lower().strip()
			review=collection.find({'name':name})
			cursor=review
			try:
				review=review.next()
				app.logger.debug('find by name')
			except StopIteration:
				return render_template('error.html')
	else:
		name=request.args.get('name')
		if not name:
			return render_template('error.html')
		name=name.lower().strip()
		review=collection.find({'name':name})
		cursor=review
		try:
			review=review.next()
		except StopIteration:
			return render_template('error.html')
	total_reviews=[review]
	for review in cursor:
		total_reviews.append(review)
	app.logger.debug(total_reviews)
	if len(total_reviews)==1:
		data=[]
		output_review={}
		for word,value in review['words'].iteritems():
			data.append({'text':word,'size':value})
		output_review['id']=review['_id']
		output_review['name']=review['display_name']
		output_review['data']=json.dumps(data)
		output_review['upvote']=review['upvote']
		output_review['downvote']=review['downvote']
		app.logger.debug(output_review)
		return render_template('item.html',review=output_review)
	else:
		page=request.args.get('p')
		app.logger.debug(request.path)
		if not page:
			page=1
		else:
			try:
				page=int(page)
			except ValueError:
				page=1
		start=(page-1)*9
		if start>len(total_reviews)-1:
			start=0
			page=1
		end=start+9
		if start+9>=len(total_reviews):
			end=len(total_reviews)
		output_review=[]
		for count in range(start,end):
			review=total_reviews[count]
			data=[]
			for word,value in review['words'].iteritems():
				data.append({'text':word,'size':value})
			output_review.append({'name':review['display_name'],'data':json.dumps(data),
								  'url':'/item?name='+review['name']+'&id='+str(review['_id'])})
		left=None
		left_ellipses=None
		prev=None
		next=None
		right_ellipses=None
		right=None
		if page>1:
			prev=page-1
			left=page-1
		if page>=3:
			left_ellipses=True
		if end<len(total_reviews)-1:
			next=page+1
			right=page+1
		if end+18<len(total_reviews)-1:
			right_ellipses=True
		pagination=[]
		pagination.append(left)
		pagination.append(left_ellipses)
		pagination.append(prev)
		pagination.append(page)
		pagination.append(next)
		pagination.append(right_ellipses)
		pagination.append(right)
		active_categories=['books','movies','places','people','trending']
		active={}
		for active_category in active_categories:
			active[active_category]="inactive"
		

		return render_template('category.html',display_message='Multiple Reviews Retrieved',reviews=output_review,
								length=len(output_review),pagination=pagination,url=request.path,active=active)
def get_trending_data(count):
	client=MongoClient()
	db=client.leanreviews
	collection=db.categories
	categories=['books','movies','places','people']
	review_ids_mixed=[]
	for category in categories:
		present_category=collection.find({'name':category})
		app.logger.debug(category)
		present_category=present_category.next()
		review_ids=present_category['review_ids']
		review_ids_mixed=review_ids_mixed+review_ids
	random.shuffle(review_ids_mixed)
	output_review=[]
	for count in range(0,count):
		review=db.reviews.find({'_id':review_ids_mixed[count]})
		app.logger.debug(str(review_ids_mixed[count]))
		review=review.next()
		data=[]
		for word,value in review['words'].iteritems():
			data.append({'text':word,'size':value})
		output_review.append({'name':review['display_name'],'data':json.dumps(data),
							  'url':'/item?name='+review['name']+'&id='+str(review['_id'])})
	return output_review

@app.route('/trending')
def trending():
	output_review=get_trending_data(9)
	return render_template('trending.html',reviews=output_review,length=9)

@app.route('/rate_item',methods=['POST'])
@login_required
def rate_item():
	
	app.logger.debug(str(request.form))
	data={}
	for name,value in dict(request.form).iteritems():
		data[name]=value[0].lower().strip()
	client=MongoClient()
	db=client.leanreviews
	app.logger.debug(data)
	review=db.reviews.find({'_id':ObjectId(data['id'])})
	review=review.next()
	_id=review['_id']
	if data['vote']=='up_vote':
		new_upvote=review['upvote']+1
		review['upvote']=new_upvote
		db.reviews.save(review)
		#result=db.reviews.update({'_id':str(_id)},{'$set':{'upvote':new_upvote}})
	else:
		review['downvote']=review['downvote']+1
		db.reviews.save(review)

	js=json.dumps({'success':'success'})

	resp = Response(js, status=200, mimetype='application/json')
	return resp

@app.route('/review_item',methods=['POST'])
@login_required
def review_item():
	
	app.logger.debug(str(request.form))
	data={}
	for name,value in dict(request.form).iteritems():
		data[name]=value[0].lower().strip()
	client=MongoClient()
	db=client.leanreviews
	review=db.reviews.find({'_id':ObjectId(data['id'])})
	review=review.next()
	if data['review'] in review['words']:
		review['words'][data['review']]=review['words'][data['review']]+1
	else:
		review['words'][data['review']]=1
	db.reviews.save(review)
	js=json.dumps({'success':'success'})

	resp = Response(js, status=200, mimetype='application/json')
	return resp

@app.route('/process_new_item',methods=['POST'])
@login_required
def process_new_item():
	data={}
	for name,value in dict(request.form).iteritems():
		if name in ('category','review'):
			data[name]=value[0].lower().strip()
		else:
			data[name]=value[0]
	app.logger.debug(data)
	client=MongoClient()
	db=client.leanreviews
	_id=db.reviews.save({'name':data['name'].lower().strip(),
					 'display_name':data['name'],
					 'description':data['description'],
					 'categories':data['category'],
					 'words':{data['review']:40},
					 'upvote':0,
					 'downvote':0})
	app.logger.debug(_id)
	if data['category']:
		category=db.categories.find({'name':data['category']})
		try:
			category=category.next()
			category['review_ids'].append(_id)
			db.categories.save(category)
		except StopIteration:
			category={'name':data['category'],'review_ids':[_id]}
			db.categories.save(category)


	
	return redirect(url_for('item',id=str(_id),name=data['name'].lower().strip()))


if __name__=='__main__':
	app.run(debug=True)