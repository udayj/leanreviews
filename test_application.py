import application
import unittest
from pymongo import MongoClient
from bson.objectid import ObjectId
import hashlib
import json

class LeanReviewsTest(unittest.TestCase):

	def setUp(self):
		application.app.config['TESTING']=True
		application.app.config['DATABASE']='test_leanreviews'
		self.app=application.app.test_client()

	
	def test_signup_without_conflict(self):
		client=MongoClient()
		db=client.test_leanreviews
		db.users.remove({'name':'udayj'})

		rv=self.app.post('/signup',data=dict(
						username='udayj',
						email='udayj.dev@gmail.com',
						password='password'),follow_redirects=True)
		
		user=db.users.find({'name':'udayj'})
		user=user.next()
		assert user['email']=='udayj.dev@gmail.com'
		assert user['active']==False
		assert user['password']==hashlib.sha512(application.SALT+'password').hexdigest()
		assert 'activate your account' in rv.data

	
	def test_signup_with_conflicting_username(self):
		client=MongoClient()
		db=client.test_leanreviews
		user=db.users.find({'name':'udayj'})
		try:
			user=user.next()
		except StopIteration:
			db.users.save({'name':'udayj','email':'udayj.dev@gmail.com'})

		rv=self.app.post('/signup',data=dict(
						username='udayj',
						email='udayj.dev@gmail.com',
						password='password'),follow_redirects=True)
		assert 'Username already exists' in rv.data

	
	def test_signup_with_conflicting_email(self):
		client=MongoClient()
		db=client.test_leanreviews
		user=db.users.find({'email':'udayj.dev@gmail.com'})
		try:
			user=user.next()
		except StopIteration:
			db.users.save({'name':'udayj','email':'udayj.dev@gmail.com'})
		rv=self.app.post('/signup',data=dict(
						email='udayj.dev@gmail.com',
						password='password'),follow_redirects=True)
		assert 'Email already exists' in rv.data

	
	def test_signup_with_incorrect_email(self):
		rv=self.app.post('/signup',data=dict(
						email='udayj.dev3gmail.com',
						password='password'),follow_redirects=True)
		assert 'Problem sending email' in rv.data

	def test_login_with_incorrect_username(self):
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3gmail.com',
						password='password'),follow_redirects=True)
		assert 'Wrong credentials' in rv.data

	def test_login_with_incorrect_password(self):
		rv=self.app.post('/login',data=dict(
						username='udayj.dev@gmail.com',
						password='password12345'),follow_redirects=True)
		assert 'Wrong credentials' in rv.data

	def test_login_with_inactive_acccount(self):
		rv=self.app.post('/login',data=dict(
						username='udayj.dev@gmail.com',
						password='password'),follow_redirects=True)
		assert 'Account still inactive' in rv.data

	def test_login_with_correct_credentials(self):
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3@gmail.com',
						password='password'),follow_redirects=True)
		assert 'makes it easy to write more reviews' in rv.data

	def test_vote_from_logged_out_user(self):
		rv=self.app.post('/rate_item',data=dict(
						id='udayj.dev3@gmail.com',
						vote='up_vote'
						),follow_redirects=True)
		assert 'Login below' in rv.data		

	def test_review_from_logged_out_user(self):
		rv=self.app.post('/review_item',data=dict(
						id='udayj.dev3@gmail.com',
						review='good'
						),follow_redirects=True)
		assert 'Login below' in rv.data

	
	def test_vote_from_logged_in_user(self):
		client=MongoClient()
		db=client.test_leanreviews
		review=db.reviews.find({'_id':ObjectId('515d48e70acdc7135c2a90f2')})
		review=review.next()
		review['upvote']=104
		db.reviews.save(review)
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3@gmail.com',
						password='password'),follow_redirects=True)
		rv=self.app.post('/rate_item',data=dict(
						id='515d48e70acdc7135c2a90f2',
						vote='up_vote'
						),follow_redirects=True)
		review=db.reviews.find({'_id':ObjectId('515d48e70acdc7135c2a90f2')})
		review=review.next()
		assert review['upvote']==105
		print rv.data
		assert '"success": "success"' in rv.data	

	
	def test_review_from_logged_in_user_new_word(self):
		client=MongoClient()
		db=client.test_leanreviews
		review=db.reviews.find({'_id':ObjectId('515d48e70acdc7135c2a90f2')})
		review=review.next()
		review['words']['good']=0
		db.reviews.save(review)
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3@gmail.com',
						password='password'),follow_redirects=True)
		rv=self.app.post('/review_item',data=dict(
						id='515d48e70acdc7135c2a90f2',
						review='good'
						),follow_redirects=True)
		
		review=db.reviews.find({'_id':ObjectId('515d48e70acdc7135c2a90f2')})
		review=review.next()
		assert 'good' in review['words']
		assert review['words']['good']==1
		assert '"success": "success"' in rv.data		

	
	def test_review_from_logged_in_user(self):
		client=MongoClient()
		db=client.test_leanreviews
		review=db.reviews.find({'_id':ObjectId('515d48e70acdc7135c2a90f2')})
		review=review.next()
		review['words']['good']=4
		db.reviews.save(review)
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3@gmail.com',
						password='password'),follow_redirects=True)
		rv=self.app.post('/review_item',data=dict(
						id='515d48e70acdc7135c2a90f2',
						review='good'
						),follow_redirects=True)
		
		review=db.reviews.find({'_id':ObjectId('515d48e70acdc7135c2a90f2')})
		review=review.next()
		assert 'good' in review['words']
		assert review['words']['good']==5
		assert '"success": "success"' in rv.data

	
	def test_new_submission_from_logged_in_user(self):
		client=MongoClient()
		db=client.test_leanreviews
		review=db.reviews.remove({'name':'lord of the rings'})
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3@gmail.com',
						password='password'),follow_redirects=True)
		rv=self.app.post('/process_new_item',data=dict(
						name='Lord of the Rings',
						description='This refers to a movie',
						review='good'
						),follow_redirects=True)
		
		review=db.reviews.find({'name':'lord of the rings'})
		review=review.next()
		assert 'good' in review['words']
		assert review['words']['good']==40
		assert review['description']=='This refers to a movie'
		assert review['display_name']=='Lord of the Rings'
		assert review['categories']==None
		assert 'Still confused about what this' in rv.data

	
	def test_new_submission_from_logged_in_user_with_category(self):
		client=MongoClient()
		db=client.test_leanreviews
		review=db.reviews.remove({'name':'lord of the rings'})
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3@gmail.com',
						password='password'),follow_redirects=True)
		rv=self.app.post('/process_new_item',data=dict(
						name='Lord of the Rings',
						category='movies',
						review='good'
						),follow_redirects=True)
		client=MongoClient()
		db=client.test_leanreviews
		review=db.reviews.find({'name':'lord of the rings'})
		review=review.next()
		assert 'good' in review['words']
		assert review['words']['good']==40
		assert review['description']==''
		assert review['display_name']=='Lord of the Rings'
		assert review['categories']=='movies'
		category=db.categories.find({'name':'movies'})
		category=category.next()
		assert review['_id'] in category['review_ids']
		assert 'Still confused about what this' in rv.data

	def test_category_page(self):
		rv=self.app.get('/browse/places')
		assert '<li id="places" class="active">' in rv.data
		assert 'Place Reviews' in rv.data

		client=MongoClient()
		db=client.test_leanreviews
		category=db.categories.find({'name':'places'})
		category=category.next()
		review_ids=category['review_ids'][0:9]
		for review_id in review_ids:
			assert str(review_id) in rv.data

	def test_item_page_with_correct_id(self):
		rv=self.app.get('/item?id=515d48e70acdc7135c2a90f2')
		assert 'Try searching for something else' not in rv.data
		assert 'confused about what this refers' in rv.data

	def test_item_page_with_incorrect_id(self):
		rv=self.app.get('/item?id=1234567')
		assert 'Try searching for something else' in rv.data
		assert 'confused about what this refers' not in rv.data	

	def test_item_page_with_multiple_entries(self):
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3@gmail.com',
						password='password'),follow_redirects=True)
		rv=self.app.post('/process_new_item',data=dict(
						name='Lord of the Rings',
						category='movies',
						review='good'
						),follow_redirects=True)
		rv=self.app.post('/process_new_item',data=dict(
						name='Lord of the Rings',
						category='movies',
						review='good'
						),follow_redirects=True)
		rv=self.app.get('/item?name=lord%20of%20the%20rings')
		print rv.data
		assert 'Multiple Reviews Retrieved' in rv.data


		
		
	









if __name__ == '__main__':
	unittest.main()
