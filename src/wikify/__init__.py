__all__ = ["wikify"]

def wikify(model_ref):
    def decorator(func):
        def inner(request, *args, **kwargs):
            # Import lazily, so we don't import views directly, saves us some
            # trouble, e.g. https://bitbucket.org/kumar303/fudge/issue/17/module-import-order-influences-whether
            from wikify.views import edit, diff, version, versions

            if isinstance(model_ref, basestring):
                try:
                    module_str, model_str = model_ref.rsplit('.', 1)
                    module = __import__(module_str, fromlist=[model_str])
                    model = getattr(module, model_str)
                except ImportError, e:
                    raise ValueError("Module %s not found: %s"
                                     % (module_str, e))
                except AttributeError:
                    raise ValueError("Module %s has no attribute %s"
                                     % (module_str, model_str))
            else:
                model = model_ref

            # The primary key must be either given by the model field's name, or
            #   simply by Django's standard 'object_id'
            primary_key = model._meta.pk.name
            object_id = kwargs.get(primary_key) or kwargs.get('object_id')

            # Get action
            if request.method == 'POST':
                action = request.POST.get('action')
            else:
                action = request.GET.get('action')

            if action == 'edit':
                return edit(request, model, object_id)
            elif action == 'diff':
                return diff(request, model, object_id)
            elif action == 'version':
                return version(request, model, object_id)
            elif action == 'versions':
                return versions(request, model, object_id)
            else:
                # No valid action given, call decorated view
                return func(request, *args, **kwargs)

        return inner

    return decorator
