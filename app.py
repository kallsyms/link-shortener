from flask import Flask, request, abort, render_template_string, redirect
from flask_sqlalchemy import SQLAlchemy
from netaddr import IPAddress
from sqlalchemy.exc import IntegrityError
import datetime
import os
import string
import random
try:
    # py3
    from urllib.parse import urljoin, urlparse
except ImportError:
    # py2
    from urlparse import urljoin, urlparse

app = Flask(__name__)
app.config.from_object('config.AppConfig')

if type(app.config['ADMIN_IPS']) not in [list, tuple]:
    app.config['ADMIN_IPS'] = [app.config['ADMIN_IPS']]

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
@app.route('/new/<id_type>')
def new_link(id_type):
    target_url = request.args['url']

    if urlparse(target_url).netloc == '':
        target_url = '//' + target_url

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
            return urljoin('http://' + app.config['SERVER_NAME'], l.id)
        except IntegrityError:
            db.session.rollback()
            if id_type not in ['rand', 'random', 'readable']:
                return abort(409, "Specified ID already in use")

@app.route('/delete/<link_id>')
def delete(link_id):
    if not any(IPAddress(request.remote_addr) in net for net in app.config['ADMIN_IPS']):
        abort(403)

    l = Link.query.get_or_404(link_id)

    db.session.delete(l)
    db.session.commit()

    return ''

@app.route('/<link_id>')
def get_link(link_id):
    l = Link.query.get_or_404(link_id)
    r = redirect(l.target)
    r.headers['Referrer-Policy'] = 'no-referrer'
    return r

@app.route('/')
def usage():
    if app.config.get('ENABLE_SUBDOMAINS') and request.host.endswith(app.config['SERVER_NAME']):
        link_id = request.host[:-len(app.config['SERVER_NAME'])].rstrip('.')
        if len(link_id) > 0:
            return get_link(link_id)

    return render_template_string("""
USAGE
<br/><br/>

Create: {{ config.server_name }}/new/{id_type}?url={url}
<br/><br/>

id_type is one of rand|random, readable, or a static id.<br/>
url is the target url.<br/>

<br/>
<br/>


Delete: {{ config.server_name }}/delete/{id}
<br/><br/>

id is the name of the short link to be deleted.<br/>
NOTE: Only the IPs defined in config.admin_ips can delete short links.
""")

if __name__ == "__main__":
    db.create_all()
    app.run(host="0.0.0.0")
