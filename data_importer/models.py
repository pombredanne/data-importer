#!/usr/bin/env python
# -*- coding: utf-8 -*-

from django.db import models
import os
import tempfile
import zipfile
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.conf import settings

DATA_IMPORTER_TASK = hasattr(settings, 'DATA_IMPORTER_TASK') and settings.DATA_IMPORTER_TASK or 0

CELERY_STATUS = ((1, 'Impoted'),
                 (2, 'Waiting'),
                 (3, 'Cancelled'),
                 (-1, 'Error'),
                 )


class FileHistoryManager(models.Manager):
    def get_query_set(self):
        return super(FileHistoryManager, self).get_query_set().filter(active=True)


class FileHistory(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True, db_index=True)
    filename = models.FileField(upload_to="upload_history/%Y/%m/%d/")
    owner = models.ForeignKey(User, null=True)
    is_task = models.BooleanField(default=DATA_IMPORTER_TASK)
    status = models.IntegerField(choices=CELERY_STATUS, default=1)

    objects = FileHistoryManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name_plural = 'File Hitories'

    def download_file(self, request):
        """
        Send a file through Django without loading the whole file into
        memory at once. The FileWrapper will turn the file object into an
        iterator for chunks of 8KB.
        """
        filename = self.filename.path
        wrapper = FileWrapper(open(filename, "rb"))
        response = HttpResponse(wrapper, content_type='application/force-download')
        response['Content-Length'] = os.path.getsize(filename)
        return response

    def download_zipfile(self, request):
        """
        Create a ZIP file on disk and transmit it in chunks of 8KB,
        without loading the whole file into memory. A similar approach can
        be used for large dynamic PDF files.
        """
        temp = tempfile.TemporaryFile()
        archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
        for index in range(10):
            filename = self.filename.path
            archive.write(filename, 'file%d.txt' % index)
        archive.close()
        wrapper = FileWrapper(temp)
        response = HttpResponse(wrapper, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=%s.zip' % self.filename
        response['Content-Length'] = temp.tell()
        temp.seek(0)
        return response


class FileHistoryLog(models.Model):
    filehistory = models.ForeignKey(FileHistory)
    created_at = models.DateTimeField(auto_now_add=True)
    log = models.CharField(max_length=255)

    def __unicode__(self):
        return self.log
