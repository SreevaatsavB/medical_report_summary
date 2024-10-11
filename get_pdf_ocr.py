from glob import glob
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
import pandas as pd
import json
import concurrent.futures
import os
import re
from pdf2image import convert_from_path
import streamlit as st


endpoint = st.secrets["AZURE_ENDPOINT"]
key = st.secrets["AZURE_KEY"]



def get_table_df(tab_dict):
    max_rows, max_cols = tab_dict["row_count"], tab_dict["column_count"]

    table_list = [[" " for j in range(max_cols)] for i in range(max_rows)]

    for cell in tab_dict["cells"]:

        column_index = cell["column_index"]
        row_index = cell["row_index"]

        table_list[row_index][column_index] = cell["content"]

    df_table = pd.DataFrame(table_list)
    df_table = df_table.to_string(index=False)

    return '<table> '+df_table +' </table>'


def binary_search(arr, target):
    left = 0
    right = len(arr) - 1
    index = -1

    while left <= right:
        mid = (left + right) // 2

        if arr[mid] == target:
            return mid

        elif arr[mid] > target:
            index = mid
            right = mid - 1

        else:
            left = mid + 1

    return index


def get_text(text_feilds):

    string = ""

    for i in range(len(text_feilds)):

        if text_feilds[i]["role"] in ["title", "sectionHeading", "pageHeader"]:
            string += "<H1> " + text_feilds[i]["content"] + " </H1> "

        else:
            string += text_feilds[i]["content"]

        string += "\n"

    return string



def get_df_string(temp_df):

    temp_str_list = temp_df.to_csv(header=True, index=True).strip('\n').split('\n')

    str_final = ""

    for s in temp_str_list:
        str_final += s
        str_final += "\n"

    return str_final


def filter_by_offset(text_feilds, tables):

    output = []

    text_offsets = []
    for txt_dic in text_feilds:
        text_offsets.append((txt_dic["spans"][0]["offset"]))

    prev_tab_end = -1

    if len(tables) == 0:

        texts_enclosed = []
        str_text = get_text(text_feilds)
        output.append(str_text)


    else:

        for tab in tables:

            spans = tab["spans"]
            spans_sorted = sorted(spans, key=lambda x: x['offset'])


            for span in spans_sorted:
                curr_tab_offset = span["offset"]
                curr_tab_end = curr_tab_offset + span["length"]

                idx_start_tab = binary_search(text_offsets, curr_tab_offset)
                idx_end_tab = binary_search(text_offsets, curr_tab_end)

                si = prev_tab_end + 1
                ei = idx_start_tab

                texts_enclosed = []

                for i in range(si, ei):
                    texts_enclosed.append(text_feilds[i])

                str_text = get_text(texts_enclosed)
                output.append(str_text)
                prev_tab_end = idx_end_tab

            output.append(get_table_df(tab))

        global_max_ind = len(text_offsets)-1

        if prev_tab_end == -1:
            final_str = ""
            for op_item in output:

                if not isinstance(op_item, str):
                    str_df = get_df_string(op_item)
                    final_str += str_df


                else:

                    final_str += op_item
                final_str += "\n"

            return final_str

        si = prev_tab_end
        ei = global_max_ind

        texts_enclosed = []

        for i in range(si, ei+1):
            texts_enclosed.append(text_feilds[i])

        str_text = get_text(texts_enclosed)
        output.append(str_text)


    final_str = ""

    for op_item in output:

        if not isinstance(op_item, str):

            str_df = get_df_string(op_item)

            final_str += str_df

        else:

            final_str += op_item

        final_str += "\n"

    return final_str




def get_outputs_processed(file_path):

    with open(file_path, 'rb') as fopen:
        file = fopen.read()

    document_analysis_client = DocumentAnalysisClient(
    endpoint=endpoint, credential=AzureKeyCredential(key)
    )

    poller = document_analysis_client.begin_analyze_document("prebuilt-layout", file)
    result = poller.result()

    resutls_dict = result.to_dict()

    text_feilds = resutls_dict["paragraphs"]
    tables = resutls_dict["tables"]

    op = filter_by_offset(text_feilds, tables)

    return op



def process_files_in_parallel(file_paths):
    # Sort file paths based on numeric value in the filename
    def get_numeric_value(filename):
        numbers = re.findall(r'\d+', filename)
        return int(numbers[0]) if numbers else 0

    sorted_file_paths = sorted(file_paths, key=lambda x: get_numeric_value(os.path.basename(x)))

    # Use ThreadPoolExecutor to run get_outputs_processed in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit tasks and store futures with their index
        future_to_index = {executor.submit(get_outputs_processed, file): idx 
                           for idx, file in enumerate(sorted_file_paths)}

        # Prepare results list with the correct size
        results = [None] * len(sorted_file_paths)

        # Collect results maintaining the original order
        for future in concurrent.futures.as_completed(future_to_index):
            idx = future_to_index[future]
            try:
                result = future.result()
                result = result.replace(' page ', ' ').replace(' Page ', ' ')
                result = f'here is pagenumber: {idx+1} {result}\n'
                results[idx] = result
                
            except Exception as exc:
                print(f'File at index {idx} generated an exception: {exc}')
                results[idx] = f'here is pagenumber: {idx+1} [Error processing file]\n'

    # Join all results, filtering out any None values
    inputs = ''.join(filter(None, results))
    return inputs



