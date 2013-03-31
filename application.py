from flask import Flask, request, render_template, Response, redirect, url_for
from pymongo import MongoClient
import json
import random

app = Flask(__name__)
app.config.from_object(__name__)

@app.route('/')
def front():
	return render_template('front.html')
@app.route('/add_new')
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
	present_category=present_category.next()
	review_ids=present_category['review_ids']
	
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
		output_review.append({'name':review['display_name'],'data':json.dumps(data)})
	left=None
	left_ellipses=None
	prev=None
	next=None
	right_ellipses=None
	right=None
	if page>1:
		prev=page-1
		left=page-1
	if page>3:
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

	return render_template('category.html',reviews=output_review,length=len(output_review),pagination=pagination,url=request.path)

@app.route('/item')
def item():
	name=request.args.get('name')
	if not name:
		return render_template('error.html')

	client=MongoClient()
	db=client.leanreviews
	collection=db.reviews
	review=collection.find({'name':name})
	try:
		review=review.next()
	except StopIteration:
		return render_template('error.html')		
	data=[]
	output_review={}
	for word,value in review['words'].iteritems():
		data.append({'text':word,'size':value})
	output_review['name']=review['display_name']
	output_review['data']=json.dumps(data)
	output_review['upvote']=review['upvote']
	output_review['downvote']=review['downvote']
	app.logger.debug(output_review)
	return render_template('item.html',review=output_review)

@app.route('/trending')
def trending():
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
	for count in range(0,9):
		review=db.reviews.find({'_id':review_ids_mixed[count]})
		app.logger.debug(str(review_ids_mixed[count]))
		review=review.next()
		data=[]
		for word,value in review['words'].iteritems():
			data.append({'text':word,'size':value})
		output_review.append({'name':review['display_name'],'data':json.dumps(data)})
	return render_template('trending.html',reviews=output_review,length=9)

@app.route('/rate_item',methods=['POST'])
def rate_item():
	
	app.logger.debug(str(request.form))
	data={}
	for name,value in dict(request.form).iteritems():
		data[name]=value[0].lower().strip()
	client=MongoClient()
	db=client.leanreviews
	review=db.reviews.find({'name':data['name']})
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
def review_item():
	
	app.logger.debug(str(request.form))
	data={}
	for name,value in dict(request.form).iteritems():
		data[name]=value[0].lower().strip()
	client=MongoClient()
	db=client.leanreviews
	review=db.reviews.find({'name':data['name']})
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
	db.reviews.save({'name':data['name'].lower().strip(),
					 'display_name':data['name'],
					 'description':data['description'],
					 'categories':data['category'],
					 'words':{data['review']:40},
					 'upvote':0,
					 'downvote':0})
	#update appropriate category or create new category
	return redirect(url_for('item',name=data['name'].lower().strip()))


if __name__=='__main__':
	app.run(debug=True)