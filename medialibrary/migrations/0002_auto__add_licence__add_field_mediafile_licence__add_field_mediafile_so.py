# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Licence'
        db.create_table('medialibrary_licence', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('code', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=200)),
        ))
        db.send_create_signal('medialibrary', ['Licence'])

        # Adding field 'MediaFile.licence'
        db.add_column('medialibrary_mediafile', 'licence', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['medialibrary.Licence'], null=True), keep_default=False)

        # Adding field 'MediaFile.source_url'
        db.add_column('medialibrary_mediafile', 'source_url', self.gf('django.db.models.fields.CharField')(max_length=400, null=True, blank=True), keep_default=False)

        # Changing field 'MediaFile.file'
        db.alter_column('medialibrary_mediafile', 'file', self.gf('thumbs.models.ImageWithThumbsField')(max_length=255, name='file', sizes=((132, 97), (650, 530), (80, 80))))


    def backwards(self, orm):
        
        # Deleting model 'Licence'
        db.delete_table('medialibrary_licence')

        # Deleting field 'MediaFile.licence'
        db.delete_column('medialibrary_mediafile', 'licence_id')

        # Deleting field 'MediaFile.source_url'
        db.delete_column('medialibrary_mediafile', 'source_url')

        # Changing field 'MediaFile.file'
        db.alter_column('medialibrary_mediafile', 'file', self.gf('thumbs.models.ImageWithThumbsField')(max_length=255, name='file', sizes=((132, 97), (80, 80))))


    models = {
        'medialibrary.category': {
            'Meta': {'ordering': "['parent__title', 'title']", 'object_name': 'Category'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['medialibrary.Category']"}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '150', 'db_index': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'medialibrary.licence': {
            'Meta': {'ordering': "['title']", 'object_name': 'Licence'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '200'})
        },
        'medialibrary.mediafile': {
            'Meta': {'object_name': 'MediaFile'},
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['medialibrary.Category']", 'null': 'True', 'blank': 'True'}),
            'copyright': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'file': ('thumbs.models.ImageWithThumbsField', [], {'max_length': '255', 'name': "'file'", 'sizes': '((132, 97), (650, 530), (80, 80))'}),
            'file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'licence': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['medialibrary.Licence']", 'null': 'True'}),
            'source_url': ('django.db.models.fields.CharField', [], {'max_length': '400', 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '12'})
        },
        'medialibrary.mediafiletranslation': {
            'Meta': {'object_name': 'MediaFileTranslation'},
            'caption': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language_code': ('django.db.models.fields.CharField', [], {'default': "'ar'", 'max_length': '10'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'translations'", 'to': "orm['medialibrary.MediaFile']"})
        }
    }

    complete_apps = ['medialibrary']
