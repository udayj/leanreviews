from fabric.api import *

env.hosts=['166.78.236.68']
env.activate='source /home/uday/code/one_word_virtual/bin/activate'
def check():
	local('echo "check" > check.txt')

def deploy():
	with cd('code'):
		run('pwd')
		with cd('one_word_virtual'):
			run('export CONFIG_FILE=production.conf')
			sudo('kill nginx')
			sudo('kill process')
			run('rm -rf one_word_application')
			put('one_word_application','/home/uday/code/one_word_virtual')
			run('source /home/uday/code/one_word_virtual/bin/activate')
			sudo('bin/supervisord -c ./one_word_application/supervisord.conf')
			sudo('/usr/sbin/nginx')
			
