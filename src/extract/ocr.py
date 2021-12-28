import cv2
from typing import Iterable, Tuple, List
import matplotlib.pyplot as plt
import numpy as np
import ocrmypdf
import glob
import os
import uuid
import tempfile
from PIL import Image
from pdf2image import convert_from_path
from transformers import TrOCRProcessor, VisionEncoderDecoderModel


def create_model():
    processor = TrOCRProcessor.from_pretrained(
        "microsoft/trocr-base-handwritten")
    model = VisionEncoderDecoderModel.from_pretrained(
        "microsoft/trocr-base-handwritten")
    return processor, model


def ocr_from_splits(img: np.ndarray,
                    splits: List[Tuple[int, int]],
                    processor: TrOCRProcessor,
                    model: VisionEncoderDecoderModel,
                    pad: int = 10) -> Iterable[str]:
    """Having line splits for a note, try to obtain OCR"""
    for i in range(0, len(splits)-1):
        cut = img[splits[i][1]-pad:splits[i+1][1]+pad]
        pixel_values = processor(cut, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values)
        generated_text = processor.batch_decode(
            generated_ids, skip_special_tokens=True)[0]
        yield generated_text


def compute_ocr_from_note(pdf_filename: os.PathLike, metadata_folder: os.PathLike):
    """Compute the OCR for a single note"""
    pages = convert_from_path(pdf_filename, 500)
    savename = os.path.join(
        metadata_folder, os.path.basename(pdf_filename)
    )
    note_contents = []
    with tempfile.TemporaryDirectory() as tmpdirname:
        for i, page in enumerate(pages):
            tfn = str(uuid.uuid4())
            fn = os.path.join(tmpdirname, f'{tfn}.jpg')
            page.save(fn)
            img = Image.open(fn)
            splits = y_intensity_histogram(
                img
            )
            content = ocr_from_splits(
                img, splits
            )
            note_contents.append(content)
    with open(savename, 'w') as f:
        f.write("\n".join(note_contents))


def transform_folder(src_folder: os.PathLike,
                     save_folder: os.PathLike):
    for fn in glob.glob(os.path.join(src_folder, "*.pdf")):
        savename = os.path.join(save_folder, os.path.basename(fn))
        ocrmypdf.ocr(
            fn, savename,
            deskew=True, force_ocr=True
        )


def show_img(img):
    fig, ax = plt.subplots(dpi=400)
    ax.axis("off")
    ax.imshow(img)


def boost_contrast(input_file):
    """Optional contrast boosting in the LAB."""
    img = cv2.imread(input_file)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    final = cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
    final = cv2.cvtColor(final, cv2.COLOR_RGB2GRAY)
    return final


def y_intensity_histogram(img, min_width=60, display=False):
    """Make intensity-based histogram splits"""
    h, w = img.shape
    # split h into many tiny pieces
    k = 100
    piece_stride = h // k
    array_hist = [a.sum() for a in np.array_split(img, k)]
    # offset by the smallest value
    array_hist = [x - min(array_hist) for x in array_hist]
    x = np.asarray([i*piece_stride for i in range(k)])

    # sep rule is 3/4 of max value
    text_sections = np.argwhere(array_hist >= 0.75*max(array_hist)).ravel()
    # we merge text sections into longer pieces than piece stride
    merged_sections = []
    start = 0
    for i in range(len(text_sections)-1):
        if text_sections[i] + 1 == text_sections[i+1]:
            continue
        merged_sections.append((
            x[start], x[text_sections[i]] + piece_stride
        ))
        start = text_sections[i+1]
    if display:
        _, ax = plt.subplots(dpi=200)
        for (start, stop) in merged_sections:
            if stop - start < min_width:
                continue
            ax.hlines(y=0.5*max(array_hist), xmin=start, xmax=stop, color='r')

        _ = ax.bar(x, array_hist, width=piece_stride//2)
        ax.set_xlabel("Frame height")
        ax.set_ylabel("Intensity")
    return array_hist, merged_sections


def draw_lines(img, splits):
    """Visualise the line splits"""
    x1, x2 = 0, img.shape[1]
    for _, stop in splits:
        cv2.line(img, (x1, stop-10), (x2, stop+10), (255, 0, 0), thickness=3)

    show_img(img)
    return img
