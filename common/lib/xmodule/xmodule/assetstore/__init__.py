"""
Classes representing asset metadata.
"""

from datetime import datetime
import dateutil.parser
import pytz
import json
from contracts import contract, new_contract
from opaque_keys.edx.keys import AssetKey
from lxml import etree


new_contract('AssetKey', AssetKey)
new_contract('datetime', datetime)
new_contract('basestring', basestring)
new_contract('AssetElement', lambda x: isinstance(x, etree._Element) and x.tag == "asset")  # pylint: disable=protected-access, no-member
new_contract('AssetsElement', lambda x: isinstance(x, etree._Element) and x.tag == "assets")  # pylint: disable=protected-access, no-member


class AssetMetadata(object):
    """
    Stores the metadata associated with a particular course asset. The asset metadata gets stored
    in the modulestore.
    """

    TOP_LEVEL_ATTRS = ['basename', 'internal_name', 'locked', 'contenttype', 'thumbnail', 'fields']
    EDIT_INFO_ATTRS = ['curr_version', 'prev_version', 'edited_by', 'edited_by_email', 'edited_on']
    CREATE_INFO_ATTRS = ['created_by', 'created_by_email', 'created_on']
    ATTRS_ALLOWED_TO_UPDATE = TOP_LEVEL_ATTRS + EDIT_INFO_ATTRS
    ALL_ATTRS = ['asset_id'] + ATTRS_ALLOWED_TO_UPDATE + CREATE_INFO_ATTRS

    # Default type for AssetMetadata objects. A constant for convenience.
    ASSET_TYPE = 'asset'

    @contract(asset_id='AssetKey',
              basename='basestring|None', internal_name='basestring|None',
              locked='bool|None', contenttype='basestring|None',
              thumbnail='basestring|None', fields='dict|None',
              curr_version='basestring|None', prev_version='basestring|None',
              created_by='int|None', created_by_email='basestring|None', created_on='datetime|None',
              edited_by='int|None', edited_by_email='basestring|None', edited_on='datetime|None')
    def __init__(self, asset_id,
                 basename=None, internal_name=None,
                 locked=None, contenttype=None,
                 thumbnail=None, fields=None,
                 curr_version=None, prev_version=None,
                 created_by=None, created_by_email=None, created_on=None,
                 edited_by=None, edited_by_email=None, edited_on=None,
                 field_decorator=None,):
        """
        Construct a AssetMetadata object.

        Arguments:
            asset_id (AssetKey): Key identifying this particular asset.
            basename (str): Original path to file at asset upload time.
            internal_name (str): Name, url, or handle for the storage system to access the file.
            locked (bool): If True, only course participants can access the asset.
            contenttype (str): MIME type of the asset.
            thumbnail (str): the internal_name for the thumbnail if one exists
            fields (dict): fields to save w/ the metadata
            curr_version (str): Current version of the asset.
            prev_version (str): Previous version of the asset.
            created_by (int): User ID of initial user to upload this asset.
            created_by_email (str): Email address of initial user to upload this asset.
            created_on (datetime): Datetime of intial upload of this asset.
            edited_by (int): User ID of last user to upload this asset.
            edited_by_email (str): Email address of last user to upload this asset.
            edited_on (datetime): Datetime of last upload of this asset.
            field_decorator (function): used by strip_key to convert OpaqueKeys to the app's understanding.
                Not saved.
        """
        self.asset_id = asset_id if field_decorator is None else field_decorator(asset_id)
        self.basename = basename  # Path w/o filename.
        self.internal_name = internal_name
        self.locked = locked
        self.contenttype = contenttype
        self.thumbnail = thumbnail
        self.curr_version = curr_version
        self.prev_version = prev_version
        now = datetime.now(pytz.utc)
        self.edited_by = edited_by
        self.edited_by_email = edited_by_email
        self.edited_on = edited_on or now
        # created_by, created_by_email, and created_on should only be set here.
        self.created_by = created_by
        self.created_by_email = created_by_email
        self.created_on = created_on or now
        self.fields = fields or {}

    def __repr__(self):
        return """AssetMetadata{!r}""".format((
            self.asset_id,
            self.basename, self.internal_name,
            self.locked, self.contenttype, self.fields,
            self.curr_version, self.prev_version,
            self.created_by, self.created_by_email, self.created_on,
            self.edited_by, self.edited_by_email, self.edited_on,
        ))

    def update(self, attr_dict):
        """
        Set the attributes on the metadata. Any which are not in ATTRS_ALLOWED_TO_UPDATE get put into
        fields.

        Arguments:
            attr_dict: Prop, val dictionary of all attributes to set.
        """
        for attr, val in attr_dict.iteritems():
            if attr in self.ATTRS_ALLOWED_TO_UPDATE:
                setattr(self, attr, val)
            else:
                self.fields[attr] = val

    def to_storable(self):
        """
        Converts metadata properties into a MongoDB-storable dict.
        """
        return {
            'filename': self.asset_id.path,
            'basename': self.basename,
            'internal_name': self.internal_name,
            'locked': self.locked,
            'contenttype': self.contenttype,
            'thumbnail': self.thumbnail,
            'fields': self.fields,
            'edit_info': {
                'curr_version': self.curr_version,
                'prev_version': self.prev_version,
                'created_by': self.created_by,
                'created_by_email': self.created_by_email,
                'created_on': self.created_on,
                'edited_by': self.edited_by,
                'edited_by_email': self.edited_by_email,
                'edited_on': self.edited_on
            }
        }

    @contract(asset_doc='dict|None')
    def from_storable(self, asset_doc):
        """
        Fill in all metadata fields from a MongoDB document.

        The asset_id prop is initialized upon construction only.
        """
        if asset_doc is None:
            return
        self.basename = asset_doc['basename']
        self.internal_name = asset_doc['internal_name']
        self.locked = asset_doc['locked']
        self.contenttype = asset_doc['contenttype']
        self.thumbnail = asset_doc['thumbnail']
        self.fields = asset_doc['fields']
        self.curr_version = asset_doc['edit_info']['curr_version']
        self.prev_version = asset_doc['edit_info']['prev_version']
        self.created_by = asset_doc['edit_info']['created_by']
        self.created_by_email = asset_doc['edit_info']['created_by_email']
        self.created_on = asset_doc['edit_info']['created_on']
        self.edited_by = asset_doc['edit_info']['edited_by']
        self.edited_by_email = asset_doc['edit_info']['edited_by_email']
        self.edited_on = asset_doc['edit_info']['edited_on']

    @contract(node='AssetElement')
    def from_xml(self, node):
        """
        Walk the etree XML node and fill in the asset metadata.
        The node should be a top-level "asset" element.
        """
        for child in node:
            qname = etree.QName(child)
            tag = qname.localname
            if tag in self.ALL_ATTRS:
                value = child.text
                if tag == 'asset_id':
                    # Locator.
                    value = AssetKey.from_string(value)
                elif tag == 'locked':
                    # Boolean.
                    value = True if value == "true" else False
                elif tag in ('created_on', 'edited_on'):
                    # ISO datetime.
                    value = dateutil.parser.parse(value)
                elif tag in ('created_by', 'edited_by'):
                    # Integer representing user id.
                    value = int(value)
                elif tag == 'fields':
                    # Dictionary.
                    value = json.loads(value)
                elif value == 'None':
                    # None.
                    value = None
                setattr(self, tag, value)

    @contract(node='AssetElement')
    def to_xml(self, node):
        """
        Add the asset data as XML to the passed-in node.
        The node should already be created as a top-level "asset" element.
        """
        for attr in self.ALL_ATTRS:
            child = etree.SubElement(node, attr)
            value = getattr(self, attr)
            if isinstance(value, bool):
                value = "true" if value else "false"
            elif isinstance(value, datetime):
                value = value.isoformat()
            else:
                value = unicode(value)
            child.text = value

    @staticmethod
    @contract(node='AssetsElement', assets=list)
    def add_all_assets_as_xml(node, assets):
        """
        Take a list of AssetMetadata objects. Add them all to the node.
        The node should already be created as a top-level "assets" element.
        """
        for asset in assets:
            asset_node = etree.SubElement(node, "asset")
            asset.to_xml(asset_node)
