"""

Weather Station

An API for a microcontroller-based weather station to record data to, and a
basic web app for reporting on that data

"""
import os
import math
import random
from datetime import date, datetime, timedelta, time, timezone
import sqlite3

import click
import pygal
from pygal.style import DefaultStyle
from flask import g, Flask, request, render_template
from flask_restful import reqparse, abort, Resource, Api
from flask_restful import fields, inputs, marshal_with
from marshmallow import Schema, ValidationError, post_load, pre_dump
from marshmallow import fields as mfields

from _namedict import namedict


# TODO: Would like to maybe have multiple options for configuration?
try:
    DATABASE_FILE_PATH = os.environ['WS_DATABASE_FILE_PATH']
except KeyError:
    DATABASE_FILE_PATH = ':memory:'


try:
    USE_FIXTURES = os.environ['WS_USE_FIXTURES'] in ['true', "True", "TRUE", 1, 'Y', 'y']
except KeyError:
    USE_FIXTURES = False


app = Flask(__name__)


#
# Database Management & Querying
#


@app.cli.command("update-database")
@click.argument("database_path")
def update_schema(database_path):
    db = get_database()
    if not initial_schema_created(db):
        create_schema(db)


def initial_schema_created(db):
    try:
        cursor = db.cursor()
        cursor.execute("SELECT 1 FROM temperature WHERE 1=2")
        cursor.close()
        return True
    except sqlite3.OperationalError:
        return False


def database_empty(db):
    try:
        cursor = db.cursor()
        cursor.execute("SELECT count(*) as num_temps FROM temperature")
        result = cursor.fetchone()
        cursor.close()
        return result.num_temps == 0
    except sqlite3.OperationalError:
        return False


def create_schema(db):
    """
    Create the base schema for the database.
    """
    cursor = db.cursor()
    cursor.execute(
        "CREATE TABLE temperature (when_recorded timestamp, temperature real, resolution integer)"
    )
    cursor.execute(
        "CREATE TABLE daily_temperature (day date, high real, low real, mean real, median real, high_recorded timestamp, low_recorded timestamp, median_recorded timestamp)"
    )
    cursor.execute(
        "CREATE TABLE pressure (when_recorded timestamp, pressure real, sensor_temperature real, resolution integer)"
    )
    cursor.execute(
        "CREATE TABLE daily_pressure (day date, high real, low real, mean real, median real, high_recorded timestamp, low_recorded timestamp, median_recorded timestamp)"
    )
    db.commit()
    cursor.close()


def make_dicts(cursor, row):
    return namedict(
        (cursor.description[idx][0], value)
        for idx, value in enumerate(row)
    )


def get_database():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(
            DATABASE_FILE_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES
        )
        db.row_factory = make_dicts

        if DATABASE_FILE_PATH == ":memory:":
            # In-memory database - going to need to create the schema
            # For file databases, creating and updating the schema
            # is assumed to be handled outside the app for efficiency
            create_schema(db)

        if USE_FIXTURES and initial_schema_created(db) and database_empty(db):
            generate_fixtures(db)
    return db


def generate_fixtures(db):
    from fixtures import temperatures as _temperatures
    from fixtures import daily_temperatures as _daily_temperatures
    from fixtures import pressures as _pressures
    from fixtures import daily_pressures as _daily_pressures
    cursor = db.cursor()
    for fixture in _temperatures:
        db.execute(
            (
                "INSERT INTO temperature (when_recorded, temperature, resolution)"
                " values (?, ?, ?)"
            ),
            (
                fixture['when_recorded'],
                fixture['temperature'],
                fixture['resolution'],
            )
        )
    for fixture in _daily_temperatures:
        high_minutes = random.randrange(15, 1440, 15)
        low_minutes = random.randrange(15, 1440, 15)
        median_minutes = random.randrange(15, 1440, 15)
        db.execute(
            (
                "INSERT INTO daily_temperature (day, high, low, mean, median, high_recorded, low_recorded, median_recorded)"
                " values (?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            (
                fixture['day'],
                fixture['high'],
                fixture['low'],
                fixture['mean'],
                fixture['median'],
                datetime.combine(fixture['day'], time(hour=high_minutes//60, minute=high_minutes%60)),
                datetime.combine(fixture['day'], time(hour=low_minutes//60, minute=low_minutes%60)),
                datetime.combine(fixture['day'], time(hour=median_minutes//60, minute=median_minutes%60)),
            )
        )
    for fixture in _pressures:
        db.execute(
            (
                "INSERT INTO pressure (when_recorded, pressure, resolution)"
                " values (?, ?, ?)"
            ),
            (
                fixture['when_recorded'],
                fixture['pressure'],
                fixture['resolution'],
            )
        )
    for fixture in _daily_pressures:
        high_minutes = random.randrange(15, 1440, 15)
        low_minutes = random.randrange(15, 1440, 15)
        median_minutes = random.randrange(15, 1440, 15)
        db.execute(
            (
                "INSERT INTO daily_pressure (day, high, low, mean, median, high_recorded, low_recorded, median_recorded)"
                " values (?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            (
                fixture['day'],
                fixture['high'],
                fixture['low'],
                fixture['mean'],
                fixture['median'],
                datetime.combine(fixture['day'], time(hour=high_minutes//60, minute=high_minutes%60)),
                datetime.combine(fixture['day'], time(hour=low_minutes//60, minute=low_minutes%60)),
                datetime.combine(fixture['day'], time(hour=median_minutes//60, minute=median_minutes%60)),
            )
        )
    db.commit()
    cursor.close()


def query_database(query, args=(), one=False):
    cursor = get_database().execute(query, args)
    rv = cursor.fetchall()
    cursor.close()
    return (rv[0] if rv else None) if one else rv


def perform_insert(table, data):
    db = get_database()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO {} ({}) VALUES ({})".format(
            table,
            ", ".join(data.keys()),
            ", ".join(["?"] * len(data))
        ),
        list(data.values())
    )
    db.commit()
    id = cursor.lastrowid
    cursor.close()
    return id


def perform_update(table, data, constraint_field, constraint_value):
    db = get_database()
    cursor = db.cursor()
    values = list(data.values())
    values.append(constraint_value)
    cursor.execute(
        "UPDATE {} SET {} WHERE {} = ?".format(
            table,
            ", ".join(["{} = ?".format(f) for f in data]),
            constraint_field
        ),
        values
    )
    db.commit()
    id = cursor.lastrowid
    cursor.close()
    return id


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


#
# Web app
#

chart_style = DefaultStyle()
chart_style.background = "transparent"
chart_style.foreground = "#999"
chart_style.guide_stroke_dasharray = '1, 2'
chart_style.major_guide_stroke_dasharray = '4, 2'
chart_style.colors = ('#ff0066', '#dd99ff', '#1a75ff')


def create_chart(title, x_labels, series, **kwargs):
    chart = pygal.Line(
        height=250,
        style=chart_style,
        dots_size=4,
        stroke_style={'width': 3},
        x_label_rotation=90,
        **kwargs
    )
    chart.title = title
    chart.show_legend = False
    chart.x_labels = x_labels
    for s in series:
        if isinstance(s, dict):
            chart.add(**s)
        else:
            chart.add(*s)
    return chart


@app.route("/")
def current_status():
    temperature = query_database(
        "SELECT rowid as id, when_recorded, temperature, resolution" \
        " from temperature order by when_recorded desc limit 1",
        one=True
    )
    pressure = query_database(
        "SELECT rowid as id, when_recorded, pressure, sensor_temperature, resolution" \
        " from pressure order by when_recorded desc limit 1",
        one=True
    )

    conditional = request.if_modified_since
    if conditional:
        if not (
            conditional < temperature.when_recorded.replace(tzinfo=timezone.utc) and
            conditional < pressure.when_recorded.replace(tzinfo=timezone.utc)
        ):
            return "", 304

    now = datetime.utcnow().replace(microsecond=0, second=0)
    minute_delta = (int(math.floor(now.minute / 15) * 15)) - now.minute
    now = now + timedelta(minutes=minute_delta)

    # Temperature chart
    temperature_24 = query_database(
        "SELECT rowid as id, when_recorded, temperature, resolution" \
        " from temperature" \
        " where when_recorded >= ?" \
        " order by when_recorded asc",
        (now - timedelta(hours=24),)
    )
    last_24_hours_temp = create_chart(
        "Temperature °C (last 24 hours)",
        x_labels=["{:%H:%M}".format(t.when_recorded) for t in temperature_24],
        series=(
            ('Temperature', [t.temperature for t in temperature_24]),
        ),
        x_labels_major_every=4,
        show_minor_x_labels=False,
        value_formatter= lambda x: "%.1f°C" % x,
    )

    # Pressure chart
    pressure_24 = query_database(
        "SELECT rowid as id, when_recorded, pressure, resolution" \
        " from pressure" \
        " where when_recorded >= ?" \
        " order by when_recorded asc",
        (now - timedelta(hours=24),)
    )
    last_24_hours_pressure = create_chart(
        "Pressure hPa (last 24 hours)",
        x_labels=["{:%H:%M}".format(p.when_recorded) for p in pressure_24],
        series=(
            ('Pressure', [round(p.pressure * 10, 2) for p in pressure_24]),
        ),
        x_labels_major_every=4,
        show_minor_x_labels=False,
        value_formatter= lambda x: "%.1f" % x,
    )

    # Daily Temperature chart
    temperature_daily = query_database(
        "SELECT rowid as id, day, high, low, mean, median, high_recorded, low_recorded, median_recorded" \
        " from daily_temperature" \
        " where day >= ?" \
        " order by day asc",
        (date.today() - timedelta(days=30),)
    )
    last_30_days_temp = create_chart(
        "Temperature °C (last 30 days)",
        x_labels=["{:%d/%m}".format(t.day) for t in temperature_daily],
        series=(
            {
                'title': 'High',
                'values': [{'value': t.high, 'label': "Recorded @ {:%H:%M}".format(t.high_recorded)} for t in temperature_daily]
            },
            {
                'title': 'Median',
                'values': [{'value': t.median, 'label': "Recorded @ {:%H:%M}".format(t.median_recorded)} for t in temperature_daily],
                'stroke_style': {'width': 4, 'dasharray': '5, 2'}
            },
            {
                'title': 'Low',
                'values': [{'value': t.low, 'label': "Recorded @ {:%H:%M}".format(t.low_recorded)} for t in temperature_daily]
            }
        ),
        x_labels_major_every=1,
        show_minor_x_labels=False,
        value_formatter= lambda x: "%.1f°C" % x,
    )

    # Daily Pressure chart
    pressure_daily = query_database(
        "SELECT rowid as id, day, high, low, mean, median, high_recorded, low_recorded, median_recorded" \
        " from daily_pressure" \
        " where day >= ?" \
        " order by day asc",
        (date.today() - timedelta(days=30),)
    )
    last_30_days_pressure = create_chart(
        "Pressure hPa (last 30 days)",
        x_labels=["{:%d/%m}".format(t.day) for t in pressure_daily],
        series=(
            {
                'title': 'High',
                'values': [{'value': t.high * 10, 'label': "Recorded @ {:%H:%M}".format(t.high_recorded)}  for t in pressure_daily]
            },
            {
                'title': 'Median',
                'values': [{'value': t.median * 10, 'label': "Recorded @ {:%H:%M}".format(t.median_recorded)} for t in pressure_daily],
                'stroke_style': {'width': 4, 'dasharray': '5, 2'}
            },
            {
                'title': 'Low',
                'values': [{'value': t.low * 10, 'label': "Recorded @ {:%H:%M}".format(t.low_recorded)} for t in pressure_daily]
            }
        ),
        x_labels_major_every=1,
        show_minor_x_labels=False,
        value_formatter= lambda x: "%.1f" % x,
    )

    return render_template(
        "current_status.html",
        temperature=round(temperature.temperature, 1),
        pressure=round(pressure.pressure*10, 1),
        last_updated=temperature.when_recorded,
        last_24_hours_temp=last_24_hours_temp.render_data_uri(),
        last_24_hours_pressure=last_24_hours_pressure.render_data_uri(),
        last_30_days_temp=last_30_days_temp.render_data_uri(),
        last_30_days_pressure=last_30_days_pressure.render_data_uri()
    ), {
        "Cache-Control": "public, max-age=900",
        "Last-Modified": "{:%a, %d %b %Y %H:%M:%S GMT}".format(
            temperature.when_recorded
        )
    }


#
# REST API
#


api = Api(app)


class IntervalQueryParametersSchema(Schema):
    before = mfields.DateTime()
    after = mfields.DateTime()
    exactly = mfields.DateTime()

interval_query_schema = IntervalQueryParametersSchema()


class DailyQueryParametersSchema(Schema):
    before = mfields.Date()
    after = mfields.Date()
    exactly = mfields.Date()

daily_query_schema = DailyQueryParametersSchema()


def parse_query(schema):
    try:
        return schema.load(request.args)
    except ValidationError as error:
        abort(400, message="Invalid query", errors=error.messages)


def load_request_body(schema, **kwargs):
    try:
        return schema.load(request.json, **kwargs)
    except ValidationError as error:
        abort(400, message="Invalid request body", errors=error.messages)


def add_date_criteria_to_query(query, date_field, args, query_args):
    if 'exactly' in args:
        query = query + " where {} = ?".format(date_field)
        query_args.append(args['exactly'])
    elif 'before' in args or 'after' in args:
        query = query + " where 1=1"
        if 'before' in args:
            query = query + " and {} <= ?".format(date_field)
            query_args.append(args['before'])
        if 'after' in args:
            query = query + " and {} >= ?".format(date_field)
            query_args.append(args['after'])
    return query, query_args


def normalise_for_resolution(data):
    resolution = data['resolution']
    when = data['when_recorded']
    when_minute = when.replace(microsecond=0, second=0)
    minute_delta = (int(round(when_minute.minute / resolution) * resolution)) - when_minute.minute
    data['when_recorded'] = when_minute + timedelta(minutes=minute_delta)
    return data


def update_daily_temperatures(day):
    db = get_database()
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    temps = query_database(
        "SELECT * FROM temperature" \
        " WHERE when_recorded >= ? AND when_recorded < ?" \
        " ORDER BY temperature DESC",
        (day_start, day_end)
    )
    if temps:
        high = temps[0]
        low = temps[-1]
        median = temps[len(temps) // 2]
        temp_sum = 0
        for t in temps:
            temp_sum += t['temperature']
        mean = temp_sum / len(temps)

        data = {
            "day": day.date(),
            "high": high["temperature"],
            "low": low["temperature"],
            "mean": mean,
            "median": median["temperature"],
            "high_recorded": high["when_recorded"],
            "low_recorded": low["when_recorded"],
            "median_recorded": median["when_recorded"]
        }

        existing = query_database(
            "SELECT rowid as id FROM daily_temperature" \
            " WHERE day = ?",
            (day.date(),),
            one=True
        )
        if existing:
            perform_update(
                "daily_temperature",
                data,
                "rowid",
                existing['id']
            )
        else:
            perform_insert(
                "daily_temperature",
                data
            )


class TemperatureSchema(Schema):
    id = mfields.Integer(dump_only=True)
    when_recorded = mfields.DateTime()
    temperature = mfields.Float(required=True)
    resolution = mfields.Integer(missing=15) # Consider custom field type with fixed resolutions
    _self = mfields.Url(dump_only=True)

    @pre_dump
    def add_url(self, data, **kwargs):
        data['_self'] = api.url_for(TemperatureDocument, id=data['id'])
        return data

    @post_load
    def make_name_dict(self, data, **kwargs):
        return namedict(data)

    class Meta:
        ordered = True

temperature_document_schema = TemperatureSchema()
temperature_put_schema = TemperatureSchema(only=('temperature',))
temperature_collection_schema = TemperatureSchema(many=True)


class TemperatureDocument(Resource):

    def get(self, id):
        result = query_database(
            "SELECT rowid as id, when_recorded, temperature, resolution from temperature where rowid = ?",
            [id],
            one=True
        )
        if result == None:
            abort(404, message="Temperature with id {} does not exist".format(id))
        return temperature_document_schema.dump(result)

    def put(self, id):
        data = load_request_body(
            temperature_put_schema
        )
        result = query_database(
            "SELECT rowid as id, when_recorded, temperature, resolution from temperature where rowid = ?",
            [id],
            one=True
        )
        if result == None:
            abort(404, message="Temperature with id {} does not exist".format(id))

        perform_update("temperature", data, "rowid", id)
        update_daily_temperatures(result.when_recorded)
        return "", 204

    def delete(self):
        pass


class TemperatureLatest(Resource):

    def get(self):
        result = query_database(
            "SELECT rowid as id, when_recorded, temperature, resolution from temperature order by when_recorded desc limit 1",
            one=True
        )
        if result == None:
            abort(404, message="No temperatures have been recorded")
        return temperature_document_schema.dump(result)


class TemperatureCollection(Resource):

    def get(self):
        args = parse_query(interval_query_schema)
        query = "SELECT rowid as id, when_recorded, temperature, resolution from temperature"
        query, query_args = add_date_criteria_to_query(
            query,
            'when_recorded',
            args,
            []
        )

        return temperature_collection_schema.dump(
            query_database(
                query,
                query_args
            )
        )

    def post(self):
        data = load_request_body(temperature_document_schema)
        if not 'when_recorded' in data:
            data.when_recorded = datetime.utcnow()
        normalise_for_resolution(data)
        existing = query_database(
            "SELECT rowid as id from temperature where when_recorded = ?",
            [data['when_recorded']],
            one=True
        )
        if existing:
            abort(
                409,
                message="A temperature is already recorded for the specified interval",
                location=api.url_for(TemperatureDocument, id=existing['id'])
            )
        id = perform_insert('temperature', data)
        update_daily_temperatures(data['when_recorded'])
        return "", 201, {'Location': api.url_for(TemperatureDocument, id=id)}


api.add_resource(
    TemperatureCollection,
    '/api/temperatures',
    endpoint='temperatures_collection'
)
api.add_resource(
    TemperatureLatest,
    '/api/temperatures/latest',
    endpoint='temperatures_latest'
)
api.add_resource(
    TemperatureDocument,
    '/api/temperatures/<int:id>',
    endpoint='temperatures_document'
)


class DailyTemperatureSchema(Schema):
    id = mfields.Integer(dump_only=True)
    day = mfields.Date()
    high = mfields.Float()
    low = mfields.Float()
    mean = mfields.Float()
    median = mfields.Float()
    high_recorded = mfields.DateTime()
    low_recorded = mfields.DateTime()
    median_recorded = mfields.DateTime()
    _self = mfields.Url(dump_only=True)

    @pre_dump
    def add_url(self, data, **kwargs):
        data['_self'] = api.url_for(DailyTemperatureDocument, id=data['id'])
        return data

    @post_load
    def make_name_dict(self, data, **kwargs):
        return namedict(data)

    class Meta:
        ordered = True

daily_temperature_document_schema = DailyTemperatureSchema()
daily_temperature_collection_schema = DailyTemperatureSchema(many=True)


class DailyTemperatureDocument(Resource):

    def get(self, id):
        result = query_database(
            "SELECT rowid as id, day, high, low, mean, median, high_recorded," \
            " low_recorded, median_recorded from daily_temperature" \
            " where rowid = ?",
            [id],
            one=True
        )
        if result == None:
            abort(404, message="Daily temperature with id {} does not exist".format(id))
        return daily_temperature_document_schema.dump(result)


class DailyTemperatureLatest(Resource):

    def get(self):
        result = query_database(
            "SELECT rowid as id, day, high, low, mean, median, high_recorded," \
            " low_recorded, median_recorded from daily_temperature" \
            " order by day desc limit 1",
            one=True
        )
        if result == None:
            abort(404, message="No temperatures have been recorded")
        return daily_temperature_document_schema.dump(result)


class DailyTemperatureCollection(Resource):

    def get(self):
        args = parse_query(daily_query_schema)
        query = \
            "SELECT rowid as id, day, high, low, mean, median, high_recorded," \
            " low_recorded, median_recorded from daily_temperature"
        query, query_args = add_date_criteria_to_query(
            query,
            'day',
            args,
            []
        )

        return daily_temperature_collection_schema.dump(
            query_database(
                query,
                query_args
            )
        )


api.add_resource(
    DailyTemperatureCollection,
    '/api/dailytemperatures',
    endpoint='daily_temperatures_collection'
)
api.add_resource(
    DailyTemperatureLatest,
    '/api/dailytemperatures/latest',
    endpoint='daily_temperatures_latest'
)
api.add_resource(
    DailyTemperatureDocument,
    '/api/dailytemperatures/<int:id>',
    endpoint='daily_temperatures_document'
)


def update_daily_pressure(day):
    db = get_database()
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    temps = query_database(
        "SELECT * FROM pressure" \
        " WHERE when_recorded >= ? AND when_recorded < ?" \
        " ORDER BY pressure DESC",
        (day_start, day_end)
    )
    if temps:
        high = temps[0]
        low = temps[-1]
        median = temps[len(temps) // 2]
        temp_sum = 0
        for t in temps:
            temp_sum += t['pressure']
        mean = temp_sum / len(temps)

        data = {
            "day": day.date(),
            "high": high["pressure"],
            "low": low["pressure"],
            "mean": mean,
            "median": median["pressure"],
            "high_recorded": high["when_recorded"],
            "low_recorded": low["when_recorded"],
            "median_recorded": median["when_recorded"]
        }

        existing = query_database(
            "SELECT rowid as id FROM daily_pressure" \
            " WHERE day = ?",
            (day.date(),),
            one=True
        )
        if existing:
            perform_update(
                "daily_pressure",
                data,
                "rowid",
                existing['id']
            )
        else:
            perform_insert(
                "daily_pressure",
                data
            )


pressure_fields = {
    'id': fields.Integer,
    'when_recorded': fields.DateTime(dt_format='iso8601'),
    'pressure': fields.Float,
    'sensor_temperature': fields.Float,
    'resolution': fields.Integer,
    'self': fields.Url(endpoint='pressure_document')
}


class PressureSchema(Schema):
    id = mfields.Integer(dump_only=True)
    when_recorded = mfields.DateTime()
    pressure = mfields.Float(required=True)
    sensor_temperature = mfields.Float()
    resolution = mfields.Integer(missing=15) # Consider custom field type with fixed resolutions
    _self = mfields.Url(dump_only=True)

    @pre_dump
    def add_url(self, data, **kwargs):
        data['_self'] = api.url_for(PressureDocument, id=data['id'])
        return data

    @post_load
    def make_name_dict(self, data, **kwargs):
        return namedict(data)

    class Meta:
        ordered = True

pressure_document_schema = PressureSchema()
pressure_put_schema = PressureSchema(only=('pressure','sensor_temperature'))
pressure_collection_schema = PressureSchema(many=True)


class PressureDocument(Resource):

    def get(self, id):
        result = query_database(
            "SELECT rowid as id, when_recorded, pressure, sensor_temperature, resolution from pressure where rowid = ?",
            [id],
            one=True
        )
        if result == None:
            abort(404, message="Pressure with id {} does not exist".format(id))
        return pressure_document_schema.dump(result)

    def put(self, id):
        data = load_request_body(pressure_put_schema, partial=('pressure', 'sensor_temperature'))
        result = query_database(
            "SELECT rowid as id, when_recorded, pressure, sensor_temperature, resolution from pressure where rowid = ?",
            [id],
            one=True
        )
        if result == None:
            abort(404, message="Pressure with id {} does not exist".format(id))

        perform_update("pressure", data, "rowid", id)
        update_daily_pressure(result.when_recorded)
        return "", 204

    def delete(self):
        pass


class PressureLatest(Resource):

    def get(self):
        result = query_database(
            "SELECT rowid as id, when_recorded, pressure, sensor_temperature, resolution from pressure order by when_recorded desc limit 1",
            one=True
        )
        if result == None:
            abort(404, message="No pressure readings have been recorded")
        return pressure_document_schema.dump(result)


class PressureCollection(Resource):

    def get(self):
        args = parse_query(interval_query_schema)
        query = "SELECT rowid as id, when_recorded, pressure, sensor_temperature, resolution from pressure"
        query, query_args = add_date_criteria_to_query(
            query,
            'when_recorded',
            args,
            []
        )

        return pressure_collection_schema.dump(
            query_database(
                query,
                query_args
            )
        )

    def post(self):
        data = load_request_body(pressure_document_schema)
        if not 'when_recorded' in data:
            data.when_recorded = datetime.utcnow()
        normalise_for_resolution(data)
        existing = query_database(
            "SELECT rowid as id from pressure where when_recorded = ?",
            [data['when_recorded']],
            one=True
        )
        if existing:
            abort(
                409,
                message="A pressure is already recorded for the specified interval",
                location=api.url_for(PressureDocument, id=existing['id'])
            )
        id = perform_insert('pressure', data)
        update_daily_pressure(data['when_recorded'])
        return "", 201, {'Location': api.url_for(PressureDocument, id=id)}


api.add_resource(
    PressureCollection,
    '/api/pressure',
    endpoint='pressure_collection'
)
api.add_resource(
    PressureLatest,
    '/api/pressure/latest',
    endpoint='pressure_latest'
)
api.add_resource(
    PressureDocument,
    '/api/pressure/<int:id>',
    endpoint='pressure_document'
)


class DailyPressureSchema(Schema):
    id = mfields.Integer(dump_only=True)
    day = mfields.Date()
    high = mfields.Float()
    low = mfields.Float()
    mean = mfields.Float()
    median = mfields.Float()
    high_recorded = mfields.DateTime()
    low_recorded = mfields.DateTime()
    median_recorded = mfields.DateTime()
    _self = mfields.Url(dump_only=True)

    @pre_dump
    def add_url(self, data, **kwargs):
        data['_self'] = api.url_for(DailyPressureDocument, id=data['id'])
        return data

    @post_load
    def make_name_dict(self, data, **kwargs):
        return namedict(data)

    class Meta:
        ordered = True

daily_pressure_document_schema = DailyPressureSchema()
daily_pressure_collection_schema = DailyPressureSchema(many=True)


class DailyPressureDocument(Resource):

    def get(self, id):
        result = query_database(
            "SELECT rowid as id, day, high, low, mean, median, high_recorded," \
            " low_recorded, median_recorded from daily_pressure" \
            " where rowid = ?",
            [id],
            one=True
        )
        if result == None:
            abort(404, message="Daily pressure with id {} does not exist".format(id))
        return daily_pressure_document_schema.dump(result)


class DailyPressureLatest(Resource):

    def get(self):
        result = query_database(
            "SELECT rowid as id, day, high, low, mean, median, high_recorded," \
            " low_recorded, median_recorded from daily_pressure" \
            " order by day desc limit 1",
            one=True
        )
        if result == None:
            abort(404, message="No pressure readings have been recorded")
        return daily_pressure_document_schema.dump(result)


class DailyPressureCollection(Resource):

    def get(self):
        args = parse_query(daily_query_schema)
        query = \
            "SELECT rowid as id, day, high, low, mean, median, high_recorded," \
            " low_recorded, median_recorded from daily_pressure"
        query, query_args = add_date_criteria_to_query(
            query,
            'day',
            args,
            []
        )

        return daily_pressure_collection_schema.dump(
            query_database(
                query,
                query_args
            )
        )


api.add_resource(
    DailyPressureCollection,
    '/api/dailypressure',
    endpoint='daily_pressure_collection'
)
api.add_resource(
    DailyPressureLatest,
    '/api/dailypressure/latest',
    endpoint='daily_pressure_latest'
)
api.add_resource(
    DailyPressureDocument,
    '/api/dailypressure/<int:id>',
    endpoint='daily_pressure_document'
)
