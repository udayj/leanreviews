import application
import unittest
from pymongo import MongoClient
from bson.objectid import ObjectId
import hashlib

class LeanReviewsTest(unittest.TestCase):

	def setUp(self):
		application.app.config['TESTING']=True
		application.app.config['DATABASE']='test_leanreviews'
		self.app=application.app.test_client()

	@unittest.skip('verified')
	def test_signup_without_conflict(self):
		rv=self.app.post('/signup',data=dict(
						username='udayj',
						email='udayj.dev@gmail.com',
						password='password'),follow_redirects=True)
		client=MongoClient()
		db=client.test_leanreviews
		user=db.users.find({'name':'udayj'})
		user=user.next()
		assert user['email']=='udayj.dev@gmail.com'
		assert user['active']==False
		assert user['password']==hashlib.sha512(application.SALT+'password').hexdigest()
		assert 'activate your account' in rv.data

	@unittest.skip('verified')
	def test_signup_with_conflicting_username(self):
		rv=self.app.post('/signup',data=dict(
						username='udayj',
						email='udayj.dev@gmail.com',
						password='password'),follow_redirects=True)
		assert 'Username already exists' in rv.data

	@unittest.skip('verified')
	def test_signup_with_conflicting_email(self):
		rv=self.app.post('/signup',data=dict(
						email='udayj.dev@gmail.com',
						password='password'),follow_redirects=True)
		assert 'Email already exists' in rv.data

	@unittest.skip('verified')
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

	@unittest.skip('verified')
	def test_vote_from_logged_in_user(self):
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3@gmail.com',
						password='password'),follow_redirects=True)
		rv=self.app.post('/rate_item',data=dict(
						id='515d48e70acdc7135c2a910c',
						vote='up_vote'
						),follow_redirects=True)
		client=MongoClient()
		db=client.test_leanreviews
		review=db.reviews.find({'_id':ObjectId('515d48e70acdc7135c2a910c')})
		review=review.next()
		assert review['upvote']==105
		print rv.data
		assert '"success": "success"' in rv.data	

	@unittest.skip('verified')
	def test_review_from_logged_in_user_new_word(self):
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3@gmail.com',
						password='password'),follow_redirects=True)
		rv=self.app.post('/review_item',data=dict(
						id='515d48e70acdc7135c2a910c',
						review='good'
						),follow_redirects=True)
		client=MongoClient()
		db=client.test_leanreviews
		review=db.reviews.find({'_id':ObjectId('515d48e70acdc7135c2a910c')})
		review=review.next()
		assert 'good' in review['words']
		assert review['words']['good']==1
		assert '"success": "success"' in rv.data		

	@unittest.skip('verified')
	def test_review_from_logged_in_user(self):
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3@gmail.com',
						password='password'),follow_redirects=True)
		rv=self.app.post('/review_item',data=dict(
						id='515d48e70acdc7135c2a910c',
						review='good'
						),follow_redirects=True)
		client=MongoClient()
		db=client.test_leanreviews
		review=db.reviews.find({'_id':ObjectId('515d48e70acdc7135c2a910c')})
		review=review.next()
		assert 'good' in review['words']
		assert review['words']['good']==8
		assert '"success": "success"' in rv.data

	@unittest.skip('verified')
	def test_new_submission_from_logged_in_user(self):
		rv=self.app.post('/login',data=dict(
						username='udayj.dev3@gmail.com',
						password='password'),follow_redirects=True)
		rv=self.app.post('/process_new_item',data=dict(
						name='Lord of the Rings',
						description='This refers to a movie',
						review='good'
						),follow_redirects=True)
		client=MongoClient()
		db=client.test_leanreviews
		review=db.reviews.find({'name':'lord of the rings'})
		review=review.next()
		assert 'good' in review['words']
		assert review['words']['good']==40
		assert review['description']=='This refers to a movie'
		assert review['display_name']=='Lord of the Rings'
		assert review['categories']==None
		assert 'Still confused about what this' in rv.data


	def test_new_submission_from_logged_in_user_with_category(self):
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









if __name__ == '__main__':
	unittest.main()
