"""S3 media storage (Garage) addressed through the app's own /media/ route.

Overriding url() keeps every image URL on yardwise.meklab.net, so the
login + garden-membership gate in serve_media applies to S3-backed files
exactly as it did to disk files - no presigned URLs to leak or expire.
"""

from storages.backends.s3boto3 import S3Boto3Storage


class GardenMediaStorage(S3Boto3Storage):
    file_overwrite = True  # keys are date-pathed; overwrite = same file

    def url(self, name, parameters=None, expire=None, http_method=None):
        return f"/media/{name}"
