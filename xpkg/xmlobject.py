import xml.dom.minidom
from xml.dom.minidom import parse, parseString
import sys

def pp_xml(dom, elem, indent=''):
    if hasattr(elem,"tagName"):
        s = indent + '<' + str(elem.tagName)
        try:
            for (key, value) in elem.attributes.items():
                s += " %s = \"%s\"" % (key, value.strip())
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
    elif hasattr(elem,"wholeText"):
        s = str(elem.wholeText).strip()
    else:
        s = indent + '<!--' + str(elem.nodeValue) + '-->\n'

    return s
    

def num (s):
    try:
        return int(s)
    except exceptions.ValueError:
        return float(s)

class XmlValue(object):
    def __init__(self, tagname=None, default=None):
        self.default=default
        self.tagname = tagname

class XmlValueList(object):
    def __init__(self, tagname=None):
        self.tagname = tagname

class XmlAttribute(object):
    def __init__(self, attrname=None, default=None):
        self.default=default
        self.attrname=attrname

class XmlNode(object):
    def __init__(self, typ, tagname=None):
        self.typ = typ
        self.tagname=tagname

class XmlNodeList(object):
    def __init__(self, typ, tagname=None):
        self.typ = typ
        self.tagname = tagname

class XmlTag(object):
    
    def __init__(self, name, tagname=None, typ=str, plural=False):
        self.name = name
        if tagname:
            self.tagname = tagname
        else:
            self.tagname = name
        self.typ = typ
        self.plural = plural

class XmlAttr(object):
    
    def __init__(self, name, attrname=None):
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
            val = getattr(self,attr)
            if isinstance(val, XmlValue):    
                if val.tagname == None:
                    val.tagname = attr
                self.tags.append(XmlTag(attr, tagname=val.tagname))
                setattr(self, attr, val.default)
            elif isinstance(val, XmlNode):
                if val.tagname == None:
                    val.tagname = attr
                self.tags.append(XmlTag(attr, tagname=val.tagname, typ=val.typ))
                setattr(self, attr, None)
            elif isinstance(val, XmlNodeList):
                if val.tagname == None:
                    if attr[-1] == 's':
                        val.tagname = attr[:-1]
                    else:
                        val.tagname = attr
                self.tags.append(XmlTag(attr,tagname=val.tagname,
                                        typ=val.typ,plural=True))
                setattr(self, attr, [])
            elif isinstance(val, XmlValueList):
                if val.tagname == None:
                    if attr[-1] == 's':
                        val.tagname = attr[:-1]
                    else:
                        val.tagname = attr
                self.tags.append(XmlTag(attr,tagname=val.tagname,
                                        typ=str,plural=True))
                setattr(self, attr, [])
            elif isinstance(val, XmlAttribute):
                if val.attrname == None:
                    val.attrname = attr
                self.attrs.append(XmlAttr(attr,attrname=val.attrname))
                setattr(self, attr, val.default)
                                                                   

    def pre_export(self):
        pass

    def post_import(self):
        pass


    def _add_child(self, dom, rootelem, name, val):
        if isinstance(val, XmlObject):
            elem = dom.createElement(name)
            val.pre_export()
            val._add_attributes(dom, elem)
            val._add_children(dom, elem)
            val._add_extra_xml(dom, elem)
            rootelem.appendChild(elem)
        elif hasattr(val, '__iter__'):
                for x in val:
                    self._add_child(dom, rootelem, name, x)
        elif val != None:
            elem = dom.createElement(name)
            text = dom.createTextNode(str(val))
            elem.appendChild(text)
            rootelem.appendChild(elem)


    def _add_children(self, dom, rootelem):
        for tag in self.tags:
            val = getattr(self, tag.name)
            self._add_child(dom, rootelem, tag.tagname, val)
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
                
            
        
    def toxml(self, root, pretty=True):
        self.pre_export()
        dom = xml.dom.minidom.parseString("<%s/>"%root)
        rootelem = dom.getElementsByTagName(root)[0]
        self._add_attributes(dom, rootelem)
        self._add_children(dom, rootelem)
        self._add_extra_xml(dom, rootelem)
        return '<?xml version=\"1.0\" ?>\n' + pp_xml(dom, rootelem).strip()
#        if pretty:
#            return dom.toprettyxml()
#        else:
#            return dom.toxml()


    def _fromdom(self, dom, root):
        for attr in self.attrs:
            setattr(self, attr.name,root.getAttribute(attr.attrname))

        for tag in self.tags:                       
            vals = []
            for x in root.childNodes:
                if hasattr(x,"tagName") and x.tagName == tag.tagname:
                    if tag.plural and hasattr(tag,"typ") and tag.typ == str:
                        current_vals = getattr(self, tag.name)
                        if not current_vals:
                            current_vals = []
                        
                        val = x.childNodes[0].wholeText
                        val = val.strip()

                        vals = current_vals + [val]                    
                    elif hasattr(tag,"typ") and issubclass(tag.typ, XmlObject):
                        val = tag.typ(parent=self)
                        val._fromdom(dom, x)
                        vals.append(val)
                    else:
                        if not x.hasChildNodes:
                            sys.stderr.write("Parse error - expected %s to have content\n"%tag.tagname)
                            exit(1)
                        if not hasattr(x.childNodes[0],"wholeText"):
                            sys.stderr.write("Parse error - expected %s to have text content\n"%tag.tagname)
                            exit(1)
                            
                        val = x.childNodes[0].wholeText
                        val = val.strip()
                        # Convert to a number if possible
                        try:
                            val = num(x)
                        except:
                            pass
                        if val in ["False","false","F","0"]:
                            val = False
                        if val in ["True","true","T","1"]:
                            val = True

                        vals.append(val)
                    root.removeChild(x)

            if hasattr(root,'wholeText'):
                self.wholeText = root.wholeText

            if tag.plural:
                setattr(self, tag.name, vals)
            elif vals != []:
                setattr(self, tag.name, vals[0])
            else:
                setattr(self, tag.name, None)


        self._extra_xml = root.cloneNode(True)
        self.post_import()

    def parseString(self, s):
        dom = xml.dom.minidom.parseString(s)
        self._fromdom(dom, dom.childNodes[0])

    def parse(self, f):
        dom = xml.dom.minidom.parse(f)
        self._fromdom(dom, dom.childNodes[0])



class TestXmlObject1(XmlObject):
    val1 = XmlValue(default=7)
    
class TestXmlObject2(XmlObject):
    val2 = XmlValue(default=5)
    object1 = XmlNode(TestXmlObject1)
    objs = XmlNodeList(TestXmlObject1)
    myattr = XmlAttribute(default="hello")

if __name__ == "__main__":
    o1a = TestXmlObject1()
    o1b = TestXmlObject1()
    o2a = TestXmlObject2()
    o1b.val1 = 13
    o2a.myattr="goodbye"
    o2a.object1 = o1a
    o2a.objs = [o1a,o1b]
    s = o2a.toxml("test")
    print s
    o2b = TestXmlObject2()
    o2b.parseString(s)
    print o2b.toxml("test")
