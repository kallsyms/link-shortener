import netaddr

class AppConfig(object):
    ENABLE_SUBDOMAINS = True
    SERVER_NAME = 'localhost:5000'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    ADMIN_IPS = netaddr.ip.IPV4_PRIVATE
