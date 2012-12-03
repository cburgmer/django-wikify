import ez_setup
ez_setup.use_setuptools()
from setuptools import setup

setup(name="django-wikify",
      #version="0.1",
      description="Wikify is a lightweight module to turn your static Django model views into full wiki pages.",
      long_description=open('README.rst').read(),
      author="Christoph Burgmer",
      author_email="cburgmer@ira.uka.de",
      url="http://github.com/cburgmer/django-wikify",
      packages=["wikify"],
      package_dir={"": "src"},
      package_data = {"wikify": ["static/wikify/*.css", "templates/wikify/*.html"]},
      dependency_links = [
          "http://google-diff-match-patch.googlecode.com/svn/trunk/python2/diff_match_patch.py#egg=diff_match_patch-py2_svn"
      ],
      install_requires = ['django_reversion>=1.6', 'Django', 'diff_match_patch'],
      tests_require = ['lxml', 'cssselect', 'fudge'],
      test_suite = "example.runtests.runtests",
      classifiers=["Development Status :: 3 - Alpha",
                   "Environment :: Web Environment",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Framework :: Django",])
