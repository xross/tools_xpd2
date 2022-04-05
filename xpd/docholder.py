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
    sections = XmlNodeList(DHSection,wrapper='sections')

    def get_section(self, name):
        for section in self.sections:
            if section.title == name:
                return section
        return None

if __name__ == "__main__":
    dh = DocumentHolder()
    dh.parse("test_dh.xml")
    print(dh.toxml("DocumentHolder"))
