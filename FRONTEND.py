# -*- coding: utf-8 -*-
"""
Created on Wed Jan 31 14:17:48 2024

@author: jack.appleby
"""

import streamlit as st
import fitz
from operator import itemgetter
import re


def fonts(doc, granularity=False):
    """Extracts fonts and their usage in PDF documents.
    :param doc: PDF document to iterate through
    :type doc: <class 'fitz.fitz.Document'>
    :param granularity: also use 'font', 'flags' and 'color' to discriminate text
    :type granularity: bool
    :rtype: [(font_size, count), (font_size, count}], dict
    :return: most used fonts sorted by count, font style information
    """
    styles = {}
    font_counts = {}

    for page in doc:
        blocks = page.get_text("dict",sort=True)["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b['type'] == 0:  # block contains text
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        if granularity:
                            identifier = "{0}_{1}_{2}_{3}".format(s['size'], s['flags'], s['font'], s['color'])
                            styles[identifier] = {'size': s['size'], 'flags': s['flags'], 'font': s['font'],
                                                  'color': s['color']}
                        else:
                            identifier = "{0}".format(s['size'])
                            styles[identifier] = {'size': s['size'], 'font': s['font']}

                        font_counts[identifier] = font_counts.get(identifier, 0) + 1  # count the fonts usage

    font_counts = sorted(font_counts.items(), key=itemgetter(1), reverse=True)

    if len(font_counts) < 1:
        raise ValueError("Zero discriminating fonts found!")

    return font_counts, styles


def font_tags(font_counts, styles):
    """Returns dictionary with font sizes as keys and tags as value.

    :param font_counts: (font_size, count) for all fonts occuring in document
    :type font_counts: list
    :param styles: all styles found in the document
    :type styles: dict

    :rtype: dict
    :return: all element tags based on font-sizes
    """
    p_style = styles[font_counts[0][0]]  # get style for most used font by count (paragraph)
    p_size = p_style['size']  # get the paragraph's size

    # sorting the font sizes high to low, so that we can append the right integer to each tag
    font_sizes = []
    for (font_size, count) in font_counts:
        font_sizes.append(float(font_size))
    font_sizes.sort(reverse=True)

    # aggregating the tags for each font size
    idx = 0
    size_tag = {}
    for size in font_sizes:
        idx += 1
        if size == p_size:
            idx = 0
            size_tag[size] = '<p>>'
        if size > p_size:
            size_tag[size] = '<h{0}>>'.format(idx)
        elif size < p_size:
            size_tag[size] = '<s{0}>>'.format(idx)

    return size_tag

def headers_para(doc_page, size_tag):
    """Scrapes headers & paragraphs from PDF and return texts with element tags.

    :param doc: PDF document to iterate through
    :type doc: <class 'fitz.fitz.Document'>
    :param size_tag: textual element tags for each size
    :type size_tag: dict

    :rtype: list
    :return: texts with pre-prended element tags
    """
    headers_para_out = []  # list with headers and paragraphs
    first = True  # boolean operator for first header
    previous_s = {}  # previous span

    blocks = doc_page.get_text("dict")["blocks"]
    for b in blocks:  # iterate through the text blocks
        if b['type'] == 0:  # this block contains text

            # REMEMBER: multiple fonts and sizes are possible IN one block

            block_string = ""  # text found in block
            for l in b["lines"]:  # iterate through the text lines
                for s in l["spans"]:  # iterate through the text spans
                    if s['text'].strip():  # removing whitespaces:
                        if first:
                            previous_s = s
                            first = False
                            block_string = size_tag[s['size']] + s['text']
                        else:
                            if s['size'] == previous_s['size']:

                                if block_string and all((c == "|") for c in block_string):
                                    # block_string only contains pipes
                                    block_string = size_tag[s['size']] + s['text']
                                if block_string == "":
                                    # new block has started, so append size tag
                                    block_string = size_tag[s['size']] + s['text']
                                else:  # in the same block, so concatenate strings
                                    block_string += " " + s['text']

                            else:
                                headers_para_out.append(block_string)
                                block_string = size_tag[s['size']] + s['text']

                            previous_s = s

                # new block started, indicating with a pipe
                block_string += "|"

            headers_para_out.append(block_string)

    return headers_para_out

def get_page_title(headers_para_out):
    headers=[x for x in headers_para_out if x.startswith("<h")]
    
    if headers:
        pattern = r'<h(\d+)>>'
        #pattern = r'<h\d+>>(.*)'

        numbers = [int(re.search(pattern, s).group(1)) if re.search(pattern, s) else 0 for s in headers]
        lowest_number_index = numbers.index(min(numbers))
        string_with_lowest_number = headers[lowest_number_index]
        title_split=" ".join([x.replace("|","") for x in re.split(pattern,string_with_lowest_number) if len(x)>0 and x!=str(min(numbers))])
    else:
        title_split=""

    return title_split

    
def get_titles_for_pages(page_no,page,size_tags,all_pdf):
    headers_para_out=headers_para(page, size_tags)
    title=get_page_title(headers_para_out)
    
    all_pdf[page_no].update({'page_title':title}) 
    
    return all_pdf


def extract_text_from_PDF(pdf_file,uploaded_file_name):
    
    doc = fitz.open(stream=pdf_file.read(),filetype="pdf")
    doc_fonts,doc_styles=fonts(doc, granularity=False)
    size_tags=font_tags(doc_fonts, doc_styles)
    
    all_pdf={}
    for page in doc: 
      all_pdf[page.number]={'from_file':uploaded_file_name}
      all_pdf=get_titles_for_pages(page.number,page,size_tags,all_pdf)

    ##need to add part where if content == title domnt include in content

      text = page.get_text(sort=True).replace("\n"," ")
      all_pdf[page.number].update({'page_content':text})
      
    pdf_list=[v for k,v in all_pdf.items()] 
    
    return pdf_list




st.title("Testing app service")

uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
uploaded_file_copy = copy.deepcopy(uploaded_file)

if uploaded_file:
    text_out=extract_text_from_PDF(uploaded_file,"test1")
    
    st.markdown(text_out)
    

