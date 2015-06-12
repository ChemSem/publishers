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
from lxml import etree

# get csx file[s] for qcpub
#   * single [cl]
#   * all in dir [cl]
#   * glob [cl]
#   * dialog
# get allocation to enhpub
#   * one-to-one
#   * all-to-one
# 

root_directory = os.path.dirname(os.path.realpath(__file__))
host_nickname = socket.gethostname().split('.')[0]
portals = {
    'portable': 'http://portable.chemsem.com',
    'cloud': 'http://chemsemplus.cloudapp.net',
    }


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

#parser = argparse.ArgumentParser(description='test', fromfile_prefix_chars="@")
#parser.add_argument('-l', '--launch_directory', type=readable_dir, default='/tmp/non_existent_dir')
#args = parser.parse_args()

#csx2portal.py --csx ~/linux/psi4/sandbox/fakefs/proj1/* ./nu_water_sp.csx 

def parse_command_line():
    """Function to

    """

    parser = argparse.ArgumentParser(description='Publish computations to CSI portal',
        formatter_class=argparse.RawTextHelpFormatter) #ArgumentDefaultsHelpFormatter)

    group = parser.add_mutually_exclusive_group()
    #group.add_argument('--csx-glob',
    #    action='append',
    #    default=[], #'./*csx'],
    #    metavar='STRING',
    #    help="""specify glob string """)
    group.add_argument('--csx-glob',
        nargs='+',
        action='store',
        metavar='STRING',
        help="""specify glob string (default: %(default)s)""")
    group.add_argument('--csx-files',
        nargs='+',
        action='store',
        metavar='FILE',
        help="""specify CSX files to upload (default: %(default)s)""")
    group.add_argument('--csx-within',
        action='store',
        type=readable_dir,
        #default='.',
        metavar='DIR',
        help="""specify directory within which to recursively seek CSX files (default: %(default)s)""")
    # TODO not clear global default for files
    # merge glob and files, testing on '*'
    # default

    group = parser.add_mutually_exclusive_group()
    group.add_argument('--each-to-pub',
        metavar='PROJECT_PREFIX',
        help="""assign each CSX to its own publication (autovivified)(default: %(default)s)""")
    group.add_argument('--all-to-pub',
        metavar='PROJECT',
        help="""assign all CSX to single publication (autovivified) (default: %(default)s)""")

    # portal username
    parser.add_argument('--user',
        action='store',
        default=getpass.getuser(),
        metavar='USER',
        help="""ChemSem portal username (default: %(default)s)""")
    # hostname
    parser.add_argument('--host',
        action='store',
        default=host_nickname,
        metavar='STRING',
        help="""nickname for data computer (default: %(default)s)""")
    # portal
    parser.add_argument('--portal',
        action='store',
        default='cloud',
        choices=portals.keys(),
        help="""ChemSem portal on which to publish (default: %(default)s)""")
    # title
    parser.add_argument('--title',
        action='store',
        default="""{host}__{pathfromhome}__{job}""",
        help="""identifier for *you* to distinguish among your QC
records. Supply a string in Python's string.format(),
using plaintext and any placeholders among: host, 
user, pathfromhome, datetime, job, project, and num.
For instance, files:
    johndoe Jun 10 14:22 fakefs/proj1/dft-psivar.csx
    johndoe Jun 10 12:58 fakefs/proj1/nu_water_sp2.csx
    johndoe Jun 10 14:22 fakefs/proj2/dft-psivar.csx
by default, '{host}__{pathfromhome}__{job}', become:
    myMac__linux-psi4-sandbox-fakefs-proj1__dft-psivar
    myMac__linux-psi4-sandbox-fakefs-proj1__nu_water_sp2
    myMac__linux-psi4-sandbox-fakefs-proj2__dft-psivar
while with '{host}__{user}__{pathfromhome}__{datetime}__{job}__{project}__{num}', become:
    myMac__johndoe__sandbox-fakefs-proj1__2015-06-10T14:22:41__dft-psivar__tmp__0
    myMac__johndoe__sandbox-fakefs-proj1__2015-06-10T12:58:13__nu_water_sp2__tmp__1
    myMac__johndoe__sandbox-fakefs-proj2__2015-06-10T14:22:41__dft-psivar__tmp__2
(default: %(default)s)
""")


    return parser.parse_args()


# "main"
args = parse_command_line()

print args

fls = [
    './dft-psivar.csx',
    '$HOME/linux/psi4/sandbox/dft-psivar.csx',
    '~/linux/psi4/sandbox/dft-psivar.csx',
    '$PSI',
    '$PSI/../sandbox/dft-psivar.csx',
    '~/linux/../Documents',
    ]


print '\nglob\n', args.csx_glob
print '\nfiles\n', args.csx_files
print '\nwithin\n', args.csx_within



# CSX files
readable_csx = []

if args.csx_files:
    for fl in args.csx_files:
        if fl.endswith('.csx'):
            if os.access(fl, os.R_OK):
                readable_csx.append(os.path.realpath(fl))

elif args.csx_glob:
    for spec in args.csx_glob:
        files = glob.glob(os.path.abspath(
                          os.path.expanduser(
                          os.path.expandvars(spec))))
        for fl in files:
            if fl.endswith('.csx'):
                if os.access(fl, os.R_OK):
                    readable_csx.append(fl)

elif args.csx_within:
    for fl in find_files(args.csx_within, '*.csx'):
        if os.access(fl, os.R_OK):
            readable_csx.append(fl)

print '\n\n'

for num, fl in enumerate(sorted(readable_csx)):
    home = os.path.expanduser('~')
    flwrthome = os.path.relpath(fl, home)
    head, tail = os.path.split(flwrthome)
    flbase, ext = os.path.splitext(tail)
    dtmodified = datetime.datetime.fromtimestamp(os.path.getmtime(fl))
    dtmodified.replace(microsecond=0)
    #print home, head, flbase, ext, os.path.getmtime(fl), dtmodified.isoformat()
    #uniq = '__'.join([args.host, args.user, head, flbase])
    fltitle = args.title.format(host=args.host,
                            user=args.user,
                            pathfromhome='-'.join(head.split(os.sep)),
                            datetime=dtmodified.isoformat(),
                            job=flbase,
                            project='tmp',
                            num=num)                            
    print fl, fltitle




#args = sys.argv[1:]
#if len(args) == 1:
#    cmlp = args[0]
#else:
#    cmlp = max(glob.iglob('*.csx'), key=os.path.getctime)
#filename = cmlp.split('.')[0]
#cmlf=open(cmlp)
#cmls=cmlf.read()
#cml64=base64.b64encode(cmls)
#cmlf.close()
#print "CML file " + cmlp + " read successfully in and converted into base64" 
#doc = etree.parse(cmlp)
#title = next(x.text for x in doc.xpath('.//*[local-name()="title"]'))
#desc = next(x.text for x in doc.xpath('.//*[local-name()="abstract"]'))
#category = next(x.text for x in doc.xpath('.//*[local-name()="category"]'))
#status = next(x.text for x in doc.xpath('.//*[local-name()="status"]'))
#type = next(x.text for x in doc.xpath('.//*[local-name()="visibility"]'))
#
#
#env_s="""
#<PublicationPublish.PublishWithValuesContract xmlns="http://schemas.datacontract.org/2004/07/ChemicalSemantics.Services.WCF">
#  <username>user_name</username>
#  <userPassword>user_pass</userPassword>
#  <title>Unique_name</title>
#  <friendlyTitle>Title_to_display</friendlyTitle>
#  <description>description</description>
#  <category>category_no</category>
#  <status>status_no</status>
#  <type>type_no</type>
#  <securityKey>security_key</securityKey>
#  <filename>filename(cml,ttl)</filename>
#  <fileBuffer>Base64 buffer</fileBuffer>
#</PublicationPublish.PublishWithValuesContract>
#"""
#env_ns='{http://schemas.datacontract.org/2004/07/ChemicalSemantics.Services.WCF}'
#root = ET.fromstring(env_s)
#
#print "REST envelope formed"
#
#user=raw_input('user name:')
#upass=getpass.getpass()
#unique="This_unique_molecule"
##title="Python Publisher from Psi4 " + filename 
##desc="Published by bwang Python module"
##category="1" # other
##status="3" # preliminary
##type="1" # public
#key="csx" # security key
#
#
#
#e_user=root.find(env_ns+'username')
#e_user.text=user
#
#e_pass=root.find(env_ns+'userPassword')
#e_pass.text=upass
#
#e_unique=root.find(env_ns+'title')
#e_unique.text=unique
#
#e_title=root.find(env_ns+'friendlyTitle')
#e_title.text=title
#
#e_desc=root.find(env_ns+'description')
#e_desc.text=desc
#
#e_category=root.find(env_ns+'category')
#e_category.text=category
#
#e_status=root.find(env_ns+'status')
#e_status.text=status
#
#e_type=root.find(env_ns+'type')
#e_type.text=type
#
#e_filename=root.find(env_ns+'filename')
#path,file=os.path.split(cmlp)
#e_filename.text=file
#
#e_filebuffer=root.find(env_ns+'fileBuffer')
#e_filebuffer.text=cml64
#
#print "REST envelope customized"
#
#env_ready=ET.tostring(root)
#print env_ready
#
##url1='http://portable.chemsem.com/cs/Services/WCF/PublicationPublish.svc/PublishWithValues'
#url1='http://chemsemplus.cloudapp.net/cs/Services/WCF/PublicationPublish.svc/PublishWithValues'
#
#r=urllib2.Request(url1,env_ready,headers={'Content-type': 'application/xml '})
#try:
#    o=urllib2.urlopen(r)
#except urllib2.HTTPError, e:
#    print e.code
#    print e.msg
#    print e.headers
#    print e.fp.read()
#print "CSX published with result:"
#print o.read()

