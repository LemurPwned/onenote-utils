import os
import string
from io import StringIO

from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser


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
    allowable_set = string.ascii_letters + string.punctuation + " " + "\n"

    # this removes line carry
    text = text.replace("-\n", "")
    text = text.replace(".\n", ". ").replace(". \n",
                                             ". ").replace("fig.??", "")
    text = text.replace("\n", " ").replace("  ", " ")
    if remove_numbers:
        text = "".join(filter(lambda x: x in allowable_set, text))
    return text.lower()
