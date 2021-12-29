from io import StringIO

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
import os 


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
