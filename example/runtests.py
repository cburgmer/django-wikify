#This file mainly exists to allow python setup.py test to work.
import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'example.example.settings'
test_dir = os.path.dirname(__file__)
print test_dir
sys.path.insert(0, test_dir)

from django.test.utils import get_runner
from django.conf import settings

def runtests():
    TestRunner = get_runner(settings)
    runner = TestRunner(verbosity=1, interactive=True)
    failures = runner.run_tests([])
    sys.exit(failures)

if __name__ == '__main__':
    runtests()
