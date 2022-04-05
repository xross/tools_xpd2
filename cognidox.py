import base64
import getpass
import os
import re
import sys
import time
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import xml.dom.minidom


class CognidoxError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


COGNIDOX_RETRIES = 100

if 'COGNIDOX_URL' in os.environ:
    base_url = os.environ['COGNIDOX_URL']
else:
    base_url = 'http://cognidox.xmos.local'
if 'COGNIDOX_USER' in os.environ:
    saved_user = os.environ['COGNIDOX_USER']
else:
    saved_user = None

if 'COGNIDOX_PASSWORD' in os.environ:
    saved_password = os.environ['COGNIDOX_PASSWORD']
else:
    saved_password = None


def urlopen(req):
    count = 0
    while True:
        try:
            return urllib.request.urlopen(req)
        except urllib.error.URLError:
            print("Error connecting to cognidox", file=sys.stderr)
            count = count + 1
            if count > COGNIDOX_RETRIES:
                raise CognidoxError("Too many attempts to connect - giving up")
            else:
                print("Retrying...", file=sys.stderr)


# url = "http://cognidox/cgi-perl/part-details?partnum=XM-000571-PC"
url = '%s/cgi-perl/soap/soapservice' % base_url
form_url = '%s/cgi-perl/do-action' % base_url
assign_license_url = '%s/cgi-perl/assign-license-to-document' % base_url
assign_license_agreemnt_url = '%s/cgi-perl/assign-license-agreement' % base_url
promote_draft_url = '%s/cgi-perl/promote-draft' % base_url
set_document_notifiers_url = '%s/cgi-perl/set-document-notifiers' % base_url
docs_url = '%s/vdocs' % base_url


def initCognidox(user=None, password=None):
    global saved_user, saved_password
    if not user:
        if not saved_user:
            sys.stdout.write('Please enter cognidox username: ')
            saved_user = input()
            # if not saved_user.startswith('XMOS\\'):
            #    saved_user = 'XMOS\\'+saved_user
            if not saved_password:
                saved_password = getpass.getpass()
        user = saved_user
        password = saved_password
    passman = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    passman.add_password(None, url, user, password)
    passman.add_password(None, form_url, user, password)
    passman.add_password(None, docs_url, user, password)
    passman.add_password(None, assign_license_url, user, password)
    passman.add_password(None, assign_license_agreemnt_url, user, password)
    passman.add_password(None, promote_draft_url, user, password)
    passman.add_password(None, set_document_notifiers_url, user, password)
    # create the NTLM authentication handler

    # Cognidox used to use NTLM but this has been changed to Kerberos
    # auth_NTLM = HTTPNtlmAuthHandler.HTTPNtlmAuthHandler(passman)

    auth = urllib.request.HTTPBasicAuthHandler(passman)

    # create and install the opener
    opener = urllib.request.build_opener(auth)
    urllib.request.install_opener(opener)


# retrieve the result (DO NOT FORMAT to 80 columns!)
request_template = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:cg="http://www.vidanti.com/CogniDox"><SOAP-ENV:Body><cg:%(reqtype)s>%(args)s</cg:%(reqtype)s></SOAP-ENV:Body></SOAP-ENV:Envelope>
"""


def buildRequest(reqtype, args, masterfile=None):
    argstr = ""
    for name, val in list(args.items()):
        argstr += "<cg:%(name)s>%(val)s</cg:%(name)s>" % {'name': name,
                                                          'val': val}

    if masterfile:
        argstr += '<cg:MasterFile href="%s"/>' % masterfile

    return request_template % {'reqtype': reqtype,
                               'args': argstr}


def doCognidoxCheckIn(partnumber,
                      path,
                      comment="Automated upload",
                      draft=True,
                      version=None):
    initCognidox()
    ts = time.time()
    boundary = '_----------=_%u' % ts
    reqtype = 'CogniDoxCreateVersionRequest'
    action = '%s/cgi-perl/soap/%s' % (base_url, reqtype)
    content_type = \
        'multipart/related; \
        boundary=%s; \
        charset="utf-8"; \
        start="<%umaincontentcognidox@vidanti.com>"; \
        type="text/xml"' % (boundary, ts)
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

    args = {'PartNumber': partnumber,
            'IssueComment': comment,
            'IssueType': issue_type}

    if version:
        args['VersionString'] = version

    req = buildRequest(reqtype,
                       args,
                       masterfile="cid:%ufilecontent.main@vidanti.com" % ts)

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

""" % {'path': path, 'ts': ts}

    f = open(path)
    s = f.read()
    f.close()

    enc = base64.b64encode(s)

    body += enc

    body += "\n\n" + "--" + boundary + "\n"
    body = body.replace("\n", "\r\n")

    req = urllib.request.Request(url, body, headers)
    response = urlopen(req)

    resp_xml = response.read()

    try:
        dom = xml.dom.minidom.parseString(resp_xml)
        elem = dom.getElementsByTagName('cg:IssueNumber')[0]
        return elem.childNodes[0].wholeText
    except Exception: # dom can return multiple exception types
        print("Error with cognidox response", file=sys.stderr)
        print(resp_xml, file=sys.stderr)
        return None


upload_document = doCognidoxCheckIn


def doCognidox(reqtype, args):
    initCognidox()
    action = '%s/cgi-perl/soap/%s' % (base_url, reqtype)
    headers = {'Content-Type': 'text/xml',
               'SOAPAction': action}
    url = '%s/cgi-perl/soap/soapservice' % base_url
    data = buildRequest(reqtype, args)
    req = urllib.request.Request(url, data, headers)
    response = urlopen(req)
    resp_xml = response.read()
    return resp_xml


def get_docinfo(partnum):
    resp_xml = doCognidox('CogniDoxDocInfoRequest',
                          {'PartNumber': partnum})
    dom = xml.dom.minidom.parseString(resp_xml)
    try:
        elem = dom.getElementsByTagName('cg:InfoResult')[0]
    except IndexError:
        return {}
    info = {}
    for node in elem.childNodes:
        key = node.tagName[3:]
        if len(node.childNodes) == 1 and \
           hasattr(node.childNodes[0], 'wholeText'):
            value = node.childNodes[0].wholeText
        else:
            value = node.toxml()
        info[key] = value
    return info


def approve_doc(partnum, issuenum, comment="Automated Approval"):
    doCognidox('CogniDoxApproveDocRequest',
               {'PartNumber': partnum,
                'IssueNumber': issuenum,
                'ApprovalComment': comment})
    return


def publish_doc(partnum, comment="Automated Publish"):
    doCognidox('CogniDoxPublishDocRequest',
               {'PartNumber': partnum,
                'PublishComment': comment})
    return


def set_auto_update(partnum, autoupdate=True):
    if autoupdate:
        val = 'Yes'
    else:
        val = 'No'
    resp_xml = doCognidox('CogniDoxMetaValRequest',
                          {'PartNumber': partnum,
                           'MetaName': 'Auto-update',
                           'MetaVal': val})
    return resp_xml


def get_docnumber(partnum):
    resp_xml = doCognidox('CogniDoxMetaValRequest',
                          {'PartNumber': partnum,
                           'MetaName': 'Document Number'})
    dom = xml.dom.minidom.parseString(resp_xml)
    try:
        elem = dom.getElementsByTagName('cg:value')[0]
        return elem.childNodes[0].wholeText
    except IndexError:
        return None


def clear_docnumber(partnum):
    doCognidox('CogniDoxMetaValRequest',
               {'PartNumber': partnum,
                'MetaName': 'Document Number',
                'MetaVal': ''})


def create_docnumber(partnum):
    initCognidox()
    actions = \
        'plugin-CogniDoxXMOSDocumentNumbersPlugin-plg_generateDocumentNumber'
    args = urllib.parse.urlencode({'partnum': partnum,
                             'actions': actions})
    req = urllib.request.Request(form_url, args)
    urlopen(req)

    return get_docnumber(partnum)


def get_category_id(path):
    resp_xml = doCognidox('CogniDoxCategorySearchRequest',
                          {'Path': path})
    dom = xml.dom.minidom.parseString(resp_xml)
    elem = dom.getElementsByTagName('cg:CategoryId')[0]
    return elem.childNodes[0].wholeText


def create_category(path, name):
    doCognidox('CogniDoxCategoryCreateRequest',
               {'ParentCategoryId': get_category_id(path),
                'CategoryName': name})


def create_document(title, doctype, path):
    count = 0
    while True:
        resp_xml = doCognidox('CogniDoxCreateDocRequest',
                              {'Title': title,
                               'DocType': doctype,
                               'Path': path})
        try:
            dom = xml.dom.minidom.parseString(resp_xml)
            break
        # TODO: find out what this exception should be
        except Exception:
            print("Error invalid data returned by cognidox", file=sys.stderr)
            print(resp_xml, file=sys.stderr)
            count = count + 1
            if count > COGNIDOX_RETRIES:
                raise CognidoxError("Too many attempts to connect - giving up")
                sys.exit(1)
            else:
                print("Retrying...", file=sys.stderr)

    try:
        elem = dom.getElementsByTagName('cg:PartNumber')[0]
        return elem.childNodes[0].wholeText
    except IndexError:
        print("Error with cognidox response", file=sys.stderr)
        print(resp_xml, file=sys.stderr)
        raise CognidoxError('Could not create document\n' + resp_xml)


def query_and_create_document(default_path,
                              title=None,
                              default_title='',
                              default_doctype='PC',
                              exit_on_failure=True,
                              auto_create=False,
                              doctype=None):
    paths = """
/Products/Tools
/Projects/Apps
"""
    doctypes = """
   CC:Company Collateral
   PC:Product Collateral
   UN:Unmanaged
"""
    print("Cannot find cognidox part number.")
    initCognidox()
    if auto_create:
        x = 'n'
    else:
        sys.stdout.write("Do you know an existing part number (y/n) [y]? ")
        x = input()

    if x.upper() not in ['N', 'NO']:
        sys.stdout.write("Enter part number: ")
        partnum = input()
        info = get_docinfo(partnum)
        if not info:
            raise CognidoxError("Invalid part number")
    else:
        if auto_create:
            x = 'y'
        else:
            sys.stdout.write("Do you want to create a part (y/n) [y]? ")
            x = input()

        if x.upper() not in ['N', 'NO']:
            if not title:
                if auto_create:
                    title = default_title
                else:
                    sys.stdout.write(
                        "Please enter document title [%s]: " % default_title)
                    title = input()
                    if not title:
                        title = default_title

                if not title:
                    raise CognidoxError("Need title to proceed.")

            if not doctype:
                print("Possible document types:")
                print(doctypes)
                if auto_create:
                    doctype = default_doctype
                else:
                    sys.stdout.write(
                        "Please enter doctype [%s]: " % default_doctype)
                    doctype = input()
                    if not doctype:
                        doctype = default_doctype

            print("Example paths:")
            print(paths)
            if auto_create:
                path = default_path
            else:
                sys.stdout.write("Please enter path [%s]: " % default_path)
                path = input()
                if not path:
                    path = default_path

            print("Create document")
            print("   Title:%s" % title)
            print("    Type:%s" % doctype)
            print("    Path:%s" % path)
            if auto_create:
                x = 'y'
            else:
                sys.stdout.write("Are you sure (y/n) [y]?")
                x = input()

            if x.upper() not in ['N', 'NO']:
                partnum = create_document(title, doctype, path)
                error = False
                if not partnum or not re.match('XM-.*', partnum):
                    error = True
                if error:
                    raise CognidoxError("Something has gone wrong")
                else:
                    print("Created document with part number " + partnum)
            else:
                raise CognidoxError("Need part number to proceed")
        else:
            raise CognidoxError("Need part number to proceed")

    return partnum


def get_revision(elem):
    return elem.getElementsByTagName('revision')[0].childNodes[0].wholeText


def get_version_tag(elem):
    return str(
        elem.getElementsByTagName('VersionTag')[0].childNodes[0].wholeText)


def get_comment(elem):
    return str(elem.getElementsByTagName('comment')[0].childNodes[0].wholeText)


def get_subinfo(elem, tag):
    return str(elem.getElementsByTagName(tag)[0].childNodes[0].wholeText)


def _to_int(x):
    if x == '':
        return 0
    else:
        return int(x)


def _get_latest_from_elems(elems, exclude_drafts=False):
    max_version = None
    max_elem = None
    for elem in elems:
        m = re.match('(\d*)(.*)', get_revision(elem))
        if m:
            version = _to_int(m.groups(0)[0]), m.groups(0)[1]
            if exclude_drafts and version[1] != '':
                continue
            if not max_version or version[0] > max_version[0] or \
                    (version[0] == max_version[0] and
                        version[1] > max_version[1]):
                max_version = version
                max_elem = elem
    if max_version is None:
        return None, None
    return str(max_version[0]) + max_version[1], max_elem


def _get_latest_issue(partnum, exclude_drafts=False):
    info = get_docinfo(partnum)
    if not info or 'Versions' not in info:
        return None
    dom = xml.dom.minidom.parseString(info['Versions'].replace('cg:', ''))
    elems = dom.getElementsByTagName('VersionItem')
    max_version, elem = _get_latest_from_elems(elems, exclude_drafts)
    return max_version, elem


def get_latest_issue(partnum, exclude_drafts=False):
    res = _get_latest_issue(partnum, exclude_drafts)
    if not res:
        return None
    max_version, elem = res
    return max_version


def fetch_revision(partnum, revision):
    info = get_docinfo(partnum)
    if not info or 'Versions' not in info:
        return None
    dom = xml.dom.minidom.parseString(info['Versions'].replace('cg:', ''))
    elems = dom.getElementsByTagName('VersionItem')
    elem = None
    for e in elems:
        if get_revision(e) == revision:
            elem = e

    if not elem:
        return None
    else:
        return urlopen(docs_url+'/'+get_subinfo(elem, 'file'))


def fetch_latest(partnum, exclude_drafts=False):
    _, elem = _get_latest_issue(partnum, exclude_drafts)
    print("Fetching %s" % (docs_url+'/'+get_subinfo(elem, 'file')))

    info = {'revision': get_revision(elem),
            'version_tag': get_version_tag(elem)}

    return urlopen(docs_url+'/'+get_subinfo(elem, 'file')), info


def fetch_version(partnum, version):
    def match_version(v1, v2):
        return (v1 == v2) or (len(v2) > len(v1) and v1 == v2[:len(v1)] and
                              re.match('rc.*|beta.*|alpha.*', v2[len(v1):]))

    info = get_docinfo(partnum)
    if not info or 'Versions' not in info:
        return None
    dom = xml.dom.minidom.parseString(info['Versions'].replace('cg:', ''))
    elems = dom.getElementsByTagName('VersionItem')
    elems = [elem for elem in elems if match_version(
        version, get_version_tag(elem))]
    version, elem = _get_latest_from_elems(elems)
    if version is None:
        return None
    print("Fetching %s" % (docs_url+'/'+get_subinfo(elem, 'file')))
    return urlopen(docs_url+'/'+get_subinfo(elem, 'file'))


def get_all_version_tags(partnum, exclude_drafts=False):
    info = get_docinfo(partnum)
    if not info or 'Versions' not in info:
        return None
    dom = xml.dom.minidom.parseString(info['Versions'].replace('cg:', ''))
    elems = dom.getElementsByTagName('VersionItem')
    tags = []
    for elem in elems:
        if get_version_tag(elem):
            tags.append(get_version_tag(elem))
    return tags


def get_all_comments(partnum):
    info = get_docinfo(partnum)
    if not info or 'Versions' not in info:
        return None
    dom = xml.dom.minidom.parseString(info['Versions'].replace('cg:', ''))
    elems = dom.getElementsByTagName('VersionItem')
    comments = []
    for elem in elems:
        if get_comment(elem):
            comments.append(get_comment(elem))
    return comments


def version_to_num(s):
    x = list(s.upper())
    total = ord(x[0])-64
    for c in x[1:]:
        total = (ord(c)-65) + total*26
    return total


def num_to_version(x):
    l = []
    x = int(x)
    while (x > 0):
        l.append(chr(x % 26+65))
        x = x/26
    l.reverse()
    if len(l) > 0:
        l[0] = chr(ord(l[0])-1)
    return ''.join(l)


def increment_version(v):
    x = version_to_num(v)+1
    return num_to_version(x)


def get_next_doc_version_tag(partnum, base_version=None):
    if get_docnumber(partnum):
        return None

    tags = get_all_version_tags(partnum)

    if tags and base_version:
        tags = [tag[len(base_version)+1:]
                for tag in tags if tag.startswith(base_version+".")]

    if tags is None or tags == []:
        if base_version:
            return base_version + '.a'
        else:
            return 'A'

    num_tags = [version_to_num(tag) for tag in tags]
    max_tag = max(num_tags)

    if base_version:
        return base_version + '.' + num_to_version(max_tag+1).lower()
    else:
        return num_to_version(max_tag+1)


def assign_license(partnum,
                   license_name,
                   comment="Automatically assigned by script"):
    resp_xml = doCognidox('CogniDoxAddDocLicenseRequest',
                          {'PartNumber': partnum,
                           'LicenseComment': comment,
                           'Licenses':
                               '<cg:License>%s</cg:License>' % license_name})
    dom = xml.dom.minidom.parseString(resp_xml)
    try:
        elem = dom.getElementsByTagName('cg:Success')[0]
        error = (elem.childNodes[0].wholeText != '1')
    # TODO: find out what this exception should be
    except Exception:
        error = True
    if error:
        sys.stderr.write(resp_xml)
        raise CognidoxError('Error assigning license in Cognidox')


def assign_license_agreement(partnum,
                             agreement,
                             comment="Automatically assigned by script"):
    resp_xml = doCognidox('CogniDoxDocAgreementsRequest',
                          {'PartNumber': partnum,
                           'Comment': comment,
                           'AddAgreement': agreement})
    dom = xml.dom.minidom.parseString(resp_xml)
    try:
        elem = dom.getElementsByTagName('cg:Success')[0]
        error = (elem.childNodes[0].wholeText != '1')
    # TODO: find out what this exception should be
    except Exception:
        error = True
    if error:
        sys.stderr.write(resp_xml)
        raise CognidoxError('Error assigning license agreement in Cognidox')


def promote_latest_draft_to_issue(partnum):
    multipart_text = \
        "------WebKitFormBoundaryiJAMNwLBAIscEsPU\r\n" + \
        "Content-Disposition: form-data; \
        name=\"comment\"\r\n\r\nAutomated Promotion to Issue\r\n" + \
        "------WebKitFormBoundaryiJAMNwLBAIscEsPU\r\n" + \
        "Content-Disposition: form-data; \
        name=\"lic-comment\"\r\n\r\n\r\n" + \
        "------WebKitFormBoundaryiJAMNwLBAIscEsPU\r\n" + \
        "Content-Disposition: form-data; \
        name=\"partnum\"\r\n\r\n" + partnum + "\r\n" + \
        "------WebKitFormBoundaryiJAMNwLBAIscEsPU\r\n" + \
        "Content-Disposition: form-data; \
        name=\"dopromote\"\r\n\r\n1\r\n" + \
        "------WebKitFormBoundaryiJAMNwLBAIscEsPU\r\n" + \
        "Content-Disposition: form-data; \
        name=\".submit\"\r\n\r\nPromote Draft\r\n" + \
        "------WebKitFormBoundaryiJAMNwLBAIscEsPU--\r\n"
    initCognidox()
    headers = {
        'Content-Type':  "multipart/form-data; \
        boundary=----WebKitFormBoundaryiJAMNwLBAIscEsPU"}
    req = urllib.request.Request(promote_draft_url + '?partnum=%s' %
                          partnum, multipart_text, headers)
    urlopen(req)

    return


def set_approval_notification(partnum):
    initCognidox()
    multipart_text = "------WebKitFormBoundaryXQaTZBcOhOSF4dnE\r\n\
    Content-Disposition: form-data; \
    name=\"input-notifiers\"\r\n\r\n%(user)s\r\n\
    ------WebKitFormBoundaryXQaTZBcOhOSF4dnE\r\nContent-Disposition: \
    form-data; \
    name=\"notifiers\"\r\n\r\n%(user)s\r\n\
    ------WebKitFormBoundaryXQaTZBcOhOSF4dnE\r\n\
    Content-Disposition: form-data; \
    name=\"type\"\r\n\r\napproval\r\n\
    ------WebKitFormBoundaryXQaTZBcOhOSF4dnE\r\n\
    Content-Disposition: form-data; \
    name=\"action\"\r\n\r\nadd\r\n\
    ------WebKitFormBoundaryXQaTZBcOhOSF4dnE\r\n\
    Content-Disposition: form-data; \
    name=\"partnum\"\r\n\r\n%(partnum)s\r\n\
    ------WebKitFormBoundaryXQaTZBcOhOSF4dnE\r\n\
    Content-Disposition: form-data; \
    name=\".submit\"\r\n\r\nAdd Notifiers\r\n\
    ------WebKitFormBoundaryXQaTZBcOhOSF4dnE--\r\n" % {
        'user': saved_user.replace('XMOS\\', ''), 'partnum': partnum}
    headers = {
        'Content-Type':
        "multipart/form-data; boundary=----WebKitFormBoundaryXQaTZBcOhOSF4dnE"}
    req = urllib.request.Request(set_document_notifiers_url +
                          '?partnum=%s' % partnum, multipart_text, headers)
    urlopen(req)

    return


def rename_document(partnum, title):
    resp_xml = doCognidox('CogniDoxRenameDocRequest',
                          {'PartNumber': partnum,
                           'Title': title})
    dom = xml.dom.minidom.parseString(resp_xml)
    try:
        elem = dom.getElementsByTagName('cg:Success')[0]
        error = (elem.childNodes[0].wholeText != '1')
    # TODO: find out what this exception should be
    except Exception:
        error = True
    if error:
        raise CognidoxError('Could not rename document: %s' % partnum)
    return resp_xml


if __name__ == "__main__":
    pass
