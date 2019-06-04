import flask_sqlalchemy as fsa
from sqlalchemy.ext.declarative import declared_attr

import sys
import pydevd
import logging
import tempfile
import os
import os.path


def stop_on():
	sys.path.append('/Applications/PyCharm.app/Contents/helpers/pydev/')
	sys.path.append('/Applications/PyCharm.app/Contents/debug-eggs/')

	try:
		port = 6868
		print("Waiting for process connection... (Start a \"Python Remote Debug\" run configuration in pycharm with the port {})".format(port))
		logging.info("Waiting for process connection...")
		pydevd.settrace("0.0.0.0", port=port, stdoutToServer=True, stderrToServer=True)
	except SystemExit:
		logging.exception("Failed to connect to remote debugger, punk")


db_counter = 1


def sqlite_connection_factory():
	global db_counter
	tempdir = tempfile.gettempdir()
	temporary_file = os.path.join(tempdir, 'db_{}.db'.format(db_counter))
	db_counter += 1
	open(temporary_file, 'a').close()
	return "sqlite:///{}".format(temporary_file)


def test_basic_binds(app, db):
	binds = {
		'foo': 'sqlite://',
		'bar': 'sqlite://'
	}
	app.config['SQLALCHEMY_BINDS'] = binds

	class Foo(db.Model):
		__bind_key__ = 'foo'
		__table_args__ = {"info": {"bind_key": "foo"}}
		id = db.Column(db.Integer, primary_key=True)

	class Bar(db.Model):
		__bind_key__ = 'bar'
		id = db.Column(db.Integer, primary_key=True)

	class Baz(db.Model):
		id = db.Column(db.Integer, primary_key=True)

	db.create_all()

	# simple way to check if the engines are looked up properly
	assert db.get_engine(app, None) == db.engine
	assert len(app.extensions['sqlalchemy'].connectors) == 2
	for bind in 'foo', 'bar':
		engine = db.get_engine(app, bind)
		connector = app.extensions['sqlalchemy'].connectors[binds[bind]]
		assert engine == connector.get_engine()
		assert str(engine.url) == app.config['SQLALCHEMY_BINDS'][bind]

	# do the models have the correct engines?
	assert db.metadata.tables['foo'].info['bind_key'] == 'foo'
	assert db.metadata.tables['bar'].info['bind_key'] == 'bar'
	assert db.metadata.tables['baz'].info.get('bind_key') is None

	# see the tables created in an engine
	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app, 'foo'))
	assert len(metadata.tables) == 1
	assert 'foo' in metadata.tables

	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app, 'bar'))
	assert len(metadata.tables) == 1
	assert 'bar' in metadata.tables

	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app))
	assert len(metadata.tables) == 1
	assert 'baz' in metadata.tables

	# do the session have the right binds set?
	assert db.get_binds(app) == {
		Foo.__table__: db.get_engine(app, 'foo'),
		Bar.__table__: db.get_engine(app, 'bar'),
		Baz.__table__: db.get_engine(app, None)
	}


def test_basic_binds_mapped_to_same_file(app, db):
	binds = {
		'foo': 'sqlite:///:memory:',
		'bar': 'sqlite:///:memory:'
	}
	app.config['SQLALCHEMY_BINDS'] = binds

	class Foo(db.Model):
		__bind_key__ = 'foo'
		__table_args__ = {"info": {"bind_key": "foo"}}
		id = db.Column(db.Integer, primary_key=True)

	class Bar(db.Model):
		__bind_key__ = 'bar'
		id = db.Column(db.Integer, primary_key=True)

	class Baz(db.Model):
		id = db.Column(db.Integer, primary_key=True)

	db.create_all()

	# simple way to check if the engines are looked up properly
	assert db.get_engine(app, None) == db.engine
	assert len(app.extensions['sqlalchemy'].connectors) == 1
	for bind in 'foo', 'bar':
		engine = db.get_engine(app, bind)
		connector = app.extensions['sqlalchemy'].connectors.get(binds[bind])
		assert connector
		assert engine == connector.get_engine()
		assert str(engine.url) == app.config['SQLALCHEMY_BINDS'][bind]

	# do the models have the correct engines?
	assert db.metadata.tables['foo'].info['bind_key'] == 'foo'
	assert db.metadata.tables['bar'].info['bind_key'] == 'bar'
	assert db.metadata.tables['baz'].info.get('bind_key') is None

	# see the tables created in an engine
	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app, 'foo'))
	assert len(metadata.tables) == 3
	assert 'foo' in metadata.tables

	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app, 'bar'))
	assert len(metadata.tables) == 3
	assert 'bar' in metadata.tables

	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app))
	assert len(metadata.tables) == 3
	assert 'baz' in metadata.tables

	# do the session have the right binds set?
	assert db.get_binds(app) == {
		Foo.__table__: db.get_engine(app, 'foo'),
		Bar.__table__: db.get_engine(app, 'bar'),
		Baz.__table__: db.get_engine(app, None)
	}


def test_basic_binds_with_multi_dbs(app, db):
	binds = {
		'foo': sqlite_connection_factory(),
		'bar': sqlite_connection_factory()
	}
	app.config['SQLALCHEMY_BINDS'] = binds

	class Foo(db.Model):
		__bind_key__ = 'foo'
		__table_args__ = {"info": {"bind_key": "foo"}}
		id = db.Column(db.Integer, primary_key=True)

	class Bar(db.Model):
		__bind_key__ = 'bar'
		id = db.Column(db.Integer, primary_key=True)

	class Baz(db.Model):
		id = db.Column(db.Integer, primary_key=True)

	db.create_all()

	# simple way to check if the engines are looked up properly
	assert db.get_engine(app, None) == db.engine
	assert len(app.extensions['sqlalchemy'].connectors) == 3
	for bind in 'foo', 'bar':
		engine = db.get_engine(app, bind)
		connector = app.extensions['sqlalchemy'].connectors.get(binds[bind])
		assert connector
		assert engine == connector.get_engine()
		assert str(engine.url) == app.config['SQLALCHEMY_BINDS'][bind]

	# do the models have the correct engines?
	assert db.metadata.tables['foo'].info['bind_key'] == 'foo'
	assert db.metadata.tables['bar'].info['bind_key'] == 'bar'
	assert db.metadata.tables['baz'].info.get('bind_key') is None

	# see the tables created in an engine
	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app, 'foo'))
	assert len(metadata.tables) == 1
	assert 'foo' in metadata.tables

	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app, 'bar'))
	assert len(metadata.tables) == 1
	assert 'bar' in metadata.tables

	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app))
	assert len(metadata.tables) == 1
	assert 'baz' in metadata.tables

	# do the session have the right binds set?
	assert db.get_binds(app) == {
		Foo.__table__: db.get_engine(app, 'foo'),
		Bar.__table__: db.get_engine(app, 'bar'),
		Baz.__table__: db.get_engine(app, None)
	}


def test_abstract_binds(app, db):
	app.config['SQLALCHEMY_BINDS'] = {
		'foo': 'sqlite://'
	}

	class AbstractFooBoundModel(db.Model):
		__abstract__ = True
		__bind_key__ = 'foo'

	class FooBoundModel(AbstractFooBoundModel):
		id = db.Column(db.Integer, primary_key=True)

	db.create_all()

	# does the model have the correct engines?
	assert db.metadata.tables['foo_bound_model'].info['bind_key'] == 'foo'

	# see the tables created in an engine
	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app, 'foo'))
	assert len(metadata.tables) == 1
	assert 'foo_bound_model' in metadata.tables


def test_connector_cache(app):
	db = fsa.SQLAlchemy()
	db.init_app(app)

	with app.app_context():
		db.get_engine()

	assert len(fsa.get_state(app).connectors) == 1
	connector = fsa.get_state(app).connectors['sqlite:///:memory:']
	assert connector._app is app


def test_polymorphic_bind(app, db):
	bind_key = 'polymorphic_bind_key'

	app.config['SQLALCHEMY_BINDS'] = {
		bind_key: 'sqlite:///:memory',
	}

	class Base(db.Model):
		__bind_key__ = bind_key

		__tablename__ = 'base'

		id = db.Column(db.Integer, primary_key=True)

		p_type = db.Column(db.String(50))

		__mapper_args__ = {
			'polymorphic_identity': 'base',
			'polymorphic_on': p_type
		}

	class Child1(Base):
		child_1_data = db.Column(db.String(50))
		__mapper_args__ = {
			'polymorphic_identity': 'child_1',
		}

	assert Base.__table__.info['bind_key'] == bind_key
	assert Child1.__table__.info['bind_key'] == bind_key


_current_tenant = None


def _dynamic_uri(binds, bind):
	global _current_tenant
	return binds[bind][_current_tenant]


def test_dynamic_runtime_binds(app, db):
	global _current_tenant
	_current_tenant = 'tenant1'

	binds = {
		'foo': {
			'tenant1': sqlite_connection_factory(),
			'tenant2': sqlite_connection_factory()
		},
		'bar': {
			'tenant1': sqlite_connection_factory(),
			'tenant2': sqlite_connection_factory()
		},
		'baz': sqlite_connection_factory()
	}

	app.config['SQLALCHEMY_BINDS'] = {
		'foo': lambda: _dynamic_uri(binds, 'foo'),
		'bar': lambda: _dynamic_uri(binds, 'bar'),
		'baz': binds['baz']
	}

	class Foo(db.Model):
		__bind_key__ = 'foo'
		id = db.Column(db.Integer, primary_key=True)

	class Bar(db.Model):
		__bind_key__ = 'bar'
		id = db.Column(db.Integer, primary_key=True)

	class Baz(db.Model):
		__bind_key__ = 'baz'
		id = db.Column(db.Integer, primary_key=True)

	for tenant in 'tenant1', 'tenant2':
		_current_tenant = tenant
		db.create_all()
		for bind in binds.keys():
			engine = db.get_engine(app, bind)
			if bind == 'baz':
				connector = app.extensions['sqlalchemy'].connectors.get(binds[bind])
				assert connector
				assert engine == connector.get_engine()
				assert str(engine.url) == app.config['SQLALCHEMY_BINDS'][bind]
				assert str(engine.url) == binds[bind]
			else:
				connector = app.extensions['sqlalchemy'].connectors.get(binds[bind][tenant])
				assert connector
				assert engine == connector.get_engine()
				assert str(engine.url) == app.config['SQLALCHEMY_BINDS'][bind]()
				assert str(engine.url) == binds[bind][tenant]

	assert len(app.extensions['sqlalchemy'].connectors) == 6  # 2 foo, 2 bar, baz and memory

	# do the models have the correct engines?
	assert db.metadata.tables['foo'].info['bind_key'] == 'foo'
	assert db.metadata.tables['bar'].info['bind_key'] == 'bar'
	assert db.metadata.tables['baz'].info['bind_key'] == 'baz'

	# see the tables created in an engine
	metadata = db.MetaData()
	stop_on()
	metadata.reflect(bind=db.get_engine(app, 'foo'))
	assert len(metadata.tables) == 1
	assert 'foo' in metadata.tables

	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app, 'bar'))
	assert len(metadata.tables) == 1
	assert 'bar' in metadata.tables

	metadata = db.MetaData()
	metadata.reflect(bind=db.get_engine(app, 'baz'))
	assert len(metadata.tables) == 1
	assert 'baz' in metadata.tables

	# do the session have the right binds set?
	assert db.get_binds(app) == {
		Foo.__table__: db.get_engine(app, 'foo'),
		Bar.__table__: db.get_engine(app, 'bar'),
		Baz.__table__: db.get_engine(app, 'baz')
	}
