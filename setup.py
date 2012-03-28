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
      install_requires = ['Django', 'django_reversion', 'diff_match_patch'],
      tests_require = ['lxml', 'fudge'],
      test_suite = "example.runtests.runtests",
      classifiers=["Development Status :: 3 - Alpha",
                   "Environment :: Web Environment",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Framework :: Django",])
