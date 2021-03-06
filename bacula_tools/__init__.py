'''Bacula configuration database stuff: common routines, credentials, etc.
Configuration is at the *end* of this file.'''

from __future__ import print_function
import re, shlex, sys, os

_INTERNED = [
    'Append', 'Available', 'Catalog', 'Cleaning', 'Error', 'Full', 'Purged', 'Recycle', 'Used',
    'actiononpurge', 'address', 'autoprune', 'autoprune', 'bacula_enabled', 'begin', 'catalog_id',
    'catalogacl', 'catalogfiles', 'catalogs', 'cleaningprefix', 'client', 'clientacl', 'clients',
    'commandacl', 'console', 'consoles', 'data', 'db', 'dbaddress', 'dbname', 'dbpassword',
    'dbport', 'dbsocket', 'dbuser', 'diraddresses', 'director', 'director_id', 'director_name',
    'directors', 'dirid', 'enabled', 'end', 'entries', 'exclude', 'excludes', 'failure',
    'fd_connect_timeout', 'fdaddress', 'fdaddresses', 'fdport', 'fdsourceaddress', 'file_retention',
    'filedaemon', 'fileretention', 'fileset', 'fileset_files', 'filesetacl', 'filesets',
    'heartbeatinterval', 'hostid', 'hostname', 'hostnames', 'hosts', 'id',
    'ignorechanges', 'includes', 'job_retention', 'jobacl', 'jobretention', 'labelformat',
    'lastupdated', 'maximumconcurrentjobs', 'maximumbandwidthperjob', 'maximumconcurrentjobs',
    'maximumconsoleconnections', 'maximumconsoleconnections', 'maximumnetworkbuffersize',
    'maximumvolumebytes', 'maximumvolumefiles', 'maximumvolumejobs', 'maximumvolumes', 'message_id',
    'messages', 'monitor', 'name', 'no', 'notes', 'option', 'options', 'os', 'owners', 'password',
    'piddirectory', 'pkiencryption', 'pkikeypair', 'pkimasterkey', 'pkisignatures', 'pool',
    'poolacl', 'pools', 'pooltype', 'port', 'primary_dir', 'priority', 'purgeoldestvolume',
    'queryfile', 'recycle', 'recyclecurrentvolume', 'recycleoldestvolume', 'recyclepool', 'rows',
    'run', 'schedule', 'schedule_time', 'scheduleacl', 'schedules', 'scratchpool', 'sdport',
    'scripts_directory', 'sd_connect_timeout', 'sdconnecttimeout', 'service', 'services',
    'sourceaddress', 'statistics_retention', 'storage', 'storageacl', 'storagepassword',
    'storageserver', 'storageserveraddress', 'timespan', 'user', 'usevolumeonce', 'verid',
    'volumeretention', 'volumeuseduration', 'vssenabled', 'whereacl', 'workingdirectory', 'yes',
    'device', 'mediatype', 'autochanger', 'allowcompression', 'type', 'level', 'differentialpool_id',
    'fileset_id', 'fullpool_id', 'incrementalpool_id', 'client_id', 'messages_id', 'pool_id',
    'schedule_id', 'job_id', 'rescheduletimes', 'accurate', 'allowduplicatejobs',
    'allowmixedpriority', 'cancellowerlevelduplicates', 'cancelqueuedduplicates',
    'cancelrunningduplicates', 'prefermountedvolumes', 'prefixlinks', 'prunefiles', 'prunejobs',
    'prunevolumes', 'rerunfailedlevels', 'rescheduleonerror', 'spoolattributes', 'spooldata',
    'writepartafterjob', 'addprefix', 'addsuffix', 'base', 'bootstrap', 'differentialmaxwaittime',
    'idmaxwaittime', 'incrementalmaxruntime', 'maxfullinterval', 'maximumbandwidth',
    'maxrunschedtime', 'maxruntime', 'maxstartdelay', 'maxwaittime', 'regexwhere',
    'rescheduleinterval', 'spoolsize', 'stripprefix', 'verifyjob', 'where', 'writebootstrap',
    'replace', 'jobdef', 'jobs', 'job', 'storage_id', 'command', 'runsonsuccess', 'runsonfailure',
    'runsonclient', 'runswhen', 'failjobonerror', 'scripts', 'message', 'script_id', 'jobdefs'
    ]

for w in _INTERNED: locals()[w.upper()] = w

STATUS = [FULL, USED, APPEND, CLEANING, ERROR, PURGED, RECYCLE, AVAILABLE]

# Bacula CONFIG DB bits that are less easily interned
BACULA_DIR_PORT = 9101
BACULA_FD_PORT = 9102
BACULA_SD_PORT = 9103

WORKING_DIR = {
    'Linux': "/var/lib/bacula",
    'OSX': "/var/db/bacula",
    'FreeBSD': "/var/db/bacula",
    'Windows': "/bacula/working",
    }

def parser(string, output=print):
    '''parse a string out into top-level resource items and pass them off to the relevant classes.'''
    # strip out comments, and turn semi-colons into newlines
    # NB: if you have embedded semi-colons in any values (e.g. runscripts),
    # You will lose here.
    RB = '}'
    LB = '{'
    file_re = re.compile(r'\s@(.*)\s+', re.MULTILINE)
    comment_re = re.compile(r'#.*', re.MULTILINE)
    semicolon_re = re.compile(r';', re.MULTILINE)
    blankline_re = re.compile(r'^\s+$', re.MULTILINE)
    string = blankline_re.sub('', comment_re.sub('', string)) # Strip the comments out

    groups = file_re.search(string)
    while groups:
        filename = groups.group(1)
        string = blankline_re.sub('', string.replace(groups.group(),
                                                     '\n' + comment_re.sub('', open(filename).read()) + '\n'))
        groups = file_re.search(string)

    string = semicolon_re.sub('\n',  string).replace('\\\n','').replace('\n\n', '\n')
    parts = string.split(RB)
    parsed = []
    while parts:
        current = parts.pop(0)
        while current.count(RB) < (current.count(LB) - 1): current += RB + parts.pop(0)
        try: name, body = current.split(LB,1)
        except:
            output(current)
            raise
        name = name.strip().lower()
        try:
            obj = _DISPATCHER[name]()
            parsed.append(obj)
            result = obj.parse_string(body.strip())
            output(result)
        except Exception as e:
            msg = '%s: Unable to handle %s at this time:\n%s' % (name.capitalize(), e,body.strip())
            output(msg)
            raise
        while parts and parts[0] == '\n': del parts[0]
    return parsed
    

def debug_print(msg, *args):
    global DEBUG
    if DEBUG: print(msg % args, file=sys.stderr)
    sys.stderr.flush()
    return

def set_debug(value):
    global DEBUG
    DEBUG = value
    return

set_debug(os.environ.get('DEBUG', False))

def set_bool_values(key, value, obj, okey):
    if value in ['1','y','yes','Y','YES','Yes','t','T','true','True','TRUE']:
        if 1 ^ obj[okey]: obj._set(okey, 1)
        return 
    if value in ['0','n','no','N','NO','No','f','F','false','False','FALSE']:
        if 0 ^ obj[okey]: obj._set(okey, 0)
        return
    raise Exception('%s takes a boolean value, and I was unable to translate %s' % (key, value))

# Configuration block

# MySQL credentials for the Bacula configuration database. They should be
# overridden in one of the configuration files (see below for the config
# files that are checked).
MYSQL_DB = 'OVERRIDE ME'
MYSQL_HOST = 'OVERRIDE ME'
MYSQL_USER = 'OVERRIDE ME'
MYSQL_PASS = 'OVERRIDE ME'

# These rules will be used to determine what fileset(s) and schedule(s)
# will be applied to new jobs that are generated in an automated fashion.
# Currently only used by webconfig.  Only HOSTNAME and OS are currently
# valid values.

# The rules in here are examples only!

# [variable, regex, fileset, schedule]
_guessing_rules = [
    (HOSTNAME, re.compile('origin'), 'SetOnHostGZIP', 'CustomHost'),
    (HOSTNAME, re.compile('origin'), 'XferLogs', 'FtpHosts'),
    (HOSTNAME, re.compile(r'\.ocs\.'), 'SetOnHostGZIP', 'Weekly'),
    (OS, re.compile(r'Windows'), 'WinFullGZIP', 'Weekly'),
    ]
_default_rules = [('Daily', 'FullUnixGZIP')]

# Where we keep
BACULADATADIR = '/data/bacula'


# Now that we've set all of the default initial values, we'll load and
# parse config files, updating the environment from them.
CUSTOM_LIST = ['/etc/bacula/bacula.conf',
               '/usr/local/etc/bacula/bacula.conf',
               '/usr/local/etc/bacula.conf',
               os.path.join(os.environ['HOME'], '.bacula.conf')
               ]
for filename in CUSTOM_LIST:
    if not os.access(filename, os.R_OK): continue
    exec( open(filename).read(), locals(), locals())

from bacula_config import *
from util import *
from schedule import Schedule
from fileset import Fileset
from messages import Messages
from director import Director
from catalog import Catalog
from console import Console
from client import Client
from pool import Pool
from storage import Storage
from job import Job, JobDef
from scripts import Script

import util

_DISPATCHER = {
    FILESET: Fileset,
    SCHEDULE: Schedule,
    MESSAGES: Messages,
    MESSAGE: Messages,
    DIRECTOR: Director,
    CATALOG.lower(): Catalog,
    CONSOLE: Console,
    CLIENT: Client,
    FILEDAEMON: Client,
    POOL: Pool,
    STORAGE: Storage,
    JOB: Job,
    JOBDEF: JobDef,
    JOBDEFS: JobDef,
    }
