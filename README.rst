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

- Model versioning (built on the nice django-reversion)
- Page edit, versioned view, list of all page versions
- View decorator to turn your view into a wiki page

Requirements
============

  * Django 1.3
  * django-reversion >= 1.4
