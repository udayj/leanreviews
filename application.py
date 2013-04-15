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
	app.logger.debug('check')
	output_review=get_trending_data(3)
	return render_template('front.html',reviews=output_review,active='front')

@app.route('/about')
def about():
	
	return render_template('about.html')

@login_manager.user_loader
def load_user(_id):
	client=MongoClient()
	db=client[app.config['DATABASE']]
	user=db.users.find({'_id':ObjectId(_id)})
	try:
		user=user.next()
		ret_user=User(name=user['name'],email=user['email'],password="",active=user['active'],_id=str(user['_id']))
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
			ret_user=User(name=content['name'],email=content['email'],password="",active=True,_id=str(_id))
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
	facebook_login='https://graph.facebook.com/oauth/authorize?scope=email&client_id=423477151081458&redirect_uri='+app.config['HOST']+'/facebook_oauth_callback'
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
		response = cgi.parse_qs(urllib.urlopen("https://graph.facebook.com/oauth/access_token?" +urllib.urlencode(args)).read()+"&scope=email")
	except Exception as e:
		app.logger.debug(str(e))
		#app.logger.debug(response)
		return render_template('/signup.html',error='Cannot login. Some problem on our server. Check back in a few minutes.',
								google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login)
	access_token = response["access_token"][-1]
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
		ret_user=User(name=content['name'],email=content['email'],password="",active=True,_id=str(_id))
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
	facebook_login='https://graph.facebook.com/oauth/authorize?scope=email&client_id=423477151081458&redirect_uri='+app.config['HOST']+'/facebook_oauth_callback'


	if request.method=='GET':
		return render_template('/signup.html',google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login,active='login')
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
		ret_user=User(name=user['name'],email=user['email'],password="",active=user['active'],_id=str(user['_id']))
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
			ret_user=User(name=user['name'],email=user['email'],password="",active=user['active'],_id=str(user['_id']))
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
	kudos=user['kudos']
	reviews_submitted=user['reviews_submitted']
	reviews_created=user['reviews_created']
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
		ret_user=User(name=user['name'],email=user['email'],password="",active=user['active'],_id=str(user['_id']))
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
	facebook_login='https://graph.facebook.com/oauth/authorize?scope=email&client_id=423477151081458&redirect_uri='+app.config['HOST']+'/facebook_oauth_callback'


	if request.method=='GET':
		return render_template('/signup.html',google_login=flow.step1_get_authorize_url(),facebook_login=facebook_login,active='signup')
	else:
		
		data={}
		for name,value in dict(request.form).iteritems():
			data[name]=value[0].lower().strip()
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
@login_required
def add_new():
	return render_template('add_new.html')

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
			data[name]=value[0].lower().strip()
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
		display_name=truncate_word(review['display_name'],24)
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

	return render_template('category.html',display_message=display[category],reviews=output_review,length=len(output_review),pagination=pagination,url=request.path,active=active)

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
			name=name.lower().strip()
			review=collection.find({'name':name})
			cursor=review
			try:
				review=review.next()
				
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
		output_review['description']=review['description']
		return render_template('item.html',review=output_review)
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
			display_name=truncate_word(review['display_name'],24)
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
		display_name=truncate_word(review['display_name'],24)
		output_review.append({'name':display_name,'data':json.dumps(data),
							  'description':description,'title_name':review['display_name'],
							  'url':'/item?name='+review['name']+'&id='+str(review['_id'])})
	return output_review

@app.route('/trending')
def trending():
	output_review=get_trending_data(9)
	return render_template('trending.html',reviews=output_review,length=9,active='trending')

@app.route('/rate_item',methods=['POST'])
@login_required
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
	user=db.users.find({'_id':ObjectId(current_user.id)})
	user=user.next()
	user['kudos']=user['kudos']+1
	db.users.save(user)

	js=json.dumps({'success':'success'})

	resp = Response(js, status=200, mimetype='application/json')
	return resp

@app.route('/review_item',methods=['POST'])
@login_required
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
	user=db.users.find({'_id':ObjectId(current_user.id)})
	user=user.next()
	user['kudos']=user['kudos']+1
	user['reviews_submitted']=user['reviews_submitted']+1
	db.users.save(user)
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
	client=MongoClient()
	db=client[app.config['DATABASE']]
	_id=db.reviews.save({'name':data['name'].lower().strip(),
					 'display_name':data['name'],
					 'description':data['description'] if 'description' in data else '',
					 'categories':data['category'] if 'category' in data else None,
					 'words':{data['review']:40},
					 'upvote':0,
					 'downvote':0})
	
	if 'category' in data and data['category'] != '':
		category=db.categories.find({'name':data['category']})
		try:
			category=category.next()
			category['review_ids'].append(_id)
			db.categories.save(category)
		except StopIteration:
			category={'name':data['category'],'review_ids':[_id]}
			db.categories.save(category)

	user=db.users.find({'_id':ObjectId(current_user.id)})
	user=user.next()
	user['kudos']=user['kudos']+1
	user['reviews_created']=user['reviews_created']+1
	db.users.save(user)

	
	return redirect(url_for('item',id=str(_id),name=data['name'].lower().strip()))

if app.debug is True or app.debug is None or app.debug is False:   
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
	