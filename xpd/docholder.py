from xmlobject import XmlObject, XmlValue, XmlNode, XmlNodeList, XmlAttribute, XmlValueList


class DHDocumentLink(XmlObject):
    partnum = XmlAttribute()
    issue = XmlAttribute()

class DHSection(XmlObject):
    title = XmlAttribute()
    description = XmlValue()
    documents = XmlNodeList(DHDocumentLink,wrapper='documents')

class DocumentHolder(XmlObject):
    introduction = XmlValue(attrs={'format':'textile'})
    sections = XmlNodeList(DHSection)

if __name__ == "__main__":
    dh = DocumentHolder()
    dh.parse("test_dh.xml")
    print dh.toxml("DocumentHolder")
