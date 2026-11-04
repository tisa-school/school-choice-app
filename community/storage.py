from pathlib import PurePosixPath
from uuid import uuid4
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from .models import PrivateUpload

class DatabasePrivateStorage(Storage):
    """No public URLs. All reads go through the school-authorized media view."""
    def _open(self, name, mode='rb'):
        if mode != 'rb': raise ValueError('Private uploads are read-only after creation.')
        try: upload = PrivateUpload.objects.get(name=name)
        except PrivateUpload.DoesNotExist: raise FileNotFoundError(name)
        return ContentFile(bytes(upload.data), name=name)
    def _save(self, name, content):
        data = content.read(settings.MAX_IMAGE_BYTES + 1)
        if len(data) > settings.MAX_IMAGE_BYTES: raise ValueError('Upload exceeds the configured size limit.')
        # Ignore caller filenames; keep a validated raster suffix for response MIME type.
        suffix = PurePosixPath(name).suffix.lower()
        if suffix not in {'.jpg', '.jpeg', '.png', '.webp'}: raise ValueError('Unsupported private file type.')
        stored_name = f'private/{uuid4().hex}{suffix}'
        PrivateUpload.objects.create(name=stored_name, data=data, size=len(data))
        return stored_name
    def exists(self, name): return PrivateUpload.objects.filter(name=name).exists()
    def size(self, name): return PrivateUpload.objects.values_list('size', flat=True).get(name=name)
    def delete(self, name): PrivateUpload.objects.filter(name=name).delete()
    def url(self, name): raise ValueError('Private uploads have no public URL. Use the authorized media view.')
