#!/usr/bin/env python

import os
import sys
import glob
import base64
import socket
import fnmatch
import getpass
import urllib2
import argparse
import datetime
import xml.etree.ElementTree as ET


root_directory = os.path.dirname(os.path.realpath(__file__))
host_nickname = socket.gethostname().split('.')[0]
portals = {
    'portable': 'http://portable.chemsem.com',
    'cloud': 'http://chemsemplus.cloudapp.net'}


def find_files(directory, pattern):
    """thanks, http://stackoverflow.com/a/2186673"""
    for root, dirs, files in os.walk(directory):
        for basename in files:
            if fnmatch.fnmatch(basename, pattern):
                filename = os.path.join(root, basename)
                yield filename


def readable_dir(prospective_dir):
    """thanks, http://stackoverflow.com/q/11415570"""
    if not os.path.isdir(prospective_dir):
        raise argparse.ArgumentTypeError("readable_dir:{0} is not a valid path".format(prospective_dir))
    if os.access(prospective_dir, os.R_OK):
        return prospective_dir
    else:
        raise argparse.ArgumentTypeError("readable_dir:{0} is not a readable dir".format(prospective_dir))


def parse_command_line():
    """Function to

    """

    parser = argparse.ArgumentParser(description='Publish computations to CSI portal',
        formatter_class=argparse.RawTextHelpFormatter)

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--csx-lasthere',
        action='store_true',
        default=True,
        help="""specify upload of most recent CSX in current directory.
This is the default when no other --csx-* arguments given.""")
    group.add_argument('--csx-files',
        nargs='+',
        action='store',
        metavar='FILE-or-STRING',
        help="""specify CSX file(s) to upload through file names,
command line wildcard expansion, or strings for glob
expansion. For example,
  --csx-files job1.csx proj/* 'proj2/*/*'
(default: %(default)s)""")
    group.add_argument('--csx-within',
        action='store',
        type=readable_dir,
        metavar='DIR',
        help="""specify directory within which to recursively seek
CSX files to upload (default: %(default)s)""")

#    group = parser.add_mutually_exclusive_group()
#    group.add_argument('--each-to-pub',
#        metavar='PROJECT_PREFIX',
#        help="""assign each CSX to its own publication (autovivified)(default: %(default)s)""")
#    group.add_argument('--all-to-pub',
#        metavar='PROJECT',
#        help="""assign all CSX to single publication (autovivified) (default: %(default)s)""")

    group = parser.add_argument_group('Portal options')
    # portal username
    group.add_argument('--user',
        action='store',
        default=getpass.getuser(),
        metavar='USER',
        help="""ChemSem portal username (default: %(default)s)""")
    # portal
    group.add_argument('--portal',
        action='store',
        default='cloud',
        choices=portals.keys(),
        help="""ChemSem portal on which to publish (default: %(default)s)""")

    group = parser.add_argument_group('Publication options')
    # publication
    group.add_argument('--publication',
        action='store',
        default="""{pathfromhome}""",
        help="""assignment to CSI publication. Same instructions as
for --title. Choose a plain string or, for instance
'water from {host} on {uploaddatetime}', to assign
all CSX to single publication with that name. Choose,
for instance, 'neverendingproject {num}' to assign
each CSX to its own publication.""")
    # hostname
    group.add_argument('--host',
        action='store',
        default=host_nickname,
        metavar='STRING',
        help="""nickname for data computer (default: %(default)s)""")
    # title
    group.add_argument('--title',
        action='store',
        default="""{host}__{pathfromhome}__{job}""",
        help="""identifier for *you* to distinguish among your QC
records. Supply a string in Python's string.format(),
using plaintext and any placeholders among: host, user, job,
pathfromhome, filemoddatetime, uploaddatetime, and num.
For instance, files:
    johndoe Jun 10 14:22 fakefs/proj1/dft-psivar.csx
    johndoe Jun 10 12:58 fakefs/proj1/nu_water_sp2.csx
    johndoe Jun 10 14:22 fakefs/proj2/dft-psivar.csx
by default, '{host}__{pathfromhome}__{job}', become:
    myMac__linux-psi4-sandbox-fakefs-proj1__dft-psivar
    myMac__linux-psi4-sandbox-fakefs-proj1__nu_water_sp2
    myMac__linux-psi4-sandbox-fakefs-proj2__dft-psivar
while with '{host}__{user}__{pathfromhome}__{filemoddatetime}__{job}__{num}', become:
    myMac__johndoe__sandbox-fakefs-proj1__2015-06-10T14:22:41__dft-psivar__0
    myMac__johndoe__sandbox-fakefs-proj1__2015-06-10T12:58:13__nu_water_sp2__1
    myMac__johndoe__sandbox-fakefs-proj2__2015-06-10T14:22:41__dft-psivar__2
(default: %(default)s)
""")


    return parser.parse_args()

# "main"
args = parse_command_line()

#
# <<<  collect readable CSX files according to cla  >>>
#
readable_csx = []

if args.csx_files:
    direct_to_glob = [f for f in args.csx_files if '*' in f]
    direct_to_files = [f for f in args.csx_files if '*' not in f]

    for fl in direct_to_files:
        if fl.endswith('.csx'):
            if os.access(fl, os.R_OK):
                readable_csx.append(os.path.realpath(fl))
    for spec in direct_to_glob:
        files = glob.glob(os.path.abspath(os.path.expanduser(os.path.expandvars(spec))))
        for fl in files:
            if fl.endswith('.csx'):
                if os.access(fl, os.R_OK):
                    readable_csx.append(fl)
    if not readable_csx:
        print """No readable CSX in globs {0} or files {1}""".format(direct_to_glob, direct_to_files)
        sys.exit()

elif args.csx_within:
    for fl in find_files(args.csx_within, '*.csx'):
        if os.access(fl, os.R_OK):
            readable_csx.append(fl)
    if not readable_csx:
        print """No readable CSX in or below directory {0}""".format(os.path.abspath(args.csx_within))
        sys.exit()

elif args.csx_lasthere:
    try:
        fl = max(glob.iglob(os.path.abspath('./*.csx')), key=os.path.getmtime)
    except ValueError:
        print """No CSX files in current directory"""
        sys.exit()
    else:
        if os.access(fl, os.R_OK):
            readable_csx.append(fl)
    if not readable_csx:
        print """No readable CSX files in current directory"""
        sys.exit()


triplet_store = []
dtupload = datetime.datetime.now()
for num, fl in enumerate(sorted(readable_csx)):
    home = os.path.expanduser('~')
    flwrthome = os.path.relpath(fl, home)
    head, tail = os.path.split(flwrthome)
    flbase, ext = os.path.splitext(tail)
    dtmodified = datetime.datetime.fromtimestamp(os.path.getmtime(fl))

    flproj = args.publication.format(host=args.host,
                                     user=args.user,
                                     pathfromhome='-'.join(head.split(os.sep)),
                                     filemoddatetime=dtmodified.strftime("%Y-%m-%dT%H:%M:%S"),
                                     uploaddatetime=dtupload.strftime("%Y-%m-%dT%H:%M:%S"),
                                     job=flbase,
                                     num=num)
    fltitle = args.title.format(host=args.host,
                                user=args.user,
                                pathfromhome='-'.join(head.split(os.sep)),
                                filemoddatetime=dtmodified.strftime("%Y-%m-%dT%H:%M:%S"),
                                uploaddatetime=dtupload.strftime("%Y-%m-%dT%H:%M:%S"),
                                job=flbase,
                                num=num)
    triplet_store.append((fl, fltitle, flproj))

fls, ttls, pjs = zip(*triplet_store)
field_files = len(max(fls, key=len))
field_titles = len(max(ttls, key=len))
field_projects = len(max(pjs, key=len))

print '=' * 80
for fl, ttl, pj in triplet_store:
    print """{pj:{pjw}s}   {ttl:{ttlw}s}   {fl:{flw}s}""".format(
        fl=fl, flw=field_files,
        pj=pj, pjw=field_projects,
        ttl=ttl, ttlw=field_titles)
print '-' * 80
print """{pj:{pjw}s}   {ttl:{ttlw}s}   {fl:{flw}s}""".format(
    fl='File', flw=field_files,
    pj='Publication', pjw=field_projects,
    ttl='QC Record', ttlw=field_titles)
print '=' * 80
print """Supply password to authorize upload to CSI portal {user}@{portal}
    each [File] above to its individual record [QC Record] and attach it
    to [Publication]. (Pub not yet relevant)
""".format(user=args.user, portal=args.portal)
upass = getpass.getpass()


# TODO pub should be array

# TODO option to filter out already uploaded calcs

# TODO any stray files go to --cxs-files w/o option

# TODO option to add title, pub line-by-line

# TODO: all of record/title/publication needs a grand name refactoring.
#   here is a mix of current status and future plans

# TODO: always Public, Other, Final

# TODO: microiterate option for same filename othersiese

env_s = """
<PublicationPublish.PublishWithValuesContract xmlns="http://schemas.datacontract.org/2004/07/ChemicalSemantics.Services.WCF">
  <username>user_name</username>
  <userPassword>user_pass</userPassword>
  <title>Unique_name</title>
  <friendlyTitle>Title_to_display</friendlyTitle>
  <description>description</description>
  <category>category_no</category>
  <status>status_no</status>
  <type>type_no</type>
  <securityKey>security_key</securityKey>
  <filename>filename(cml,ttl)</filename>
  <fileBuffer>Base64 buffer</fileBuffer>
</PublicationPublish.PublishWithValuesContract>
"""

for fl, ttl, pj in triplet_store:
    print 'File {0} ...'.format(fl)

    with open(fl) as handle:
        cml64 = base64.b64encode(handle.read())
    print '  ... CML file read in and converted into base64'

    # I don't think we want to glean these from CSX anymore
    # doc = etree.parse(fl)
    # title = next(x.text for x in doc.xpath('.//*[local-name()="title"]'))
    # desc = next(x.text for x in doc.xpath('.//*[local-name()="abstract"]'))
    # category = next(x.text for x in doc.xpath('.//*[local-name()="category"]'))
    # status = next(x.text for x in doc.xpath('.//*[local-name()="status"]'))
    # type = next(x.text for x in doc.xpath('.//*[local-name()="visibility"]'))
    # print title, desc, category, status, type

    env_ns = '{http://schemas.datacontract.org/2004/07/ChemicalSemantics.Services.WCF}'
    root = ET.fromstring(env_s)

    print '  ... REST envelope formed'

    e_user = root.find(env_ns + 'username')
    e_user.text = args.user

    e_pass = root.find(env_ns + 'userPassword')
    e_pass.text = upass

    # e_unique=root.find(env_ns+'title')
    # e_unique.text=unique

    e_title = root.find(env_ns + 'friendlyTitle')
    e_title.text = ttl

    # e_desc=root.find(env_ns+'description')
    # e_desc.text=desc

    e_category = root.find(env_ns + 'category')
    e_category.text = "14"  # computational chemistry

    e_status = root.find(env_ns + 'status')
    e_status.text = "13"  # TODO prelim = 13, draft = 12, final = 11

    e_type = root.find(env_ns + 'type')
    e_type.text = "8"  # TODO priv = 9, protect = 10, public = 8

    e_filename = root.find(env_ns + 'filename')
    e_filename.text = fl + '.csx'

    e_filebuffer = root.find(env_ns + 'fileBuffer')
    e_filebuffer.text = cml64

    print '  ... REST envelope customized'

    env_ready = ET.tostring(root)
    url1 = portals[args.portal] + '/cs/Services/WCF/PublicationPublish.svc/PublishWithValues'
    request = urllib2.Request(url1, env_ready, headers={'Content-type': 'application/xml '})

    try:
        response = urllib2.urlopen(request)
    except urllib2.HTTPError, e:
        print e.code
        print e.msg
        print e.headers
        print e.fp.read()
    print '  ... CSX published with result:'
    print response.read()
