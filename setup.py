import re
import ez_setup
ez_setup.use_setuptools()
from setuptools import setup

def parse_requirements(file_name):
    requirements = []
    for line in open(file_name, 'r').read().split('\n'):
        if re.match(r'(\s*#)|(\s*$)', line):
            continue
        if re.match(r'\s*-e\s+', line):
            requirements.append(re.sub(r'\s*-e\s+.*#egg=(.*)$', r'\1', line))
        elif re.match(r'\s*-f\s+', line):
            pass
        else:
            requirements.append(line)

    return requirements

setup(name="django-wikify",
      #version="0.1",
      description="Wikify is a lightweight module to turn your static Django model views into full wiki pages.",
      long_description=open('README.md').read(),
      author="Christoph Burgmer",
      author_email="cburgmer@ira.uka.de",
      url="http://github.com/cburgmer/django-wikify",
      packages=["wikify"],
      package_dir={"": "src"},
      package_data = {"wikify": ["static/wikify/*.css", "templates/wikify/*.html"]},
      dependency_links = [
          "http://google-diff-match-patch.googlecode.com/svn/trunk/python2/diff_match_patch.py#egg=diff_match_patch-py2_svn"
      ],
      install_requires = parse_requirements('requirements.txt'),
      tests_require = ['lxml', 'cssselect', 'fudge'],
      test_suite = "example.runtests.runtests",
      classifiers=["Development Status :: 3 - Alpha",
                   "Environment :: Web Environment",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Framework :: Django",])
