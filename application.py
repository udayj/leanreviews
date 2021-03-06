 # -*- coding: utf-8 -*-
from flask import Flask, request, render_template, Response, redirect, url_for,flash 
from pymongo import MongoClient
from bson.objectid import ObjectId
import json
import random
from flask.ext.login import (LoginManager, current_user, login_required,
                            login_user, logout_user, UserMixin, AnonymousUser,
                            confirm_login, fresh_login_required,login_url)
from flask.ext.mail import Message, Mail
import hashlib
from oauth2client.client import OAuth2WebServerFlow
import httplib2
import urllib
import cgi
import ast
import base64
import codecs
import urllib2
import nltk
import datetime
import re


SECRET_KEY='SECRET'
SALT='123456789passwordsalt'
FACEBOOK_APP_ID='423477151081458'
FACEBOOK_APP_SECRET='2c16203539a13addf1ed141e7a68dbd7'

app = Flask(__name__)
app.config.from_envvar('CONFIG_FILE')
app.debug=app.config['DEBUG']


login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = u"Please log in to access this page."

mail=Mail(app)



class User(UserMixin):
    def __init__(self, name, _id, password,email,activation_hash=None,active=True,access_token=None,fb_id=None):
        self.name = name
        self.id = _id
        self.active = active
        self.password=password
        self.email=email
        self.activation_hash=activation_hash
        self.access_token=access_token
        self.fb_id=fb_id

    def is_active(self):
        return self.active

@app.route('/review_analytics',methods=['GET','POST'])
def get_review_content():
	if request.method=='GET':
		return render_template('review_analytics.html')
	else:
		data={}
		for name,value in dict(request.form).iteritems():
			data[name]=value[0].lower().strip()
		client=MongoClient()
		db=client[app.config['DATABASE']]
		review=None
		words=data['words']
		app.logger.debug(words)
		words=words.replace('“',' ')
		words=words.encode('utf-8')
		tokens=nltk.word_tokenize(words)
		text=nltk.Text(tokens)
		feq=nltk.FreqDist(text)
		app.logger.debug(feq.keys())
		app.logger.debug(type(text))
		output=[]
		for key in feq.keys():
			output.append({'text':key,'size':70-feq[key]})


		js=json.dumps({'success':'success','words':output})
		resp = Response(js, status=200, mimetype='application/json')
		return resp



def get_leaderboard():
	client=MongoClient()
	db=client[app.config['DATABASE']]
	cursor=db.users.find()
	users=[]
	def sort_function(user):
		return -user['kudos']
	for user in cursor:
		users.append(user)
	users.sort(key=sort_function)
	return users[:5]

def get_recent_reviews():
	client=MongoClient()
	db=client[app.config['DATABASE']]
	cursor=db.recentreviews.find()
	reviews=[]
	for review in cursor:
		reviews.append(review)
	return reviews

@app.route('/')
def front():
	
	output_review=get_trending_data(6)
	users=get_leaderboard()
	#recent_reviews=get_recent_reviews()
	return render_template('front.html',reviews=output_review,active='front',users=users,length=6,title='Quick reviews for almost anything',
							meta_description='Lean Reviews provides a quick and clean crowd opinion and review on almost anything.')

@app.route('/about')
def about():
	
	return render_template('about.html',title='About',active='about')

@login_manager.user_loader
def load_user(_id):
	client=MongoClient()
	db=client[app.config['DATABASE']]
	user=db.users.find({'_id':ObjectId(_id)})
	try:
		user=user.next()
		access_token=''
		fb_id=''
		try:
			access_token=user['access_token']
			fb_id=user['fb_id']
			kudos=user['kudos']
		except Exception:
			access_token=''
			fb_id=''
		ret_user=User(name=user['name'],email=user['email'],password="",active=user['active'],_id=str(user['_id']),
					access_token=access_token,fb_id=fb_id)
		return ret_user
	except StopIteration:
		return None

login_manager.setup_app(app)

@app.route('/google_oauth_callback')
def google_oauth_callback():
	client=MongoClient()
	db=client[app.config['DATABASE']]
	flow = OAuth2WebServerFlow(client_id='738745937386.apps.googleusercontent.com',
                           client_secret='cIy6tyZyyKXeSc8YfqXWtQtS',
                           scope='https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email',
                           redirect_uri=app.config['HOST']+'/google_oauth_callback',
                           access_type='online')

	facebook_login='https://graph.facebook.com/oauth/authorize?scope=email&client_id=423477151081458&redirect_uri='+app.config['HOST']+'/facebook_oauth_callback'

	code=request.args['code']
	credentials=flow.step2_exchange(code)
	http=httplib2.Http()
	http=credentials.authorize(http)
	try:
		resp, content=http.request('https://www.googleapis.com/oauth2/v1/userinfo','GET')
		content=json.loads(content)
		user=db.users.find({'email':content['email']})

		try:
			user=user.next()

			ret_user=User(name=content['name'],email=content['email'],password="",active=True,_id=str(user['_id']))
			if login_user(ret_user):
				flash('Logged in!')
				return redirect(url_for('front'))
			else:
				return render_template('/signup.html',error='Cannot login. Some problem on our server. Check back in a few minutes.',
										google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login)
		except Exception:		
			_id=db.users.save({'name':content['name'],
							   'email':content['email'],
							   'password':'',
							   'activation_hash':'',
							   'reviews_submitted':0,
							   'reviews_created':0,
							   'kudos':0,
							   'active':True})
			ret_user=User(name=content['name'],email=content['email'],password="",active=True,_id=str(_id),access_token='',fb_id='')
			if login_user(ret_user):
				flash('Logged in!')
				return redirect(url_for('front'))
			else:
				return render_template('/signup.html',error='Cannot login. Some problem on our server. Check back in a few minutes',
										google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login)
	except Exception:
			return render_template('/signup.html',error='Cannot login now. Some problem on our server. Check back in a few minutes.',
									google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login)

@app.route('/facebook_oauth_callback')
def facebook_oauth_callback():
	flow = OAuth2WebServerFlow(client_id='738745937386.apps.googleusercontent.com',
                           client_secret='cIy6tyZyyKXeSc8YfqXWtQtS',
                           scope='https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email',
                           redirect_uri=app.config['HOST']+'/google_oauth_callback',
                           access_type='online')
	facebook_login='https://graph.facebook.com/oauth/authorize?scope=email,publish_actions&client_id=423477151081458&redirect_uri='+app.config['HOST']+'/facebook_oauth_callback'
	client=MongoClient()
	db=client[app.config['DATABASE']]
	args = dict(client_id=FACEBOOK_APP_ID,
                redirect_uri=app.config['HOST']+'/facebook_oauth_callback')
	code=request.args['code']
	if not code:
		return render_template('/signup.html',error='Cannot login. Some problem on our server. Check back in a few minutes.')
	args["client_secret"] = FACEBOOK_APP_SECRET
	args["code"] = code
	response=None
	try:
		response = cgi.parse_qs(urllib.urlopen("https://graph.facebook.com/oauth/access_token?" +urllib.urlencode(args)).read()+"&scope=email,publish_actions")
	except Exception as e:
		app.logger.debug(str(e))
		#app.logger.debug(response)
		return render_template('/signup.html',error='Cannot login. Some problem on our server. Check back in a few minutes.',
								google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login)
	access_token = response["access_token"][-1]
	app.logger.debug(access_token)
	user=None
	try:
		content = json.load(urllib.urlopen("https://graph.facebook.com/me?" +urllib.urlencode(dict(access_token=access_token))))
		user=db.users.find({'email':content['email']})
	except Exception:
		app.logger.debug('Problem geting user data from facebook')
		return render_template('/signup.html',error='Cannot login. Some problem on our server. Check back in a few minutes.',
								google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login)
	
	try:
		user=user.next()
		ret_user=User(name=content['name'],email=content['email'],password="",active=True,_id=str(user['_id']),
					access_token=access_token,fb_id=content['id'])
		if login_user(ret_user):
			flash('Logged in!')
			return redirect(url_for('front'))
		else:
			return render_template('/signup.html',error='Cannot login. Some problem on our server. Check back in a few minutes.',
									google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login)
	except Exception:		
		_id=db.users.save({'name':content['name'],
						   'email':content['email'],
						   'password':'',
						   'activation_hash':'',
						   'reviews_submitted':0,
						   'reviews_created':0,
						   'kudos':0,
						   'access_token':access_token,
						   'fb_id':content['id'],
						   'active':True})
		ret_user=User(name=content['name'],email=content['email'],password="",active=True,_id=str(_id),access_token=access_token,fb_id=content['id'])
		if login_user(ret_user):
			flash('Logged in!')
			return redirect(url_for('front'))
		else:
			return render_template('/signup.html',error='Cannot login. Some problem on our server. Check back in a few minutes',
									google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login)
		
@app.route('/login',methods=['GET','POST'])
def login():
	flow = OAuth2WebServerFlow(client_id='738745937386.apps.googleusercontent.com',
                           client_secret='cIy6tyZyyKXeSc8YfqXWtQtS',
                           scope='https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email',
                           redirect_uri=app.config['HOST']+'/google_oauth_callback',
                           access_type='online')
	facebook_login='https://graph.facebook.com/oauth/authorize?scope=email,publish_actions&client_id=423477151081458&redirect_uri='+app.config['HOST']+'/facebook_oauth_callback'


	if request.method=='GET':
		return render_template('/signup.html',google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login,active='login',
								title='quick reviews for almost anything')
	data={}
	for name,value in dict(request.form).iteritems():
		data[name]=value[0]
	username=None
	if 'username' in data and 'password' in data:
		username=data['username']
		password=data['password']
	else:
		app.logger.debug('Login Form submitted without fields')
		return render_template('/signup.html')
	client=MongoClient()
	db=client[app.config['DATABASE']]
	password=hashlib.sha512(SALT+password).hexdigest()
	user=db.users.find({'name':username,'password':password})
	try:
		user=user.next()
		ret_user=User(name=user['name'],email=user['email'],password="",active=user['active'],_id=str(user['_id']),access_token='',fb_id='')
		if login_user(ret_user):
			flash('Logged in!')
			return redirect(url_for('front'))
		else:
			return render_template('/signup.html',error='Cannot login. Account still inactive',
									google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login,active='login')
	except StopIteration:
		user=db.users.find({'email':username,'password':password})
		try:
			user=user.next()
			ret_user=User(name=user['name'],email=user['email'],password="",active=user['active'],_id=str(user['_id']),access_token='',fb_id='')
			if login_user(ret_user):
				flash('Logged in!')
				return redirect(url_for('front'))
			else:
				return render_template('/signup.html',error='Cannot login. Account still inactive',
										google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login,active='login')
		except StopIteration:
			return render_template('/signup.html',error='Cannot login. Wrong credentials',
									google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login,active='login')

@app.route("/logout")
@login_required
def logout():
	logout_user()
	flash("Logged out!")
	return redirect(url_for('front'))

@app.route('/profile')
def profile():
	_id=request.args.get('id')
	name=request.args.get('name')
	client=MongoClient()
	db=client[app.config['DATABASE']]
	if not _id:
		return render_template('error.html')
	user=db.users.find({'_id':ObjectId(_id)})
	try:
		user=user.next()
	except StopIteration:
		return render_template('error.html')
	try:
		kudos=user['kudos']
		reviews_submitted=user['reviews_submitted']
		reviews_created=user['reviews_created']
	except Exception:
		kudos=0
		reviews_submitted=0
		reviews_created=0
	return render_template('profile.html',user=user)

@app.route('/activate')
def activate():
	activation_hash=request.args.get('hash')
	if not activation_hash:
		return render_template('activate.html',message='Sorry account not activated')
	client=MongoClient()
	db=client[app.config['DATABASE']]
	user=db.users.find({'activation_hash':activation_hash})
	try:
		user=user.next()
		user['active']=True
		db.users.save(user)
		ret_user=User(name=user['name'],email=user['email'],password="",active=user['active'],_id=str(user['_id']),access_token='',fb_id='')
		login_user(ret_user)
		return render_template('activate.html',message='Welcome to Lean Reviews. Your account has been activated')
	except StopIteration:
		return render_template('activate.html',message='Sorry account not activated')


@app.route('/signup',methods=['GET','POST'])
def signup():
	flow = OAuth2WebServerFlow(client_id='738745937386.apps.googleusercontent.com',
                           client_secret='cIy6tyZyyKXeSc8YfqXWtQtS',
                           scope='https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email',
                           redirect_uri=app.config['HOST']+'/google_oauth_callback',
                           access_type='online')
	facebook_login='https://graph.facebook.com/oauth/authorize?scope=email,publish_actions&client_id=423477151081458&redirect_uri='+app.config['HOST']+'/facebook_oauth_callback'


	if request.method=='GET':
		return render_template('/signup.html',google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login,active='signup',
								title='quick reviews for almost anything')
	else:
		
		data={}
		for name,value in dict(request.form).iteritems():
			data[name]=value[0]
		username=None
		if 'username' in data:
			username=data['username']
		client=MongoClient()
		db=client[app.config['DATABASE']]
		salt='leanreviewactivateusingtoken'
		activation_hash=hashlib.sha512(salt+data['email']).hexdigest()[10:30]
		
		exist_user=db.users.find({'email':data['email']})
		try:
			exist_user.next()
			return render_template('signup.html',signup_error='Email already exists',username=username,email=data['email'],
									google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login,active='signup')
		except StopIteration:
			pass

		_id=db.users.save({'name':username,
					   'email':data['email'],
					   'password':hashlib.sha512(SALT+data['password']).hexdigest(),
					   'activation_hash':activation_hash,
					   'reviews_submitted':0,
					   'reviews_created':0,
					   'kudos':0,
					   'access_token':'',
					   'fb_id':'',
					   'active':False})
		#user=User(name=username,email=data['email'],password=data['password'],active=False,id=str(_id))
		msg = Message('Welcome to Lean Reviews', sender = app.config['MAIL_SENDER'], recipients = [data['email']])
		
		
		msg.body = 'Click this link to activate your account '+app.config['HOST']+'/activate?hash='+activation_hash
		app.logger.debug('Sending activation email to:'+data['email'])
		#app.logger.debug(activation_hash)
		#app.logger.debug(str(app.extensions['mail'].server))
		try:
			mail.send(msg)
		except Exception:
			db.users.remove({'_id':_id})
			return render_template('signup.html',signup_error='Problem sending email. Account not created. Try again later.',
									google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login,username=username,email=data['email'],
									active='signup')
		return render_template('checkmail.html')


@app.route('/add_new')
def add_new():
	return render_template('add_new.html',title='Add New Item',active='add_new')

@app.route('/edit_review',methods=['GET','POST'])
def edit_review():
	#if current_user.email!='udayj.dev@gmail.com':
	#	return redirect(url_for('front'))
	if request.method=='GET':
		_id=request.args.get('id')
		if not _id:
			return redirect(url_for('error'))
		client=MongoClient()
		db=client[app.config['DATABASE']]
		review=db.reviews.find({'_id':ObjectId(_id)})
		review=review.next()
		app.logger.debug(review['words'])
		return render_template('edit_review.html',review=review,words=str(review['words']))
	else:
		data={}
		for name,value in dict(request.form).iteritems():
			data[name]=value[0].strip()
		client=MongoClient()
		db=client[app.config['DATABASE']]
		review=None
		try:
			review=db.reviews.find({'_id':ObjectId(data['id'])})
			review=review.next()	
		except Exception:
			js=json.dumps({'success':'false'})
			resp = Response(js, status=500, mimetype='application/json')
			return resp

		review['categories']=data['category']
		review['display_name']=data['display_name']
		for category in review['categories'].split(','):
			db_category=db.categories.find({'name':category})
			try:
				db_category=db_category.next()
				if review['_id'] not in db_category['review_ids']:
					db_category['review_ids'].append(review['_id'])
					db.categories.save(db_category)
			except StopIteration:
				db_category={'name':category.lower().strip(),'review_ids':[review['_id']]}
				db.categories.save(db_category)

		review['description']=data['description']
		if len(data['picture'])>5:
			review['picture']=data['picture']
		review['words']=ast.literal_eval(data['review'])
		db.reviews.save(review)
		return render_template('edit_review.html',review=review,words=str(review['words']),message="Successfully updated database")


def get_start_end(page,length):
	start=(page-1)*9
	if start>length-1:
		start=0
		page=1
	end=start+9
	if start+9>=length:
		end=length
	return start,end
	

def truncate_word(word,length):
	if len(word)>length:
		return word[:length-3]+'...'
	return word

@app.route('/categories')
def categories():
	client=MongoClient()
	db=client[app.config['DATABASE']]
	categories=db.categories.find()
	output=[]
	for category in categories:
		output.append(category['name'].title())
	output.sort()
	return render_template('categories.html',categories=output,title='Browse different reviews, share your reviews',active='categories')


@app.route('/browse/<category>')
def category(category):
	page=request.args.get('p')
	if not page:
		page=1
	else:
		try:
			page=int(page)
		except ValueError:
			page=1
	client=MongoClient()
	db=client[app.config['DATABASE']]
	collection=db.categories
	category=category.lower().strip()
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
	active=category
	
	display={'books':'Book Reviews','movies':'Movie Reviews','places':'Place Reviews','people':'People Reviews'}
	(start,end)=get_start_end(page,len(review_ids))
	output_review=[]
	for count in range(start,end):
		review=db.reviews.find({'_id':review_ids[count]})
		review=review.next()
		data=[]
		for word,value in review['words'].iteritems():
			data.append({'text':word,'size':value})
		description=truncate_word(review['description'],30)
		display_name=truncate_word(review['display_name'],30)
		output_review.append({'name':display_name,'description':description,'data':json.dumps(data),
							  'title_description':review['description'],'title_name':review['display_name'],
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
	meta_description='The most accurate reviews on '+category+'. Explore thousands of other reviews easily and even write some quick reviews.'

	return render_template('category.html',display_message=category.title(),reviews=output_review,
							length=len(output_review),pagination=pagination,url=request.path,active=active,title=category.title(),
							meta_description=meta_description)

def get_recent_submitters(length):
	client=MongoClient()
	db=client[app.config['DATABASE']]
	cursor=db.users.find({'type':'fake'})
	users=[]
	for user in cursor:
		users.append(user)
	random.shuffle(users)
	output=[]
	for user in users[:length]:
		output.append((user['_id'],user['name']))
	return output



def get_recommendations(categories,present_review_id):
	client=MongoClient()
	db=client[app.config['DATABASE']]
	review_ids=[]
	for category in categories.split(','):
		new_category=db.categories.find({'name':category})
		new_category=new_category.next()
		
		for review_id in new_category['review_ids']:
			review_ids.append(review_id)
	random.shuffle(review_ids)
	review_ids.remove(present_review_id)
	output=[]
	for review_id in review_ids[:5]:
		review=db.reviews.find({'_id':review_id})
		review=review.next()
		output.append([review_id,review['name'],review['display_name']])
	return output

def remove_stop_words(query):

	words=['reviews','review','reveiw']
	for word in words:
		query=query.replace(word,' ')
	return query

@app.route('/item')
def item():
	client=MongoClient()
	db=client[app.config['DATABASE']]
	collection=db.reviews
	_id=request.args.get('id')
	review=None
	cursor=None
	if _id:
		try:
			review=collection.find({'_id':ObjectId(_id)})
		except Exception:
			return render_template('error.html')
		cursor=review
		try:
			
			review=review.next()
			
		except StopIteration:
			name=request.args.get('name')
			if not name:
				return render_template('error.html')
			name=remove_stop_words(name).lower().strip()
			review=collection.find({'name':name})
			cursor=review
			try:
				review=review.next()
				
			except StopIteration:
				return render_template('add_new.html',message='We cant find what you are looking for. But you can add a new review real quick.',
										name=name)
	else:
		name=request.args.get('name')
		if not name:
			return render_template('error.html')
		name=remove_stop_words(name).lower().strip()
		review=collection.find({'name':name})
		cursor=review
		try:
			review=review.next()
		except StopIteration:
			return render_template('add_new.html',message='We cant find what you are looking for. But you can add a new review real quick.',
										name=name)
	total_reviews=[review]
	for review in cursor:
		total_reviews.append(review)
	if len(total_reviews)==1:
		data=[]
		output_review={}
		number_reviews=0
		for word,value in review['words'].iteritems():
			data.append({'text':word,'size':value})
			number_reviews+=value

		output_review['id']=review['_id']
		output_review['name']=review['display_name']
		output_review['data']=json.dumps(data)
		output_review['upvote']=review['upvote']
		output_review['downvote']=review['downvote']
		if len(review['description'])>5:
			output_review['description']=review['description']
		if 'picture' in review:
			output_review['picture']=review['picture']
		recent_submitters=None
		if 'recent_submitters' not in review:
			recent_submitters=get_recent_submitters(3)
		else:
			length=len(review['recent_submitters'])
			recent_submitters=get_recent_submitters(3-length)
			recent_submitters.extend(review['recent_submitters'])
		recommendations=get_recommendations(review['categories'],review['_id'])
		meta_description='Get to know what the crowd thinks about '+ review['display_name']+' and write quick, honest reviews.'
		return render_template('item.html',review=output_review,recommendations=recommendations,number_reviews=number_reviews,
								votes=review['upvote']+review['downvote'],recent_submitters=recent_submitters,
								title=review['display_name']+ ' Reviews', meta_description=meta_description)
	else:
		page=request.args.get('p')
		
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
			description=truncate_word(review['description'],30)
			display_name=truncate_word(review['display_name'],30)
			output_review.append({'name':display_name,'data':json.dumps(data),'description':description,
								  'title_name':review['display_name'],
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
	db=client[app.config['DATABASE']]
	collection=db.categories
	categories=['books','movies','places','people']
	review_ids_mixed=[]
	for category in categories:
		present_category=collection.find({'name':category})
		present_category=present_category.next()
		review_ids=present_category['review_ids']
		review_ids_mixed=review_ids_mixed+review_ids
	random.shuffle(review_ids_mixed)
	output_review=[]
	for count in range(0,count):
		review=db.reviews.find({'_id':review_ids_mixed[count]})
		review=review.next()
		data=[]
		for word,value in review['words'].iteritems():
			data.append({'text':word,'size':value})
		description=truncate_word(review['description'],30)
		display_name=truncate_word(review['display_name'],30)
		output_review.append({'name':display_name,'data':json.dumps(data),
							  'description':description,'title_name':review['display_name'],
							  'url':'/item?name='+review['name']+'&id='+str(review['_id'])})
	return output_review

@app.route('/share_facebook',methods=['POST'])
def share_facebook():
	data={}
	for name,value in dict(request.form).iteritems():
		data[name]=value[0]
	image=data['image']
	image=base64.decodestring(image)
	facebook_login='https://graph.facebook.com/oauth/authorize?scope=email,publish_actions&client_id=423477151081458&redirect_uri='+app.config['HOST']+'/facebook_oauth_callback'
	f=open('static/data/'+data['id']+'.png','w')
	f.write(image)
	f.close()
	access_token=None
	client=MongoClient()
	db=client[app.config['DATABASE']]
	review=db.reviews.find({'_id':ObjectId(data['id'])})
	review=review.next()
	try:
		access_token=current_user.access_token
	except AttributeError:
		js=json.dumps({'facebook_login':facebook_login})
		resp = Response(js, status=200, mimetype='application/json')
		return resp	
	
	values={'message':'A much better (and easier) way to read and write reviews',
			'access_token':access_token,
			'picture':'http://www.leanreviews.com/static/data/'+data['id']+'.png',
			'link':'http://www.leanreviews.com/item?name='+review['name']+'&id='+str(review['_id']),
			'name':review['display_name'],
			'caption':'Read what the crowd thinks about '+review['display_name'],
			'description':'The easiest way yet to read and write opinions about '+review['display_name']+' on the web'}

	app.logger.debug(values)		
	url='https://graph.facebook.com/'+current_user.fb_id+'/feed?method=post'
	app.logger.debug(url)
	data = urllib.urlencode(values)
	app.logger.debug(data)
	req = urllib2.Request(url, data)
	app.logger.debug(req.headers)
	try:
		response = urllib2.urlopen(req)
	except:
		app.logger.debug('User logged in but not using Facebook')
		js=json.dumps({'facebook_login':facebook_login})
		resp = Response(js, status=200, mimetype='application/json')
		return resp	
		
	app.logger.debug(response.read())
	js=json.dumps({'success':'success'})
	resp = Response(js, status=200, mimetype='application/json')
	return resp
	


@app.route('/trending')
def trending():
	output_review=get_trending_data(9)
	return render_template('trending.html',reviews=output_review,length=9,active='trending',title='Trending Reviews')

@app.route('/rate_item',methods=['POST'])
def rate_item():
	
	data={}
	for name,value in dict(request.form).iteritems():
		data[name]=value[0].lower().strip()
	
	#if not current_user or not current_user.is_authenticated():
	#	return redirect(login_url('signup',next_url=url_for('item',id=data['id'])))
	
	
	client=MongoClient()
	db=client[app.config['DATABASE']]
	app.logger.debug(data)
	review=None
	try:
		review=db.reviews.find({'_id':ObjectId(data['id'])})
	except Exception:
		js=json.dumps({'success':'false'})
		resp = Response(js, status=500, mimetype='application/json')
		return resp		
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
	js=None
	try:
		user=db.users.find({'_id':ObjectId(current_user.id)})
		user=user.next()
		user['kudos']=user['kudos']+1
		db.users.save(user)
		js=json.dumps({'success':'success'})
	except AttributeError:
		js=json.dumps({'partial_success':'success'})

	

	resp = Response(js, status=200, mimetype='application/json')
	return resp

@app.route('/review_item',methods=['POST'])
def review_item():
	
	
	data={}
	for name,value in dict(request.form).iteritems():
		data[name]=value[0].lower().strip()
	client=MongoClient()
	db=client[app.config['DATABASE']]
	review=None
	try:
		review=db.reviews.find({'_id':ObjectId(data['id'])})
	except Exception:
		js=json.dumps({'success':'false'})
		resp = Response(js, status=500, mimetype='application/json')
		return resp	
	review=review.next()
	if data['review'] in review['words']:
		review['words'][data['review']]=review['words'][data['review']]+1
	else:
		review['words'][data['review']]=1
	db.reviews.save(review)
	js=None
	try:
		user=db.users.find({'_id':ObjectId(current_user.id)})
		user=user.next()
		user['kudos']=user['kudos']+1
		user['reviews_submitted']=user['reviews_submitted']+1
		db.users.save(user)
		js=json.dumps({'success':'success'})
	except AttributeError:
		js=json.dumps({'partial_success':'success'})
	

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
	client=MongoClient()
	db=client[app.config['DATABASE']]
	_id=db.reviews.save({'name':data['name'].lower().strip(),
					 'display_name':data['name'],
					 'description':data['description'] if 'description' in data else '',
					 'categories':data['category'] if 'category' in data else None,
					 'words':{data['review']:1},
					 'upvote':0,
					 'downvote':0,
					 'creation_time':datetime.datetime.utcnow()})
	

	if 'category' in data and data['category'] != '':

		categories=data['category']
		for new_category in categories.split(','):
			category=db.categories.find({'name':new_category})
			try:
				category=category.next()
				category['review_ids'].append(_id)
				db.categories.save(category)
			except StopIteration:
				category={'name':new_category,'review_ids':[_id]}
				db.categories.save(category)
	try:
		user=db.users.find({'_id':ObjectId(current_user.id)})
		user=user.next()
		user['kudos']=user['kudos']+1
		user['reviews_created']=user['reviews_created']+1
		db.users.save(user)
	except:
		pass

	
	return redirect(url_for('item',id=str(_id),name=data['name'].lower().strip()))

@app.route('/options')
def options():
	q=request.args.get('term')
	q=q.lower().strip()
	client=MongoClient()
	db=client[app.config['DATABASE']]
	pattern=re.compile('.*'+q+'.*')
	reviews=db.reviews.find({"name":pattern})
	output=[]
	try:
		for review in reviews:
			output.append({'value':review['display_name']})
	except StopIteration:
		pass
	js=json.dumps(output)
	resp = Response(js, status=200, mimetype='application/json')
	return resp

if app.debug is None or app.debug is False or app.debug is True:   
	    import logging
	    from logging.handlers import RotatingFileHandler
	    file_handler = RotatingFileHandler('/home/uday/code/one_word_virtual/logs/application.log', maxBytes=1024 * 1024 * 100, backupCount=20)
	    file_handler.setLevel(logging.DEBUG)
	    formatter = logging.Formatter("%(asctime)s - %(funcName)s - %(levelname)s - %(message)s")
	    file_handler.setFormatter(formatter)
	    app.logger.addHandler(file_handler)
	    app.logger.error(str(app.config))

if __name__=='__main__':
	app.run()
	