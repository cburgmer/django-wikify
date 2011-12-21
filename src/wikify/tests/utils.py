import datetime

import fudge

def _fake_meta(pk, other_fields):
    fields = [fudge.Fake('Field').has_attr(name=field_name).is_a_stub()
              for field_name in [pk] + other_fields]
    # Workaround for fudge creating a callable fake that throws a runtime
    # error and Django not likeing that in its template guessing algorithm
    # https://bitbucket.org/kumar303/fudge/issue/15/callable-fudgefake-returns-true-even
    for field in fields:
        field.is_callable().returns(field)

    return fudge.Fake('Meta').has_attr(fields=fields, pk=fields[0],
                                       many_to_many=[])


def construct_instance(title, content):
    instance = (fudge.Fake('Page')
                     .has_attr(pk=title)
                     .has_attr(title=title)
                     .has_attr(content=content)
                     .has_attr(_meta=_fake_meta('title', ['content'])))
    # Workaround for fudge creating a callable fake that throws a runtime
    # error and Django not likeing that in its template guessing algorithm
    # https://bitbucket.org/kumar303/fudge/issue/15/callable-fudgefake-returns-true-even
    instance.is_callable().returns(instance)
    return instance

def construct_version(user_name=None, ip_address=None, comment=None,
                      instance=None, date_created=None):
    # Workaround for __str__ not being overwritable in Fudge!?
    # https://bitbucket.org/kumar303/fudge/issue/16/cannot-overwrite-fake-objects-__str__
    fake_user = (fudge.Fake('User').is_callable().returns(user_name)
                    if user_name else None)

    # Workaround for fudge creating a callable fake that throws a runtime
    # error and Django not likeing that in its template guessing algorithm
    # https://bitbucket.org/kumar303/fudge/issue/15/callable-fudgefake-returns-true-even
    if ip_address:
        fake_versionmeta_set = (fudge.Fake('versionmeta_set_helper')
                                        .is_callable()
                                        .returns(fudge.Fake('versionmeta_set')
                                                    .provides('get')
                                                    .returns(fudge.Fake('versionmeta')
                                                                    .has_attr(ip_address=ip_address))))
    else:
        fake_versionmeta_set = None

    date_created = date_created or datetime.datetime.utcnow()
    fake_revision = (fudge.Fake('Revision')
                            .has_attr(user=fake_user)
                            .has_attr(versionmeta_set=fake_versionmeta_set)
                            .has_attr(date_created=date_created)
                            .has_attr(comment=comment))
    instance = instance or construct_instance(title='test title',
                                              content='test content')

    page_class = (fudge.Fake('PageClass')
                       .has_attr(_meta=_fake_meta('title', ['content'])))
    version = (fudge.Fake('Version')
                    .has_attr(id=42)
                    .has_attr(revision=fake_revision)
                    .has_attr(object_version=fudge.Fake()
                                                    .has_attr(object=instance)))

    # Workaround for fudge creating a callable fake that throws a runtime
    # error and Django not likeing that in its template guessing algorithm
    # https://bitbucket.org/kumar303/fudge/issue/15/callable-fudgefake-returns-true-even
    fake_revision.is_callable().returns(fake_revision)
    version.is_callable().returns(version)
    return version

def construct_versions(version_count, user_name=None, ip_address=None):
    versions = []
    for i in range(version_count):
        instance = construct_instance(title='test title',
                                      content='content_%s' % i)
        date_created = (datetime.datetime.utcnow()
                        - datetime.timedelta(hours=i))
        version = construct_version(user_name=user_name,
                                            ip_address=ip_address,
                                            comment='Version %s' % i,
                                            instance=instance)
        versions.append(version)
    return versions
