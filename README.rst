Wikify is a lightweight module to turn your static Django model views into
full wiki pages.

Rationale
=========
Wikify comes with a small and simple set of loosely coupled views, backed by
example templates. This gives you, the developer, some control over
what is happening. Either extend the existing code, or base your own wiki
implementation on this code here (it's licensed under the permissive BSD
license).

Wikify tries just to be a bare wiki - no page-based permission system, no
subscriptions, even no integrated markup support... This means that you have to
provide your own components in case you need some of that functionality.
Luckily Django has already plenty of those to offer.

Features
========

- Page edit, diff view, old version view, list of all page versions
- Model versioning (built on the nice django-reversion)
- View decorator to turn your view into a wiki page

Each version stores:

- author information (including IP address of anonymous users)
- date & time of change
- an optional comment
- a copy of the instance at this time

Install & Example
=================

Quick install:

    $ virtualenv env
    $ source env/bin/activate
    $ python setup.py develop

To run the example see `example/README.rst`.

Requirements
============

- Django >= 1.3
- django-reversion >= 1.4
- diff-match-patch

Run unit tests
==============

    $ python setup.py test
