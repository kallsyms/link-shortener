from flask import Flask, request, abort, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import datetime
import os
import string
import random
try:
    # py3
    from urllib.parse import urljoin
except ModuleNotFoundError:
    # py2
    from urlparse import urljoin

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

db = SQLAlchemy(app)

# ID generation
rand_charset = list(set(string.ascii_letters + string.digits) - set(['0', 'O', '1', 'l', 'I']))
# We use gfycat's lists and ID generation format
readable_adjs = open('adjectives').read().splitlines()
readable_animals = open('animals').read().splitlines()

def random_id(length=8):
    return ''.join(random.choice(rand_charset) for _ in range(length))

def readable_id():
    return random.choice(readable_adjs).capitalize() + random.choice(readable_animals).capitalize()

# Models
class Link(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    target = db.Column(db.Text, nullable=False)
    creation_date = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    creator_ip = db.Column(db.String(64), nullable=False)

# Routes
@app.route('/')
def usage():
    return render_template_string("""
Usage: {{ request.host }}/new/{id_type}/{url}

id_type is one of rand|random, readable, or a static id.
url is the target url.
""")

@app.route('/new/<id_type>/<path:target_url>')
def new_link(id_type, target_url):
    id_type = id_type.lower()

    l = Link(target=target_url, creator_ip=request.remote_addr)

    # Generate random ids until one with the same name isn't found.
    # This is basically always just going to be 1 interation.
    while True:
        if id_type in ['rand', 'random']:
            l.id = random_id()
        elif id_type in ['readable']:
            l.id = readable_id()
        else:
            l.id = id_type

        try:
            db.session.add(l)
            db.session.commit()
            break
        except IntegrityError:
            db.session.rollback()
            if id_type not in ['rand', 'random', 'readable']:
                return abort(409, "Specified ID already in use")

    return urljoin(request.host_url, l.id)

@app.route('/<link_id>')
def get_link(link_id):
    l = Link.query.get_or_404(link_id)
    r = redirect(l.target)
    r.headers['Referrer-Policy'] = 'no-referrer'
    return r

if __name__ == "__main__":
    db.create_all()
    app.run(host="0.0.0.0")
