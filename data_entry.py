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
	message={'books':'This refers to a book','movies':'This refers to a movie',
			 'places':'This refers to a place','people':'This refers to a person'}
	while True:
		tags=tag_file.readline()
		if not tags:
			break
		tags=tags.split(',')
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
			for word in tags:
				review['words'][word]=randint(10,100)
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
