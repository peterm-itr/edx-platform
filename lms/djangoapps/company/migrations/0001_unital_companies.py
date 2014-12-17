# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Company'
        db.create_table('company', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(db_index=True, max_length=255, blank=True)),
            ('address', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('real_address', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('inn', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('kpk', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('ceo_name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
        ))
        db.send_create_signal('company', ['Company'])


    def backwards(self, orm):
        # Deleting model 'Company'
        db.delete_table('company')


    models = {
        'company.company': {
            'Meta': {'object_name': 'Company', 'db_table': "'company'"},
            'address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'ceo_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inn': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'kpk': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'real_address': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '255', 'blank': 'True'})
        }
    }

    complete_apps = ['company']