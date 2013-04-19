from pymongo import MongoClient
from random import randint
import datetime
import codecs

words="nice-place,awesome,serene,busy,hectic,cosmopolitan,peaceful,hot,humid,very-dry,helpful-people,cheap,very-rich,nice-food,good-hotels,awesome-scenary,great-view,great-cars,cold,must-visit,avoid,waste-of-time,soothing,great-climate,overhyped,expensive"
def seed_data():
	client=MongoClient()
	db=client.leanreviews
	collection=db.reviews
	review={}
	word=words.split(',')
	review['name']='hindi movie'
	review['display_name']='Hindi Movie'
	review['upvote']=100
	review['downvote']=40
	review['categories']='Movies'
	review['created_by']='admin'
	review['creation_time']=datetime.datetime.utcnow()
	review['words']={}
	for text in word:
		review['words'][text]=randint(10,100)
	collection.save(review)
	print review
def normalize(item):
	return item.lower().strip()
def seed_data_from_file():
	tag_file=codecs.open('data/seed.txt','r','utf-8')
	types=['books','movies','places','people']
	counter=0
	client=MongoClient()
	db=client.leanreviews
	collection=db.reviews
	message={'books':'','movies':'',
			 'places':'','people':''}
	probability={'good':0.8,'bad':0.2}
	while True:
		tags_good=tag_file.readline()
		if not tags_good:
			break
		tags_bad=tag_file.readline()
		tags_good=tags_good.split(',')
		tags_bad=tags_bad.split(',')
		review_type=types[counter]
		names=codecs.open('data/'+review_type+'.txt','r','utf-8')
		while True:
			item=names.readline()
			item=item.strip()
			if not item:
				break
			review={}
			review['name']=normalize(item)
			review['display_name']=item.title()
			review['description']=message[review_type]
			review['upvote']=100
			review['downvote']=40
			review['categories']=review_type
			review['created_by']='admin'
			review['creation_time']=datetime.datetime.utcnow()
			review['words']={}
			for word in tags_good:
				review['words'][word]=int(randint(10,180)*probability['good'])
			for word in tags_bad:
				review['words'][word]=int(randint(10,400)*probability['bad'])
			collection.save(review)
		names.close()
		counter+=1
	tag_file.close()
def seed_categories():
	client=MongoClient()
	db=client.leanreviews
	collection=db.reviews
	categories=db.categories
	types=['books','movies','places','people']
	for category in types:
		new_category={}
		new_category['name']=category
		new_category['review_ids']=[]
		categories.save(new_category)
	print categories.count()
	for review in collection.find():
		category=review['categories']
		categories.update({'name':category},{'$push':{'review_ids':review['_id']}})
def seed_content():
	files=['american_actors.txt','books_new.txt','movies_new.txt','places_new.txt']
	types=['people','books','movies','places']
	
	client=MongoClient()
	db=client.leanreviews
	collection=db.reviews
	counter=0
	for genre in files:
		new_content=codecs.open('data/'+genre,'r','utf-8')
		while True:
			content=new_content.readline()
			if not content:
				break
			content=content.split('\t')
			name=content[0]
			
			review={}
			review['name']=normalize(name)
			review['display_name']=name
			review['description']=''
			review['upvote']=randint(10,300)
			review['downvote']=randint(10,35)
			review['categories']=types[counter]
			review['created_by']='admin'
			review['creation_time']=datetime.datetime.utcnow()
			review['words']={}
			for word in content[1:]:
				review['words'][word.strip().replace('.','')]=randint(10,150)
			collection.save(review)
		counter+=1
		new_content.close()

def seed_fake_users():
	f=codecs.open('data/american_names.txt','r','utf-8')
	client=MongoClient()
	db=client.leanreviews
	while True:
		name=f.readline()
		if not name:
			break
		name=name.strip()
		user={}
		user['name']=name
		user['password']=''
		user['active']=False
		user['email']='fake@leanreviews.com'
		user['reviews_created']=randint(0,7)
		user['reviews_submitted']=randint(1,30)
		user['kudos']=user['reviews_created']+user['reviews_submitted']
		user['fb_id']=''
		user['access_token']=''
		user['type']='fake'
		db.users.save(user)
	f.close()

def seed_javascript():
	files=['american_actors.txt','books_new.txt','movies_new.txt','places_new.txt']
	types=['people','books','movies','places']
	javascript_file=codecs.open('data/javascript_file','w','utf-8')
	counter=0
	file_content=''
	for genre in files:
		new_content=codecs.open('data/'+genre,'r','utf-8')
		while True:
			content=new_content.readline()
			if not content:
				break
			content=content.split('\t')
			name=content[0]
			file_content=file_content+'\n'+name
			
			
		counter+=1
		new_content.close()
	javascript_file.write(file_content)
	javascript_file.close()