from django.contrib.auth.middleware import PersistentRemoteUserMiddleware


class AuthentikRemoteUserMiddleware(PersistentRemoteUserMiddleware):
    """Trust the username Authentik's forward-auth injects at the ingress.

    Unknown usernames get a Django user auto-created on first login
    (RemoteUserBackend default), so adding someone is purely an Authentik
    operation - no Django-side account step.
    """

    header = "HTTP_X_AUTHENTIK_USERNAME"
