import zipfile
import xml.etree.ElementTree as ET
import sys
import os

def extract_text(docx_path):
    try:
        with zipfile.ZipFile(docx_path) as zf:
            xml_content = zf.read('word/document.xml')
        
        tree = ET.fromstring(xml_content)
        namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        
        text_parts = []
        for p in tree.findall('.//w:p', namespace):
            texts = [node.text for node in p.findall('.//w:t', namespace) if node.text]
            if texts:
                text_parts.append(''.join(texts))
            else:
                text_parts.append('') # Paragraph break
        
        return '\n'.join(text_parts)
    except Exception as e:
        return f"Error reading {docx_path}: {e}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_docx.py <file1> <file2> ...")
        sys.exit(1)
        
    for file_path in sys.argv[1:]:
        print(f"--- START OF {os.path.basename(file_path)} ---")
        print(extract_text(file_path))
        print(f"--- END OF {os.path.basename(file_path)} ---")
