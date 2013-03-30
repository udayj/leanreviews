from flask import Flask, request, render_template
from pymongo import MongoClient
import json
import random

app = Flask(__name__)
app.config.from_object(__name__)

@app.route('/')
def front():
	return render_template('front.html')

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


if __name__=='__main__':
	app.run(debug=True)