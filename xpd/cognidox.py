import getpass
import base64
import urllib
import urllib2
from xpd.ntlm import HTTPNtlmAuthHandler
import xml.dom.minidom
from xml.dom.minidom import parse, parseString
import time
import sys
import os
import re
#url = "http://cognidox/cgi-perl/part-details?partnum=XM-000571-PC"
url = 'http://cognidox.xmos.local/cgi-perl/soap/soapservice'
form_url = 'http://cognidox.xmos.local/cgi-perl/do-action'
docs_url = 'http://cognidox/vdocs'
if 'COGNIDOX_USER' in os.environ:
    saved_user = 'XMOS\\'+os.environ['COGNIDOX_USER']
else:
    saved_user = None

if 'COGNIDOX_PASSWORD' in os.environ:
    saved_password = os.environ['COGNIDOX_PASSWORD']
else:
    saved_password = None

def initCognidox(user=None,password=None):
    global saved_user, saved_password
    if not user:
        if not saved_user:
            sys.stdout.write('Please enter cognidox username: ')
            saved_user = raw_input()
            saved_user = 'XMOS\\'+saved_user
            if not saved_password:
                saved_password = getpass.getpass()
        user = saved_user
        password = saved_password
    passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, user, password)
    passman.add_password(None, form_url, user, password)
    passman.add_password(None, docs_url, user, password)
    # create the NTLM authentication handler
    auth_NTLM = HTTPNtlmAuthHandler.HTTPNtlmAuthHandler(passman)

    # create and install the opener
    opener = urllib2.build_opener(auth_NTLM)
    urllib2.install_opener(opener)


# retrieve the result

request_template = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:cg="http://www.vidanti.com/CogniDox"><SOAP-ENV:Body><cg:%(reqtype)s>%(args)s</cg:%(reqtype)s></SOAP-ENV:Body></SOAP-ENV:Envelope>
"""

def buildRequest(reqtype, args, masterfile = None):
    argstr = ""
    for name, val in args.items():
        argstr += "<cg:%(name)s>%(val)s</cg:%(name)s>" % {'name':name,
                                                          'val':val}

    if masterfile:
        argstr += '<cg:MasterFile href="%s"/>'%masterfile

    return request_template % {'reqtype':reqtype,
                               'args':argstr}


def doCognidoxCheckIn(partnumber,
                      path,
                      comment = "Automated upload",
                      draft = True,
                      version = None):
    initCognidox()
    ts = time.time()
    boundary = '_----------=_%u' % ts
    reqtype = 'CogniDoxCreateVersionRequest'
    action = 'http://cognidox.xmos.local/cgi-perl/soap/%s' % reqtype
    content_type = \
        'multipart/related; boundary=%s; charset="utf-8"; start="<%umaincontentcognidox@vidanti.com>"; type="text/xml"'%(boundary,ts)
    headers = {'SOAPAction': action,
               'Content-Type': 'multipart/related'}

    body = """MIME-Version: 1.0
Content-Transfer-Encoding: binary
Content-Type: %s

This is a multi-part message in MIME format

""" % content_type

    if draft:
        issue_type = 'draft'
    else:
        issue_type = 'issue'

    args = {'PartNumber':partnumber,
                        'IssueComment':comment,
                        'IssueType': issue_type}

    if version:
        args['VersionString'] = version

    req = buildRequest(reqtype,
                       args,
                       masterfile="cid:%ufilecontent.main@vidanti.com"%ts)

    n = len(req)+1
    body += "--" + boundary
    body += """
Content-Disposition: inline
Content-Id: <%umaincontentcognidox@vidanti.com>
Content-Length: %u
Content-Transfer-Encoding: binary
Content-Type: text/xml; charset="utf-8"

""" % (ts, n)

    body += req
    body += "\n"

    body += "--" + boundary
    body += """
Content-Disposition: inline; filename="%(path)s"
Content-Id: <%(ts)ufilecontent.main@vidanti.com>
Content-Transfer-Encoding: base64
Content-Type: application/octet-stream; name="%(path)s"

""" % {'path':path,'ts':ts}

    f = open(path)
    s = f.read()
    f.close()

    enc = base64.b64encode(s)

    body += enc

    body += "\n\n" + "--" + boundary + "\n"


    lines = body.split("\n")
    body = "\r\n".join(lines)
    req = urllib2.Request(url, body, headers)
    try:
        response = urllib2.urlopen(req)
    except TypeError:
        print >>sys.stderr, "Error connecting to cognidox"
        sys.exit(1)

    resp_xml = response.read()

    dom = xml.dom.minidom.parseString(resp_xml)
    try:
        elem = dom.getElementsByTagName('cg:IssueNumber')[0]
        return elem.childNodes[0].wholeText
    except IndexError:
        return None


def doCognidox(reqtype, args):
    initCognidox()
    action = 'http://cognidox.xmos.local/cgi-perl/soap/%s' % reqtype
    headers = { 'Content-Type': 'text/xml',
                'SOAPAction': action }
    url = 'http://cognidox.xmos.local/cgi-perl/soap/soapservice'
    data = buildRequest(reqtype, args)
    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req)
    resp_xml = response.read()
    return resp_xml

def get_docinfo(partnum):
    resp_xml = doCognidox('CogniDoxDocInfoRequest',
                          {'PartNumber':partnum})
    dom = xml.dom.minidom.parseString(resp_xml)
    try:
        elem = dom.getElementsByTagName('cg:InfoResult')[0]
    except IndexError:
        return {}
    info = {}
    for node in elem.childNodes:
        key = node.tagName[3:]
        if len(node.childNodes) == 1 and \
           hasattr(node.childNodes[0],'wholeText'):
            value = node.childNodes[0].wholeText
        else:
            value = node.toxml()
        info[key] = value
    return info


def get_docnumber(partnum):
    resp_xml = doCognidox('CogniDoxMetaValRequest',
                          {'PartNumber':partnum,
                           'MetaName':'Document Number'})
    dom = xml.dom.minidom.parseString(resp_xml)
    try:
        elem = dom.getElementsByTagName('cg:value')[0]
        return elem.childNodes[0].wholeText
    except IndexError:
        return None

def create_docnumber(partnum):
    initCognidox()
    actions = 'plugin-CogniDoxXMOSDocumentNumbersPlugin-plg_generateDocumentNumber'
    args = urllib.urlencode({'partnum':partnum,
                             'actions':actions})
    req = urllib2.Request(form_url, args)
    response = urllib2.urlopen(req)
    return get_docnumber(partnum)

def create_document(title, doctype, path):
    resp_xml = doCognidox('CogniDoxCreateDocRequest',
                          {'Title':title,
                           'DocType':doctype,
                           'Path':path})
    dom = xml.dom.minidom.parseString(resp_xml)
    try:
        elem = dom.getElementsByTagName('cg:PartNumber')[0]
        return elem.childNodes[0].wholeText
    except IndexError:
        return None



def query_and_create_document(default_path,
                              title=None,
                              default_title = '',
                              default_doctype = 'PC',
                              exit_on_failure = True,
                              auto_create = False,
                              doctype = None):
    paths = """
/Products/Tools
/Projects/Apps
"""
    doctypes = """
   CC:Company Collateral
   PC:Product Collateral
   UN:Unmanaged
"""
    print "Cannot find cognidox part number."
    initCognidox()
    sys.stdout.write("Do you know an existing part number (Y/n)?")
    if auto_create:
        x = 'n'
    else:
        x = raw_input()
    if not x.upper() in ['N','NO']:
        sys.stdout.write("Enter part number: ")
        partnum = raw_input()
        info = get_docinfo(partnum)
        if not info:
            print "Invalid part number"
            sys.exit(1)
    else:
        sys.stdout.write("Do you want to create a part (Y/n)?")
        if auto_create:
            x = 'y'
        else:
            x = raw_input()
        if not x.upper() in ['N','NO']:
            if not title:
                sys.stdout.write("Please enter document title (%s): " % default_title)
                if auto_create:
                    title = default_title
                else:
                    title = raw_input()
                if title == '':
                    title = default_title
                if title == '':
                    sys.stderr.write("Need title to proceed.\n")
                    sys.exit(1)
            if not doctype:
                print "Possible document types:"
                print doctypes
                sys.stdout.write("Please enter doctype (%s): " % default_doctype)
                if auto_create:
                    doctype = default_doctype
                else:
                    doctype = raw_input()
                if doctype == '':
                    doctype = default_doctype
            print "Example paths:"
            print paths
            sys.stdout.write("Please enter path (%s): " % default_path)
            if auto_create:
                path = default_path
            else:
                path = raw_input()
            if path == '':
                path = default_path

            print "Create document"
            print "   Title:%s" % title
            print "    Type:%s" % doctype
            print "    Path:%s" % path
            sys.stdout.write("Are you sure (Y/n)?")
            if auto_create:
                x = 'y'
            else:
                x = raw_input()
            if not x.upper() in ['N','NO']:
                partnum = create_document(title,doctype,path)
                error = False
                if not partnum or not re.match('XM-.*',partnum):
                    error = True
                if error:
                    print "Something has gone wrong"
                    sys.exit(1)
                else:
                    print "Created document with part number " + partnum
            else:
                print "Need part number to proceed"
                sys.exit(1)
        else:
            print "Need part number to proceed"
            sys.exit(1)

    return partnum


def get_revision(elem):
    return elem.getElementsByTagName('revision')[0].childNodes[0].wholeText

def get_version_tag(elem):
    try:
        return str(elem.getElementsByTagName('VersionTag')[0].childNodes[0].wholeText)
    except:
        return ""

def get_subinfo(elem, tag):
    return str(elem.getElementsByTagName(tag)[0].childNodes[0].wholeText)

def _to_int(x):
    if x=='':
        return 0
    else:
        return int(x)

def _get_latest_from_elems(elems, exclude_drafts = False):
    max_version = None
    max_elem = None
    for elem in elems:
        m = re.match('(\d*)(.*)',get_revision(elem))
        if m:
            version = _to_int(m.groups(0)[0]), m.groups(0)[1]
            if exclude_drafts and version[1] != '':
                continue
            if not max_version or version[0] > max_version[0] or \
                (version[0]==max_version[0] and version[1] > max_version[1]):
                max_version = version
                max_elem = elem
    if max_version == None:
        return None, None
    return str(max_version[0]) + max_version[1], max_elem

def _get_latest_issue(partnum, exclude_drafts=False):
    info = get_docinfo(partnum)
    if not info or not 'Versions' in info:
        return None
    dom = xml.dom.minidom.parseString(info['Versions'].replace('cg:',''))
    elems = dom.getElementsByTagName('VersionItem')
    max_version,elem = _get_latest_from_elems(elems, exclude_drafts)
    return max_version,elem

def get_latest_issue(partnum, exclude_drafts=False):
    res = _get_latest_issue(partnum, exclude_drafts)
    if not res:
        return None
    max_version,elem = res
    return max_version

def fetch_revision(partnum, revision):
    info = get_docinfo(partnum)
    if not info or not 'Versions' in info:
        return None
    dom = xml.dom.minidom.parseString(info['Versions'].replace('cg:',''))
    elems = dom.getElementsByTagName('VersionItem')
    elem = None
    for e in elems:
        if get_revision(e) == revision:
            elem = e

    if not elem:
        return None
    else:
        return urllib2.urlopen(docs_url+'/'+get_subinfo(elem,'file'))


def fetch_latest(partnum,exclude_drafts=False):
    _,elem = _get_latest_issue(partnum, exclude_drafts)
    print "Fetching %s" % (docs_url+'/'+get_subinfo(elem,'file'))

    info = {'revision':get_revision(elem),
            'version_tag':get_version_tag(elem)}
    return urllib2.urlopen(docs_url+'/'+get_subinfo(elem,'file')),info


def fetch_version(partnum, version):
    def match_version(v1,v2):
        return (v1==v2) or (len(v2)>len(v1) and v1==v2[:len(v1)] and \
                            re.match('rc.*|beta.*|alpha.*',v2[len(v1):]))

    info = get_docinfo(partnum)
    if not info or not 'Versions' in info:
        return None
    dom = xml.dom.minidom.parseString(info['Versions'].replace('cg:',''))
    elems = dom.getElementsByTagName('VersionItem')
    elems = [elem for elem in elems if match_version(version,get_version_tag(elem))]
    version, elem = _get_latest_from_elems(elems)
    if version == None:
        return None
    print "Fetching %s" % (docs_url+'/'+get_subinfo(elem,'file'))
    return urllib2.urlopen(docs_url+'/'+get_subinfo(elem,'file'))


if __name__ == "__main__":
    initCognidox()
    print get_docinfo('XM-001603-DH')
