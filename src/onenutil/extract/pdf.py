import os
import re
import string
from io import StringIO

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

compiled_word = re.compile(r'[^\W\d\-]*$')
compiled_whitespace = re.compile(r'\s+')


def extract_text_pdf(filename: os.PathLike) -> str:
    """Extract text from a pdf file
    :param filename: pdf path
    :returns: extracted text from a pdf"""
    output_string = StringIO()
    try:
        with open(filename, 'rb') as in_file:
            parser = PDFParser(in_file)
            doc = PDFDocument(parser)
            rsrcmgr = PDFResourceManager()
            device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
            interpreter = PDFPageInterpreter(rsrcmgr, device)
            for page in PDFPage.create_pages(doc):
                interpreter.process_page(page)
    except PermissionError:
        print(f"\nPermission denied: {filename}\n")
        return ""
    return output_string.getvalue()


def format_pdf(text: str, remove_numbers: bool = True) -> str:
    """Remove numbers and non-letters from the string
    :param text: text to format
    :param remove_numbers: remove numbers from the text
    :returns: formatted text"""

    # this removes line carry
    text = text.replace("-\n", "").replace("- \n",
                                           "").replace("-",
                                                       " ").replace("\"", "")
    text = text.replace(".\n", ". ").replace(". \n",
                                             ". ").replace("fig.??", "")
    # substitute multiple whitespace to one
    text = compiled_whitespace.sub(' ', text)
    tokens = text.strip().split()
    clean_tokens = [t for t in tokens if compiled_word.match(t)]
    text = ' '.join(clean_tokens)
    return text
