"""Translate known interface text on the server while preserving user-authored content."""
from html import escape
from html.parser import HTMLParser
import re

class InterfaceHTML(HTMLParser):
    def __init__(self,translate):
        super().__init__(convert_charrefs=False);self.translate=translate;self.output=[];self.stack=[]
    def handle_starttag(self,tag,attrs):
        attributes=dict(attrs);blocked=any(self.stack) or tag in ['script','style','textarea'] or 'data-user-content' in attributes
        if tag not in ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']:self.stack.append(blocked)
        raw=self.get_starttag_text()
        if not blocked:
            for attribute in ['placeholder','aria-label','title']:
                if attributes.get(attribute):
                    original=attributes[attribute];translated=self.translate(original)
                    if translated!=original:raw=re.sub(r'('+attribute+r'\s*=\s*)([\'"])(.*?)\2',lambda m:m[1]+m[2]+escape(translated,quote=True)+m[2],raw,count=1,flags=re.S)
        self.output.append(raw)
    def handle_startendtag(self,tag,attrs):self.output.append(self.get_starttag_text())
    def handle_endtag(self,tag):
        if self.stack:self.stack.pop()
        self.output.append('</'+tag+'>')
    def handle_data(self,data):
        if not any(self.stack) and data.strip():
            value=data.strip();translated=self.translate(value)
            if value!=translated:data=data.replace(value,escape(translated,quote=False),1)
        self.output.append(data)
    def handle_entityref(self,name):self.output.append('&'+name+';')
    def handle_charref(self,name):self.output.append('&#'+name+';')
    def handle_comment(self,data):self.output.append('<!--'+data+'-->')
    def handle_decl(self,data):self.output.append('<!'+data+'>')


def localize_html(source,translate):
    parser=InterfaceHTML(translate);parser.feed(source);parser.close();return ''.join(parser.output)
