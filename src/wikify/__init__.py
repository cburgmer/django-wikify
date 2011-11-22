__all__ = ["wikify"]

def wikify(model):
    def decorator(func):
        def inner(request, *args, **kwargs):
            # Import lazily, so we don't import views directly, saves us some
            # trouble, e.g. https://bitbucket.org/kumar303/fudge/issue/17/module-import-order-influences-whether
            from wikify.views import edit, version, versions

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
            elif action == 'version':
                return version(request, model, object_id)
            elif action == 'versions':
                return versions(request, model, object_id)
            else:
                # No valid action given, call decorated view
                return func(request, *args, **kwargs)

        return inner

    return decorator
