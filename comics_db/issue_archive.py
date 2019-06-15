import tempfile
from zipfile import ZIP_DEFLATED

import boto3
import zipstream
from django.conf import settings


class S3FileWrapper:
    """
    Get S3 key and wraps it to iterator.

    Class needed for downloading multiple issues and to postpone download of actual file until zip started
    """

    def __init__(self, bucket, key):
        self._bucket = bucket
        self.key = key
        self.file = None

    def get_file(self):
        with tempfile.NamedTemporaryFile() as comics_file:
            self.file = comics_file
            self._bucket.download_fileobj(self.key, comics_file)
            comics_file.seek(0)
            yield comics_file.read()


def construct_archive(issues):
    session = boto3.session.Session()
    s3 = session.resource('s3', region_name=settings.DO_REGION_NAME,
                          endpoint_url=settings.DO_ENDPOINT_URL,
                          aws_access_key_id=settings.DO_KEY_ID,
                          aws_secret_access_key=settings.DO_SECRET_ACCESS_KEY)
    bucket = s3.Bucket(settings.DO_STORAGE_BUCKET_NAME)

    z = zipstream.ZipFile(mode='w', compression=ZIP_DEFLATED, allowZip64=True)

    for issue in issues:
        f = S3FileWrapper(bucket, issue[1])
        z.write_iter(issue[0], f.get_file())

    return z
