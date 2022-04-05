import xml.parsers.expat
import xml.dom.minidom
from xml.dom.minidom import parse, parseString
import sys
import xml.sax.saxutils
from xmos_logging import *

class ExpatParseNode(object):
    """ Intermediate representation to convert from expat to a dom-like structure
    """
    def __init__(self, parent, name, attrs, line, column):
        self.parent = parent
        self.tagName = name
        self.attrs = {}
        self.childNodes = []
        self.line = line
        self.column = column
        for (attname, value) in list(attrs.items()):
            self.setAttribute(attname, value)

    def addChild(self, child):
        self.childNodes.append(child)

    def setAttribute(self, name, value):
        self.attrs[name] = value

    def getAttribute(self, name):
        if name in self.attrs:
            return self.attrs[name]
        else:
            return ''

    def cloneNode(self, deep, root=None):
        clone = ExpatParseNode(root, self.tagName, {}, self.line, self.column)
        for (attname, value) in list(self.attrs.items()):
            clone.setAttribute(attname, value)
        for child in self.childNodes:
            clone.cloneNode(deep, clone)
        if hasattr(self, 'wholeText'):
            clone.wholeText = self.wholeText
        return clone

    def removeChild(self, child):
        self.childNodes.remove(child)

    def hasChildNodes(self):
        if self.childNodes:
            return True
        return False


def init_expat_parser():
    """ The expat parser builds up a global structure using the three call-back functions
        This function initialises everything required for that parsing and returns
        the parser to use.
    """
    # Global to store the latest expat parsed structure
    global expat_tree
    expat_tree = ExpatParseNode(None, '_root', {}, 0, 0)

    # Global expat parser - connected up to the callback functions
    global expat_parser
    expat_parser = xml.parsers.expat.ParserCreate()
    expat_parser.StartElementHandler = expat_start_element
    expat_parser.EndElementHandler = expat_end_element
    expat_parser.CharacterDataHandler = expat_char_data
    return expat_parser

# Handler functions to convert from expat calls to a structure
def expat_start_element(name, attrs):
    """ On the start of an element make a node for that element and change the current root
        to be that node. The nodes all remember their parent in order to unwind at the end
        of an element.
    """
    global expat_tree
    node = ExpatParseNode(expat_tree, name, attrs, expat_parser.CurrentLineNumber, expat_parser.CurrentColumnNumber)
    if expat_tree:
        expat_tree.addChild(node)
    expat_tree = node

def expat_end_element(name):
    """ End of an element, move the global root back to the parent. The parent should never
        be able to be None because of the initial _root node created in init_expat_parser()
    """
    global expat_tree
    assert expat_tree.parent
    expat_tree = expat_tree.parent

def expat_char_data(data):
    """ Data found. The DOM structure is to create a child node for that data with the
        'wholeText' attribute containing the data. If data is called and the last node
        is a text node then simply append the data - expat seems to give data in
        16-character chunks.
    """
    global expat_tree
    if expat_tree.childNodes and hasattr(expat_tree.childNodes[-1], 'wholeText'):
        child = expat_tree.childNodes[-1]
    else:
        child = ExpatParseNode(expat_tree, '_textNode', {}, expat_parser.CurrentLineNumber, expat_parser.CurrentColumnNumber)
        expat_tree.addChild(child)
        child.wholeText = ''

    child.wholeText += data

def pp_xml(dom, elem, indent=''):
    if hasattr(elem, "tagName"):
        s = indent + '<' + str(elem.tagName)
        try:
            for (key, value) in list(elem.attributes.items()):
                s += " %s = \"%s\"" % (key, xml.sax.saxutils.escape(value.strip()))
        except:
            pass
        s += '>'
        found_subnode = False
        child_str = ''
        for c in elem.childNodes:
            if hasattr(c, 'tagName'):
                found_subnode = True
            child_str += pp_xml(dom, c, indent + '    ')
        if found_subnode:
           s += '\n' + child_str + indent
        else:
           s += child_str

        s += '</' + str(elem.tagName) + '>\n'
    elif hasattr(elem, "wholeText"):
        s = xml.sax.saxutils.escape(str(elem.wholeText).strip())
    else:
        s = indent + '<!--' + str(elem.nodeValue) + '-->\n'

    return s

def num(s):
    try:
        return int(s)
    except exceptions.ValueError:
        return float(s)


class XmlObject(object):
    def __init__(self, required=None):
        self.required = required


class XmlValue(XmlObject):
    def __init__(self, tagname=None, default=None, attrs={}, required=False):
        super(XmlValue, self).__init__(required=required)
        self.default = default
        self.tagname = tagname
        self.attrs = attrs

class XmlText(XmlObject):
    def __init__(self, tagname=None, default=None, attrs={}, required=False):
        super(XmlText, self).__init__(required=required)
        self.default = default
        self.tagname = tagname
        self.attrs = attrs


class XmlValueList(XmlObject):
    def __init__(self, tagname=None, required=False):
        super(XmlValueList, self).__init__(required=required)
        self.tagname = tagname


class XmlAttribute(XmlObject):
    def __init__(self, attrname=None, default=None, required=False):
        super(XmlAttribute, self).__init__(required=required)
        self.default=default
        self.attrname=attrname
        

class XmlNode(XmlObject):
    def __init__(self, typ, tagname=None, required=False):
        super(XmlNode, self).__init__(required=required)
        self.typ = typ
        self.tagname=tagname


class XmlNodeList(XmlObject):
    def __init__(self, typ, tagname=None, wrapper=None, required=False):
        super(XmlNodeList, self).__init__(required=required)
        self.typ = typ
        self.tagname = tagname
        self.wrapper = wrapper


class XmlTag(XmlObject):
    def __init__(self, name, tagname=None, typ=str, plural=False, attrs={}, wrapper=None, required=False, isWholeText = False):
        super(XmlTag, self).__init__(required=required)
        self.name = name
        if tagname:
            self.tagname = tagname
        else:
            self.tagname = name
        self.typ = typ
        self.plural = plural
        self.attrs = attrs
        self.wrapper = wrapper
        self.isWholeText = isWholeText


class XmlAttr(XmlObject):
    def __init__(self, name, attrname=None, required=False):
        super(XmlAttr, self).__init__(required=required)
        self.name = name
        if attrname:
            self.attrname = attrname
        else:
            self.attrname = name


class XmlObject(object):
    tags = []
    attrs = []

    def __init__(self, parent = None):
        self.tags = []
        self.attrs = []
        self.parent = parent
        self._extra_xml = None
        for attr in dir(self):
            val = getattr(self, attr)
            if isinstance(val, XmlValue):
                if val.tagname == None:
                    val.tagname = attr
                self.tags.append(XmlTag(attr, tagname=val.tagname, attrs=val.attrs, required=val.required))
                setattr(self, attr, val.default)
            elif isinstance(val, XmlNode):
                if val.tagname == None:
                    val.tagname = attr
                self.tags.append(XmlTag(attr, tagname=val.tagname, typ=val.typ, required=val.required))
                setattr(self, attr, None)
            elif isinstance(val, XmlNodeList):
                if val.tagname == None:
                    if attr[-1] == 's':
                        val.tagname = attr[:-1]
                    else:
                        val.tagname = attr
                self.tags.append(XmlTag(attr, tagname=val.tagname,
                                        typ=val.typ, plural=True,
                                        wrapper=val.wrapper, required=val.required))
                setattr(self, attr, [])
            elif isinstance(val, XmlValueList):
                if val.tagname == None:
                    if attr[-1] == 's':
                        val.tagname = attr[:-1]
                    else:
                        val.tagname = attr
                self.tags.append(XmlTag(attr, tagname=val.tagname,
                                        typ=str, plural=True, required=val.required))
                setattr(self, attr, [])
            elif isinstance(val, XmlAttribute):
                if val.attrname == None:
                    val.attrname = attr
                self.attrs.append(XmlAttr(attr, attrname=val.attrname, required=val.required))
                setattr(self, attr, val.default)
            elif isinstance(val, XmlText):
                if val.tagname == None:
                    val.tagname = attr
                self.tags.append(XmlTag(attr, tagname=val.tagname, attrs=val.attrs, required=val.required, isWholeText = True))
                setattr(self, attr, val.default)

    def pre_export(self):
        pass

    def post_import(self):
        pass

    def _add_child(self, dom, rootelem, name, val, attrs = {}, wrapper=None):
        if isinstance(val, XmlObject):
            elem = dom.createElement(name)
            for key, value in list(attrs.items()):
                elem.setAttribute(key, value)
            val.pre_export()
            val._add_attributes(dom, elem)
            val._add_children(dom, elem)
            val._add_extra_xml(dom, elem)
            rootelem.appendChild(elem)
        elif hasattr(val, '__iter__'):
            if wrapper:
                elem = dom.createElement(wrapper)
                rootelem.appendChild(elem)
            else:
                elem = rootelem
            for x in val:
                self._add_child(dom, elem, name, x)
        elif val != None:
            elem = dom.createElement(name)
            for key, value in list(attrs.items()):
                elem.setAttribute(key, value)
            text = dom.createTextNode(str(val))
            elem.appendChild(text)
            rootelem.appendChild(elem)

    def _add_children(self, dom, rootelem):
        for tag in self.tags:
            val = getattr(self, tag.name)
            if tag.isWholeText:
                text = ''
                if val:
                    text = str(val)
                textnode = dom.createTextNode(text)
                rootelem.appendChild(textnode)
            else:
                self._add_child(dom, rootelem, tag.tagname, val, tag.attrs,
                                tag.wrapper)
        return

    def _add_attributes(self, dom, elem):
        for attr in self.attrs:
            val = getattr(self, attr.name)
            if val:
                elem.setAttribute(attr.attrname, val)

    def _add_extra_xml(self, dom, elem):
        if self._extra_xml:
            for c in self._extra_xml.childNodes:
                elem.appendChild(c.cloneNode(True))

    def todom(self, root):
        self.pre_export()
        dom = xml.dom.minidom.parseString("<%s/>" % root)
        rootelem = dom.getElementsByTagName(root)[0]
        self._add_attributes(dom, rootelem)
        self._add_children(dom, rootelem)
        self._add_extra_xml(dom, rootelem)
        return dom

    def toxml(self, root):
        dom = self.todom(root)
        rootelem = dom.getElementsByTagName(root)[0]
        return '<?xml version=\"1.0\" ?>\n' + pp_xml(dom, rootelem).strip()

    def _fromdom(self, dom, root, src):
        for attr in self.attrs:
            attr_val = root.getAttribute(attr.attrname)
            if attr.required and not attr_val:
                log_error("%s:%d:%d: Missing attribute %s" % (src, root.line, root.column, attr.attrname))
            setattr(self, attr.name, attr_val)

        for tag in self.tags:
            vals = []
            childNodes = root.childNodes
            _root = root

            if tag.isWholeText:
                val = None
                if len(root.childNodes) > 0 and \
                   hasattr(root.childNodes[0], 'wholeText'):
                    val = root.childNodes[0].wholeText.rstrip()
                setattr(self, tag.name, val)
                continue

            if tag.wrapper:
                childNodes = []
                _root = None
                for x in root.childNodes:
                    if hasattr(x, "tagName") and x.tagName == tag.wrapper:
                        childNodes = x.childNodes
                        _root = x
                        break

                if tag.required and not _root:
                    log_error("%s:%d:%d: Missing node %s" % (src, root.line, root.column, tag.wrapper))

            for x in childNodes:
                if hasattr(x, "tagName") and x.tagName == tag.tagname:
                    if tag.plural and hasattr(tag, "typ") and tag.typ == str:
                        if x.childNodes == []:
                            val = ""
                        else:
                            val = x.childNodes[0].wholeText
                            val = val.strip()
                        vals.append(val)
                    elif hasattr(tag, "typ") and issubclass(tag.typ, XmlObject):
                        val = tag.typ(parent=self)
                        val._fromdom(dom, x, src)
                        vals.append(val)
                    else:
                        if not x.hasChildNodes():
                            log_warning("%s:%d:%d: Expected %s to have content" %
                                        (src, root.line, root.column, tag.tagname))
                        elif len(x.childNodes)<1 or not hasattr(x.childNodes[0], "wholeText"):
                            log_error("%s:%d:%d: Parse error - expected %s to have text content" %
                                        (src, root.line, root.column, tag.tagname))
                        else:
                            val = x.childNodes[0].wholeText
                            val = val.strip()
                            # Convert to a number if possible
                            try:
                                val = num(x)
                            except:
                                pass
                            if val in ["False", "false", "F", "0"]:
                                val = False
                            if val in ["True", "true", "T", "1"]:
                                val = True

                            vals.append(val)
                    _root.removeChild(x)

            if not tag.wrapper and tag.required and not vals:
                log_error("%s:%d:%d: Missing node %s" % (src, root.line, root.column, tag.tagname))

            if tag.wrapper and _root:
                root.removeChild(_root)

            if tag.plural:
                setattr(self, tag.name, vals)
            elif vals != []:
                setattr(self, tag.name, vals[0])
            else:
                setattr(self, tag.name, None)

        if len(root.childNodes) > 0 and \
                hasattr(root.childNodes[0], 'wholeText'):
            self.wholeText = root.childNodes[0].wholeText.rstrip()
        else:
            self.wholeText = ''

        self._extra_xml = root.cloneNode(True)
        self.post_import()

    def parseString(self, s, src='_internal'):
        try:
            expat_parser = init_expat_parser()
            expat_parser.Parse(s)
            dom = expat_tree
        except xml.parsers.expat.ExpatError:
            if src:
                log_error("XML parsing error: %s" % src, exc_info=True)
                sys.exit(1)
            else:
                log_error("XML parsing error", exc_info=True)
                sys.exit(1)

        self._fromdom(dom, dom.childNodes[0], src)

    def parse(self, filename):
        f = open(filename, 'rb')
        expat_parser = init_expat_parser()
        expat_parser.ParseFile(f)
        dom = expat_tree
        self._fromdom(dom, dom.childNodes[0], filename)


class TestXmlObject1(XmlObject):
    val1 = XmlValue(default=7)

class TestXmlObject3(XmlObject):
    myattr = XmlAttribute(default="hello")
    myval = XmlText()

class TestXmlObject2(XmlObject):
    val2 = XmlValue(default=5)
    object1 = XmlNode(TestXmlObject1)
    objs = XmlNodeList(TestXmlObject1)
    myattr = XmlAttribute(default="hello")
    val3 = XmlNode(TestXmlObject3)

if __name__ == "__main__":
    o1a = TestXmlObject1()
    o1b = TestXmlObject1()
    o2a = TestXmlObject2()
    o3a = TestXmlObject3()
    o1b.val1 = 13
    o2a.myattr="goodbye"
    o2a.object1 = o1a
    o2a.objs = [o1a, o1b]
    o2a.val3 = o3a
    o2a.val3.myattr = "goodbye"
    o2a.val3.myval = "bar"
    s = o2a.toxml("test")
    print(s)
    o2b = TestXmlObject2()
    o2b.parseString(s)
    print((o2b.toxml("test")))
