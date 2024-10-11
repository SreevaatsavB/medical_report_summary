import streamlit as st
import PyPDF2
import io
import base64
import json
from get_pdf_ocr import process_files_in_parallel
from get_claude_response import complete_chat
import os 
from pdf2image import convert_from_path
import re
from pdf2image import convert_from_bytes


def save_images_pdf(pdf_path, output_dir):

    pdf_filename = pdf_path.split(".pdf")[0]
    # pdf_filename = os.path.splitext(pdf_file)[0]
    
    output_folder = os.path.join(output_dir, pdf_filename)
    os.makedirs(output_folder, exist_ok=True)
    
    images = convert_from_path(pdf_path)
    
    if images:
        for i, image in enumerate(images, start=0):
            image.save(os.path.join(output_folder, f'{i}.png'), 'PNG')
    
    print(f'Images from {pdf_path} saved in {output_folder}')
    

def get_numeric_value(filename):
    numbers = re.findall(r'\d+', filename)
    return int(numbers[0]) if numbers else 0

def generate_summary(text):
    prompt = f'''You are working for an orthopedic doctor. Your task is to summarize medical records of a patient before the doctor sees them. The summary will be used in a dashboard for quick reference.

Generate a summary so that the doctor quickly understands the patient. Also, ensure that we can reference back to the original document if required. Make sure it is very useful to the orthopaedic.

Analyze the following medical records and create a JSON-formatted summary. Each entry in the JSON should represent a key point , a detailed information about the key point, along with its corresponding page number(s). Format the output as follows:

{{
  "summary": [
    {{
      "point": "Brief description of the key point",
      "description": "Detailed observations from the medical records about the key point",
      "pages": [list of page numbers where this information is found]
    }},
    
    More entries...
  ]
}}

Medical records:
{text}

Provide only the JSON-formatted summary, with no additional text before or after. Do not hallucinate or add any new information which is not present in the given medical records.
'''

    return complete_chat(prompt)

# def display_pdf_page(pdf_file, page_number):
#     pdf_reader = PyPDF2.PdfReader(pdf_file)
#     if page_number < 1 or page_number > len(pdf_reader.pages):
#         st.error(f"Invalid page number. The PDF has {len(pdf_reader.pages)} pages.")
#         return
#     pdf_writer = PyPDF2.PdfWriter()
#     pdf_writer.add_page(pdf_reader.pages[page_number - 1])
#     pdf_bytes = io.BytesIO()
#     pdf_writer.write(pdf_bytes)
#     pdf_bytes.seek(0)
#     base64_pdf = base64.b64encode(pdf_bytes.read()).decode('utf-8')
#     pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
#     st.markdown(pdf_display, unsafe_allow_html=True)

def display_pdf_page(pdf_file, page_number):
    try:
        # Convert PDF to image
        images = convert_from_bytes(pdf_file.getvalue(), first_page=page_number, last_page=page_number)
        
        if images:
            # Convert PIL Image to bytes
            img_byte_arr = io.BytesIO()
            images[0].save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Display the image
            st.image(img_byte_arr, caption=f'Page {page_number}', use_column_width=True)
        else:
            st.error(f"Failed to render page {page_number}. Please check if the PDF file is valid.")
    except Exception as e:
        st.error(f"An error occurred while displaying the PDF: {str(e)}")
        st.error("Please ensure the PDF file is not corrupted and try again.")
        st.error("If the issue persists, make sure pdf2image and its dependencies are correctly installed.")

def main():
    st.title("Orthopedic Patient Summary")

    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_file is not None:
        # with open("temp.pdf", "wb") as f:
        #     f.write(uploaded_file.getbuffer())

        filename = uploaded_file.name

        with open(filename, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # filename

        if filename not in st.session_state:
            st.session_state[filename] = {}

       
        if "saved_files" not in st.session_state[filename]:
            with st.spinner('Processing data ...'):
                save_images_pdf(filename, "pdf_files")
                st.session_state[filename]["saved_files"] = True
        
        pdf_imgs_path = "pdf_files" + "/" + filename.split(".pdf")[0]

        pdf_imgs = os.listdir(pdf_imgs_path)
        complete_paths = [os.path.join(pdf_imgs_path, img) for img in pdf_imgs]


        # image_paths = os.listdir(pdf_imgs_path)       
        # Sort image paths
        sorted_paths = sorted(complete_paths, key=lambda x: get_numeric_value(os.path.basename(x)))

        # st.write(complete_paths)
        print(complete_paths)
        # print(sorted_paths)
        if "ocr_text" not in st.session_state[filename]:
            with st.spinner('Processing data ...'):
                ocr_text = process_files_in_parallel(sorted_paths)
                st.session_state[filename]['ocr_text'] = ocr_text

        else:
            ocr_text = st.session_state[filename]["ocr_text"]

        if "summary_json" not in st.session_state[filename]:
            with st.spinner('Getting important summaries ...'):
                summary_json = generate_summary(ocr_text)
                st.session_state[filename]["summary_json"] = summary_json

        else:
            summary_json = st.session_state[filename]["summary_json"]

    
        try:
            summary_data = json.loads(summary_json)
            
            st.markdown("### Patient Summary")
            for item in summary_data['summary']:
                st.subheader(item['point'])
                st.write(item['description'])
                
                # page_refs = ", ".join([f"[Page {page}]" for page in item['pages']])
                # st.markdown(f"**References:** {page_refs}")
                
                for page in item['pages']:
                    if st.button(f"View Page {page}", key=f"{item['point']}_{page}"):
                        display_pdf_page(uploaded_file, page)
                
                st.markdown("---")  # Add a separator between points
        
            # st.write(st.session_state)
        except json.JSONDecodeError:
            st.error("Error parsing the summary. Please try again.")



if __name__ == "__main__":
    main()
    
