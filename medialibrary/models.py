# ------------------------------------------------------------------------
# coding=utf-8
# ------------------------------------------------------------------------

from datetime import datetime

from django.contrib import admin, messages
from django.contrib.auth.decorators import permission_required
from django.conf import settings as django_settings
from django.core.urlresolvers import get_callable
from django.db import models
from django.template.defaultfilters import filesizeformat
from django.utils.safestring import mark_safe
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.template.defaultfilters import slugify
from django.http import HttpResponseRedirect
# 1.2 from django.views.decorators.csrf import csrf_protect

from feincms import settings
from feincms.models import Base

from feincms.templatetags import feincms_thumbnail
from feincms.translations import TranslatedObjectMixin, Translation, \
    TranslatedObjectManager

from thumbs.models import ImageWithThumbsField

import re
import os
import logging
from PIL import Image

# ------------------------------------------------------------------------
class CategoryManager(models.Manager):
    """
    Simple manager which exists only to supply ``.select_related("parent")``
    on querysets since we can't even __unicode__ efficiently without it.
    """
    def get_query_set(self):
        return super(CategoryManager, self).get_query_set().select_related("parent")

# ------------------------------------------------------------------------
class Licence(models.Model):
    """
    These Licence are for the images
    """

    title = models.CharField(_('title'), max_length = 200)
    code = models.CharField(max_length = 200)
    url = models.CharField(max_length = 200)

    class Meta:
        ordering = ['title']
        verbose_name = _('licence')
        verbose_name_plural = _('licences')

    def __unicode__(self):
        return self.title


class LicenceAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'url']
    list_per_page = 25
    search_fields = ['title']

# ------------------------------------------------------------------------
class Category(models.Model):
    """
    These categories are meant primarily for organizing media files in the
    library.
    """

    title = models.CharField(_('title'), max_length = 200)
    parent = models.ForeignKey('self', blank = True, null = True,
        related_name = 'children', limit_choices_to = {'parent__isnull': True},
        verbose_name = _('parent'))

    slug = models.SlugField(_('slug'), max_length = 150)

    class Meta:
        ordering = ['parent__title', 'title']
        verbose_name = _('category')
        verbose_name_plural = _('categories')

    objects = CategoryManager()

    def __unicode__(self):
        if self.parent_id:
            return u'%s - %s' % (self.parent.title, self.title)

        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)

        super(Category, self).save(*args, **kwargs)


class CategoryAdmin(admin.ModelAdmin):
    list_display = ['parent', 'title']
    list_filter = ['parent']
    list_per_page = 25
    search_fields = ['title']
    prepopulated_fields = { 'slug': ('title',), }


# ------------------------------------------------------------------------
class MediaFileBase(Base, TranslatedObjectMixin):
    """
    Abstract media file class. Inherits from :class:`feincms.module.Base`
    because of the (handy) extension mechanism.
    """

    from django.core.files.storage import FileSystemStorage
    default_storage_class = getattr(django_settings, 'DEFAULT_FILE_STORAGE',
                                    'django.core.files.storage.FileSystemStorage')
    default_storage = get_callable(default_storage_class)

    fs = default_storage(location = settings.FEINCMS_MEDIALIBRARY_ROOT,
                           base_url = settings.FEINCMS_MEDIALIBRARY_URL)

    sizes = getattr(django_settings, 'MEDIALIBRARY_IMAGESIZES', ())

    file = ImageWithThumbsField(_('file'), sizes = sizes, max_length = 255, upload_to = settings.FEINCMS_MEDIALIBRARY_UPLOAD_TO, storage = fs)
    type = models.CharField(_('file type'), max_length = 12, editable = False, choices = ())
    created = models.DateTimeField(_('created'), editable = False, default = datetime.now)
    copyright = models.CharField(_('copyright'), max_length = 200, blank = True)
    file_size = models.IntegerField(_("file size"), blank = True, null = True, editable = False)

    categories = models.ManyToManyField(Category, verbose_name = _('categories'),
                                        blank = True, null = True)
    categories.category_filter = True

    licence = models.ForeignKey(Licence, null=True)
    source_url = models.CharField(max_length=400, blank=True, null=True)

    class Meta:
        abstract = True
        verbose_name = _('media file')
        verbose_name_plural = _('media files')

    objects = TranslatedObjectManager()

    filetypes = [ ]
    filetypes_dict = { }

    def formatted_file_size(self):
        return filesizeformat(self.file_size)
    formatted_file_size.short_description = _("file size")
    formatted_file_size.admin_order_field = 'file_size'

    def formatted_created(self):
        return self.created.strftime("%Y-%m-%d %H:%M")
    formatted_created.short_description = _("created")
    formatted_created.admin_order_field = 'created'

    @classmethod
    def reconfigure(cls, upload_to = None, storage = None):
        f = cls._meta.get_field('file')
        # Ugh. Copied relevant parts from django/db/models/fields/files.py
        # FileField.__init__ (around line 225)
        if storage:
            f.storage = storage
        if upload_to:
            f.upload_to = upload_to
            if callable(upload_to):
                f.generate_filename = upload_to

    @classmethod
    def register_filetypes(cls, *types):
        cls.filetypes[0:0] = types
        choices = [ t[0:2] for t in cls.filetypes ]
        cls.filetypes_dict = dict(choices)
        cls._meta.get_field('type').choices[:] = choices

    def __init__(self, *args, **kwargs):
        super(MediaFileBase, self).__init__(*args, **kwargs)
        if self.file and self.file.path:
            self._original_file_path = self.file.path

    def __unicode__(self):
        trans = None

        # This might be provided using a .extra() clause to avoid hundreds of extra queries:
        if hasattr(self, "preferred_translation"):
            trans = getattr(self, "preferred_translation", u"")
        else:
            try:
                trans = unicode(self.translation)
            except models.ObjectDoesNotExist:
                pass
            except AttributeError, e:
                pass

        if trans:
            return trans
        else:
            return os.path.basename(self.file.name)

    def get_absolute_url(self):
        return self.file.url

    def file_type(self):
        t = self.filetypes_dict[self.type]
        if self.type == 'image':
            try:
                from django.core.files.images import get_image_dimensions
                d = get_image_dimensions(self.file.file)
                if d: t += "<br/>%d&times;%d" % (d[0], d[1])
            except IOError, e:
                t += "<br/>(%s)" % e.strerror
        return t
    file_type.admin_order_field = 'type'
    file_type.short_description = _('file type')
    file_type.allow_tags = True

    def file_info(self):
        """
        Method for showing the file name in admin.

        Note: This also includes a hidden field that can be used to extract
        the file name later on, this can be used to access the file name from
        JS, like for example a TinyMCE connector shim.
        """
        from os.path import basename
        from feincms.utils import shorten_string
        return u'<input type="hidden" class="medialibrary_file_path" name="_media_path_%d" value="%s" /> %s' % (
                self.id,
                self.file.name,
                shorten_string(basename(self.file.name), max_length = 28),)
    file_info.short_description = _('file info')
    file_info.allow_tags = True

    def copyright_text(self):
        return '%s, (c) %s (%s)', (self.translation.caption, self.copyright, self.licence.code)

    def determine_file_type(self, name):
        for type_key, type_name, type_test in self.filetypes:
            if type_test(name):
                return type_key
        return self.filetypes[-1][0]

    def save(self, *args, **kwargs):
        if not self.id and not self.created:
            self.created = datetime.now()

        self.type = self.determine_file_type(self.file.name)
        if self.file:
            try:
                self.file_size = self.file.size
            except (OSError, IOError, ValueError), e:
                logging.error("Unable to read file size for %s: %s", self, e)

        # Try to detect things that are not really images
        if self.type == 'image':
            try:
                try:
                    image = Image.open(self.file)
                except (OSError, IOError):
                    image = Image.open(self.file.path)

                # Rotate image based on exif data.
                if image:
                    try:
                        exif = image._getexif()
                    except (AttributeError, IOError):
                        exif = False
                    # PIL < 1.1.7 chokes on JPEGs with minimal EXIF data and
                    # throws a KeyError deep in its guts.
                    except KeyError:
                        exif = False

                    if exif:
                        orientation = exif.get(274)
                        rotation = 0
                        if orientation == 3:
                            rotation = 180
                        elif orientation == 6:
                            rotation = 270
                        elif orientation == 8:
                            rotation = 90
                        if rotation:
                            image = image.rotate(rotation)
                            image.save(self.file.path)

            except (OSError, IOError), e:
                self.type = self.determine_file_type('***') # It's binary something

        if getattr(self, '_original_file_path', None):
            if self.file.path != self._original_file_path:
                try:
                    os.unlink(self._original_file_path)
                except:
                    pass

        super(MediaFileBase, self).save(*args, **kwargs)
        self.purge_translation_cache()

# ------------------------------------------------------------------------
MediaFileBase.register_filetypes(
        # Should we be using imghdr.what instead of extension guessing?
        ('image', _('Image'), lambda f: re.compile(r'\.(bmp|jpe?g|jp2|jxr|gif|png|tiff?)$', re.IGNORECASE).search(f)),
        ('other', _('Binary'), lambda f: True), # Must be last
    )

"""
        ('video', _('Video'), lambda f: re.compile(r'\.(mov|m[14]v|mp4|avi|mpe?g|qt|ogv|wmv)$', re.IGNORECASE).search(f)),
        ('audio', _('Audio'), lambda f: re.compile(r'\.(au|mp3|m4a|wma|oga|ram|wav)$', re.IGNORECASE).search(f)),
        ('pdf', _('PDF document'), lambda f: f.lower().endswith('.pdf')),
        ('swf', _('Flash'), lambda f: f.lower().endswith('.swf')),
        ('txt', _('Text'), lambda f: f.lower().endswith('.txt')),
        ('rtf', _('Rich Text'), lambda f: f.lower().endswith('.rtf')),
        ('zip', _('Zip archive'), lambda f: f.lower().endswith('.zip')),
        ('doc', _('Microsoft Word'), lambda f: re.compile(r'\.docx?$', re.IGNORECASE).search(f)),
        ('xls', _('Microsoft Excel'), lambda f: re.compile(r'\.xlsx?$', re.IGNORECASE).search(f)),
        ('ppt', _('Microsoft PowerPoint'), lambda f: re.compile(r'\.pptx?$', re.IGNORECASE).search(f)),
"""

# ------------------------------------------------------------------------
class MediaFile(MediaFileBase):
    @classmethod
    def register_extension(cls, register_fn):
        register_fn(cls, MediaFileAdmin)

# ------------------------------------------------------------------------
# ------------------------------------------------------------------------
class MediaFileTranslation(Translation(MediaFile)):
    """
    Translated media file caption and description.
    """

    caption = models.CharField(_('caption'), max_length = 200)
    description = models.TextField(_('description'), blank = True)

    class Meta:
        verbose_name = _('media file translation')
        verbose_name_plural = _('media file translations')

    def __unicode__(self):
        return self.caption

#-------------------------------------------------------------------------
class MediaFileTranslationInline(admin.StackedInline):
    model = MediaFileTranslation
    max_num = len(django_settings.LANGUAGES)


def admin_thumbnail(obj):
    if obj.type == 'image':
        image = None
        try:
            image = feincms_thumbnail.thumbnail(obj.file.name, '100x60')
        except:
            pass

        if image:
            return mark_safe(u"""
                <a href="%(url)s" target="_blank">
                    <img src="%(image)s" alt="" />
                </a>""" % {
                    'url': obj.file.url,
                    'image': image, })
    return ''
admin_thumbnail.short_description = _('Preview')
admin_thumbnail.allow_tags = True

#-------------------------------------------------------------------------
class MediaFileAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    inlines = [MediaFileTranslationInline]
    list_display = ['__unicode__', admin_thumbnail, 'file_type', 'licence', 'copyright', 'file_info', 'formatted_file_size', 'formatted_created']
    list_filter = ['type', 'categories', 'licence']
    list_per_page = 25
    search_fields = ['copyright', 'file', 'translations__caption']
    filter_horizontal = ("categories",)

    def get_urls(self):
        from django.conf.urls.defaults import url, patterns

        urls = super(MediaFileAdmin, self).get_urls()
        my_urls = patterns('',
            url(r'^mediafile-bulk-upload/$', self.admin_site.admin_view(MediaFileAdmin.bulk_upload), {}, name = 'mediafile_bulk_upload')
            )

        return my_urls + urls

    def changelist_view(self, request, extra_context = None):
        if extra_context is None:
            extra_context = {}
        extra_context['categories'] = Category.objects.all()
        return super(MediaFileAdmin, self).changelist_view(request, extra_context = extra_context)

    @staticmethod
    # 1.2 @csrf_protect
    @permission_required('medialibrary.add_mediafile')
    def bulk_upload(request):
        from django.core.urlresolvers import reverse
        from django.utils.functional import lazy

        def import_zipfile(request, category_id, data):
            import zipfile
            from os import path

            category = None
            if category_id:
                category = Category.objects.get(pk = int(category_id))

            try:
                z = zipfile.ZipFile(data)

                storage = MediaFile.fs
                if not storage:
                    messages.error(request, _("Could not access storage"))
                    return

                count = 0
                for zi in z.infolist():
                    if not zi.filename.endswith('/'):
                        from django.template.defaultfilters import slugify
                        from django.core.files.base import ContentFile

                        bname = path.basename(zi.filename)
                        if bname and not bname.startswith(".") and "." in bname:
                            fname, ext = path.splitext(bname)
                            target_fname = slugify(fname) + ext.lower()

                            mf = MediaFile()
                            mf.file.save(target_fname, ContentFile(z.read(zi.filename)))
                            mf.save()
                            if category:
                                mf.categories.add(category)
                            count += 1

                messages.info(request, _("%d files imported") % count)
            except Exception, e:
                messages.error(request, _("ZIP file invalid: %s") % str(e))
                return

        if request.method == 'POST' and 'data' in request.FILES:
            import_zipfile(request, request.POST.get('category'), request.FILES['data'])
        else:
            messages.error(request, _("No input file given"))

        return HttpResponseRedirect(reverse('admin:medialibrary_mediafile_changelist'))

    def queryset(self, request):
        qs = super(MediaFileAdmin, self).queryset(request)

        # FIXME: This is an ugly hack but it avoids 1-3 queries per *FILE*
        # retrieving the translation information
        if django_settings.DATABASE_ENGINE == 'postgresql_psycopg2':
            qs = qs.extra(
                select = {
                    'preferred_translation':
                        """SELECT caption FROM medialibrary_mediafiletranslation
                        WHERE medialibrary_mediafiletranslation.parent_id = medialibrary_mediafile.id
                        ORDER BY
                            language_code = %s DESC,
                            language_code = %s DESC,
                            LENGTH(language_code) DESC
                        LIMIT 1
                        """
                },
                select_params = (translation.get_language(), django_settings.LANGUAGE_CODE)
            )
        return qs

    def save_model(self, request, obj, form, change):
        obj.purge_translation_cache()
        return super(MediaFileAdmin, self).save_model(request, obj, form, change)


#-------------------------------------------------------------------------
