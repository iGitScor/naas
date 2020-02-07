"""
Mongodb library.
"""
import re
import uuid
from bson import ObjectId
from bson.errors import BSONError
from datetime import datetime, timedelta
from dictdiffer import diff, ADD, CHANGE, REMOVE
from pymongo.errors import PyMongoError, OperationFailure
from pymongo.results import DeleteResult, UpdateResult

from dispatcher.lib import change_key_name, sub_key

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


class CollectionError(Exception):
    """Collection level error."""
    pass


class AbstractModel(object):
    """
    General mongo abstraction of a model.
    """
    _saved = {}  # local saved state ; updated on insert/update/remove

    def __init__(self, _id=None, created_at=None, *args, **kwargs):
        self._id = _id
        if not isinstance(created_at, datetime):
            created_at = self.now
        self.created_at = created_at

        self._check_args(args, kwargs)

    @property
    def now(self):
        """
        Give current date, without microseconds (unsupported by mongo).

        :rtype: datetime
        """
        return self._filter_micro(datetime.now())

    def _check_args(self, args, kwargs):
        """Check for unparsed parameters."""
        if args not in [(), None] or kwargs not in [{}, None]:
            print(f'Ignored values on {self.__class__.__name__} creation ; {args} -- {kwargs}')

    @staticmethod
    def convert_case(name):
        """
        Convert camel case names to snake case.
        https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case

        :param str name:
        :rtype: str
        """
        fc_ = first_cap_re.sub(r'\1_\2', name)
        return all_cap_re.sub(r'\1_\2', fc_).lower()

    @staticmethod
    def _filter_micro(date):
        """
        Remove microseconds from a datetime.

        :param datetime date:
        :rtype: datetime
        """
        return date - timedelta(microseconds=date.microsecond)

    @classmethod
    def from_dict(cls, dict_):
        """
        All models must be loadable from a dict.

        :param dict dict_:
        :rtype: AbstractModel
        """
        dic_o = dict_
        for key in dict_:
            converted_key = key
            if key == 'id':
                converted_key = '_id'
            elif key == 'type':
                converted_key = 'type_'
            elif key == 'scope':
                converted_key = 'scopes'
            else:
                converted_key = cls.convert_case(key)

            if key != converted_key:
                dic_o = change_key_name(dict_=dic_o, key=key, with_=converted_key)

        return cls(**dic_o)

    @staticmethod
    def gen_id():
        """Generate a unique id."""
        return str(ObjectId())

    @staticmethod
    def gen_token():
        """Generate a token string."""
        return uuid.uuid4().hex[:35]

    def get(self, key):
        """Find an object value with a path."""
        return sub_key(self.to_dict(), key)

    def post_init(self):
        """
        Do some post init validations.
        Add an _id if its a new object, or update local state if not.

        ! Necesssary for all first class models !
        """
        if self._id is None:  # New object
            self._id = self.gen_id()
            self._saved = {}
        else:
            self.update_saved()

    def to_dict(self):
        """
        All models must be convertible to dict.

        :rtype: dict
        """
        raise NotImplementedError()

    def to_json(self):
        """
        Convert object to json (cleaned up)

        :rtype: dict
        """
        dict_ = self.to_dict()
        for key in ['_id', 'id', 'createdAt', 'created_at']:
            if key in dict_:
                del dict_[key]

        return dict_

    def update_saved(self):
        """Update local saved state."""
        self._saved = self.to_dict()

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(('id', self.id))

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self._id)

    def __str__(self):
        return self.__repr__()


class MongoCollection(object):
    """
    Collection level abstraction.

    ! Don't use as is !
    """
    class_ = None
    collection_name = None

    def __init__(self, db):
        """
        :param pymongo.Database db: database instance
        """
        self.collection = db.get_collection(self.collection_name)

    @staticmethod
    def has_succeed(response):
        """
        Tell if mongo reports a success.

        :param dict/UpdateResult response: response given by mongodb
        :rtype: bool
        """
        if isinstance(response, (UpdateResult, DeleteResult)):
            response = response.raw_result

        return 'ok' in response and response['ok'] == 1.0

    def __default_update_result(self, _id):
        """Return a default (empty) UpdateResult object."""
        return UpdateResult({'upserted': _id}, acknowledged=True)

    def delete(self, model, *args, **kwargs):
        """
        Delete a model from db.

        :param AbstractModel model:
        :rtype: DeleteResult
        """
        if not isinstance(model, self.class_):
            raise CollectionError(f'Wrong class {self.class_}')

        result = self.delete_document(query={'_id': model._id}, *args, **kwargs)

        model._id = None
        model.update_saved()

        return result

    def delete_document(self, query, *args, **kwargs):
        """
        Delete elements from db.

        :param dict query: mongo filter identifying the document to update
        :rtype: DeleteResult
        """
        try:
            return self.collection.delete_one(query, *args, **kwargs)

        except OperationFailure as exc:
            message = f'Operation failure on delete: {exc}'
        except Exception as exc:
            message = f'{type(exc)} on delete: {exc}'

        raise CollectionError(message)

    def find(self, query, *args, **kwargs):
        """
        Find documents.

        :param dict query: mongo filter
        :rtype: pymongo.Cursor
        """
        return self.collection.find(query, *args, **kwargs)

    def find_one(self, query, *args, **kwargs):
        """
        Find a document.

        :param dict query: mongo filter
        :rtype: pymongo.Cursor
        """
        return self.collection.find_one(query, *args, **kwargs)

    def insert(self, model, *args, **kwargs):
        """
        Insert a model into db.
        ! Modify model to insert db id !

        :param AbstractModel model:
        :returns: id of the inserted element
        :rtype: str
        """
        if not isinstance(model, self.class_):
            raise CollectionError(f'Wrong class {self.class_} used')

        inserted_id = self.insert_document(model.to_dict(), *args, **kwargs)

        if not hasattr(model, '_id') or model._id is None:
            model._id = inserted_id

        model.update_saved()

        return inserted_id

    def insert_document(self, document, *args, **kwargs):
        """
        Insert a document into db.

        :param dict document:
        :returns: id of the inserted element
        :rtype: str
        """
        try:
            insert = self.collection.insert_one(document=document, *args, **kwargs)

        except OperationFailure as exc:
            message = f'Operation failure on insert: {exc}'
            raise CollectionError(message)
        except Exception as exc:
            message = f'{type(exc)} on insert: {exc}'
            raise CollectionError(message)

        return insert.inserted_id

    def update(self, model, *args, **kwargs):
        """
        Update a model into db.

        :param AbstractModel model:
        :rtype: UpdateResult
        """
        if not isinstance(model, self.class_):
            raise CollectionError(f'Wrong class {self.class_}')

        update_dict = self.generate_update_query(model._saved, model.to_dict())

        result = self.__default_update_result(model._id)
        if len(update_dict) > 0:
            result = self.update_document(
                query={'_id': model._id},
                update=update_dict,
                *args, **kwargs
            )
            model.update_saved()

        return result

    def update_document(self, query, update, *args, **kwargs):
        """
        Update a document into db.

        :param dict query: mongo filter identifying the document to update
        :param dict update: update dict (set/unset...)
        :rtype: UpdateResult
        """
        try:
            update_result = self.collection.update_one(
                filter=query,
                update=update,
                *args, **kwargs
            )

        except BSONError as exc:
            message = f'Document format error: {exc}'
            raise CollectionError(message)
        except OperationFailure as exc:
            message = f'Operation failure on update: {exc}'
            raise CollectionError(message)
        except PyMongoError as exc:
            message = f'Pymongo error: {exc}'
            raise CollectionError(message)
        except TypeError as exc:
            message = f'TypeError on update: {exc}'
            raise CollectionError(message)
        except Exception as exc:
            message = f'{type(exc)} on update: {exc}'
            raise CollectionError(message)

        return update_result

    def save(self, model):
        """
        Save a Model instance.

        :param AbstractModel model:
        :returns: id of the processed element
        :rtype: str
        """
        missing = self.find_one({'_id': model._id}) is None
        if missing:
            return self.insert(model=model)
        else:
            return self.update(model=model).upserted_id

    def spawn(self, query):
        """
        Find a document and return the corresponding model.

        :param dict query: a mongo query filter
        :rtype: AbstractModel
        """
        doc = self.find_one(query)
        if doc is None:
            raise CollectionError(f'No document found: {query}')

        return self.class_.from_dict(doc)

    @staticmethod
    def generate_update_query(original, new_one):
        """
        Generate $set/unset/push/pull query by comparing two dicts.

        NB: There is no atomic operation on lists, because mongo cannot
        push and pull at the same time.
        https://stackoverflow.com/questions/34217874/mongodb-array-push-and-pull

        :param dict original: previous state
        :param dict new_one: new state
        :rtype: dict
        """
        pull_ = {}
        push_ = {}
        set_ = {}
        unset_ = {}

        list_change = {}  # Updated full list
        for diff_ in diff(original, new_one):
            #print(diff_)
            verb, key, values = diff_
            changed_index = None
            if isinstance(key, list):  # an item list has changed
               changed_index = key[-1]
               key = '.'.join(key[:-1])
            pointed_val = sub_key(new_one, key)

            if verb in [ADD, CHANGE]:
                if isinstance(pointed_val, list):
                    if verb == CHANGE and changed_index is not None:  # Changed in list
                        old_val, new_val = values
                        if key not in list_change:
                            list_change[key] = pointed_val
                        list_change[key][changed_index] = new_val
                    else:  # Append in list
                        vals = [v[1] for v in values]
                        push_[key] = {'$each': vals}
                elif isinstance(pointed_val, dict):  # Add in dict
                    for value in values:
                        sk, sv = value
                        set_[f'{key}.{sk}'] = sv
                else:  # Value just changed
                    old_val, new_val = values
                    set_[key] = new_val

            elif verb in [REMOVE]:
                if key == '':  # Element has disappeared
                    for target, old_val in values:
                        unset_[target] = ''
                elif isinstance(pointed_val, list):  # Pop from list
                    if key not in list_change:
                        # Otherwise, its already deleted as a change in list
                        vals = [v[1] for v in values]
                        pull_[key] = {'$in': vals}
                elif isinstance(pointed_val, dict):  # Clear from dict
                    for value in values:
                        sk, sv = value
                        unset_[f'{key}.{sk}'] = sv
                else:
                    print(f'What to do with {key} : {values} ?')

        # Update list as a single operation
        for key, value in list_change.items():
            set_[key] = value

        result = {}
        if pull_:
            result['$pull'] = pull_
        if push_:
            result['$push'] = push_
        if set_:
            result['$set'] = set_
        if unset_:
            result['$unset'] = unset_
        return result
