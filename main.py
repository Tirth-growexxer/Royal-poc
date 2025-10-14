import pdfkit
import os
import re
import base64
import requests
from io import BytesIO
# from secret_manager import SecretManager
from secret_manager_local import SecretManager
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import JSONResponse
from datetime import datetime
import os
import traceback
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from email.message import EmailMessage
import smtplib



sm = SecretManager()
# Pass a sensible default so get_secret never returns None unexpectedly
secrets = sm.get_secret(default={})


def html_to_pdf(html_content, output_filename):
    print(f"Output file: {output_filename}")
    
    try:
        # Convert HTML string to PDF
        pdfkit.from_string(html_content, output_filename)
        print(f"PDF generated successfully: {output_filename}")
        return output_filename
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return None

def convert_image_url_to_base64(url, timeout=20):
    """
    Download image from URL and convert to base64 data URI.
    
    Args:
        url (str): URL of the image
        timeout (int): Request timeout in seconds
    
    Returns:
        str: Base64 data URI or original URL if conversion fails
    """
    try:
        # Download the image
        response = requests.get(url, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()
        
        # Get content type
        content_type = response.headers.get('content-type', 'image/png')
        
        # Convert to base64
        image_data = base64.b64encode(response.content).decode('utf-8')
        
        # Create data URI
        data_uri = f"data:{content_type};base64,{image_data}"
        return data_uri
        
    except Exception as e:
        print(f"Error converting image URL to base64: {str(e)}")
        print(f"Keeping original URL: {url}")
        return url


def process_html_images(html_content):
    """
    Find all image tags with URL sources and convert them to base64.
    
    Args:
        html_content (str): HTML content with image tags
    
    Returns:
        str: HTML content with images converted to base64
    """
    # Regex pattern to find img tags with src containing http/https URLs
    img_pattern = r'<img\s+([^>]*?)src=["\']([^"\'>]+)["\']([^>]*?)>'
    
    def replace_image(match):
        before_src = match.group(1)
        src_url = match.group(2)
        after_src = match.group(3)
        
        # Check if it's a URL (http or https)
        if src_url.startswith('http://') or src_url.startswith('https://'):
            print(f"Found image URL in HTML: {src_url}")
            # Convert to base64
            base64_src = convert_image_url_to_base64(src_url)
            return f'<img {before_src}src="{base64_src}"{after_src}>'
        else:
            # Not a URL, keep as is
            return match.group(0)
    
    # Replace all image URLs with base64
    processed_html = re.sub(img_pattern, replace_image, html_content, flags=re.IGNORECASE)
    return processed_html


def get_html_content(data_dict, template_file_path="template.txt"):
    """
    Load HTML template from file and fill it with dynamic data.
    
    Args:
        data_dict (dict): Dictionary containing data to fill in the template placeholders
        template_file_path (str): Path to the HTML template file
    
    Returns:
        str: HTML content with filled placeholders
    """
    
    # Process data_dict to convert image URLs to base64 in dynamic data
    processed_data_dict = {}
    for key, value in data_dict.items():
        if isinstance(value, str) and ('<img' in value.lower()):
            # This field contains HTML with potential images
            processed_data_dict[key] = process_html_images(value)
        else:
            processed_data_dict[key] = value
    
    # Try to load template from file
    if os.path.exists(template_file_path):
        print(f"Reading HTML template from file: {template_file_path}")
        try:
            with open(template_file_path, 'r', encoding='utf-8') as file:
                template_content = file.read()
            print("HTML template loaded from file successfully")
            
            # Fill the template with data using format()
            filled_html = template_content.format(**processed_data_dict)
            print("Template filled with dynamic data successfully")
            return filled_html
            
        except Exception as e:
            print(f"Error reading HTML template file: {str(e)}")
            print("Template file not found or error occurred")
            return None
    else:
        print(f"Template file '{template_file_path}' not found")
        return None


def remove_paragraph_tags(html_content):
    """
    Remove ALL <p> and </p> tags while keeping all other HTML tags intact.
    This function removes all paragraph tags, including nested ones.
    
    Args:
        html_content (str): HTML content that may contain paragraph tags
    
    Returns:
        str: HTML content with ALL paragraph tags removed
    """
    if not html_content:
        return html_content
    
    # Remove ALL opening <p> tags (with or without attributes) - use global flag
    content = re.sub(r'<p\b[^>]*>', '', html_content, flags=re.IGNORECASE)
    
    # Remove ALL closing </p> tags - use global flag  
    content = re.sub(r'</p>', '', content, flags=re.IGNORECASE)
    
    # Clean up any extra whitespace that might be left
    content = re.sub(r'\s+', ' ', content)  # Replace multiple spaces with single space
    
    return content.strip()


def get_email_content(data_dict, template_file_path="email_template.txt"):
    """
    Load email template from file and fill it with dynamic data.
    Simple template loading without image processing since emails don't need image URL conversion.
    
    Args:
        data_dict (dict): Dictionary containing data to fill in the template placeholders
        template_file_path (str): Path to the email template file
    
    Returns:
        str: Email HTML content with filled placeholders
    """
    
    # Try to load template from file
    if os.path.exists(template_file_path):
        print(f"Reading email template from file: {template_file_path}")
        try:
            with open(template_file_path, 'r', encoding='utf-8') as file:
                template_content = file.read()
            print("Email template loaded from file successfully")
            
            # Fill the template with data using format()
            filled_html = template_content.format(**data_dict)
            print("Email template filled with dynamic data successfully")
            return filled_html
            
        except Exception as e:
            print(f"Error reading email template file: {str(e)}")
            return None
    else:
        print(f"Email template file '{template_file_path}' not found")
        return None
    
# -------------------------------
# LOAD CONFIG
# -------------------------------
with open('config.json') as config_file:
    config = json.load(config_file)

username = secrets.get("email_username")
password = secrets.get("email_password")

SMTP_SERVER = config['smtp_server']
SENDER_EMAIL = config['sender_email']
SMTP_USERNAME = username
SMTP_PASSWORD = password
SMTP_PORT = config['smtp_port']


# -------------------------------
# EXTRACT DOCUMENT NAME FROM FILENAME
# -------------------------------
def extract_document_name(pdf_filename):
    """
    Basic
    """
    name_part = os.path.splitext(pdf_filename)[0]  # Remove .pdf
    parts = name_part.split(" ", 1)  # Split at first space
    if len(parts) > 1:
        return parts[1]
    return name_part  # fallback if no space

# -------------------------------
# SEND EMAIL WITH ATTACHMENT
# -------------------------------

def create_file_from_base64(file_data, mime_type, file_name):
    """
    Decode base64 file data and create a file with proper extension.
    
    Args:
        file_data (str): Base64 encoded file content
        mime_type (str): MIME type in format "type/extension" (e.g., "application/pdf")
        file_name (str): Base name for the file
    
    Returns:
        str: Full file path with extension, or None if error
    """
    try:
        print(f"Creating file from base64 data...")
        
        # Validate inputs
        if not file_data or not file_name or not mime_type:
            print("Error: Missing required parameters (file_data, file_name, or mime_type)")
            return None
        
        # Extract extension from mime_type (after '/')
        if '/' in mime_type:
            extension = mime_type.split('/')[-1]
        else:
            extension = 'bin'  # Default extension if mime_type is invalid
            print(f"Warning: Invalid MIME type format, using default extension: {extension}")
        
        # Check if filename already has the correct extension
        if file_name.lower().endswith(f'.{extension.lower()}'):
            full_filename = file_name  # Already has correct extension
        else:
            full_filename = f"{file_name}.{extension}"  # Add extension
        
        # Decode base64 data
        file_content = base64.b64decode(file_data)
        
        # Write file to disk
        with open(full_filename, 'wb') as f:
            f.write(file_content)
        
        return full_filename
        
    except Exception as e:
        print(f" Error creating file from base64: {str(e)}")
        return None


def send_email_with_attachment(pdf_path, html_content, reciever_email, request_id, subject='Service Request - Approved', cc_emails=None):
    pdf_filename = os.path.basename(pdf_path)
    document_name = extract_document_name(pdf_filename)
    # Service Request [#RequestID] – Approved

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = reciever_email

    if cc_emails:
        if isinstance(cc_emails, list):
            msg['Cc'] = ', '.join(cc_emails)
        else:
            msg['Cc'] = cc_emails

    # Set the plain text fallback (optional)
    msg.set_content("This email contains HTML content. Please view in an HTML-compatible email client.")

    # Add HTML content
    msg.add_alternative(html_content, subtype='html')

    # Attach PDF
    with open(pdf_path, 'rb') as f:
        file_data = f.read()
    msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=pdf_filename)

    # Send email
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(msg)


def send_email_with_extra_attachment(pdf_path, html_content, reciever_email, request_id, subject='Service Request - Approved', cc_emails=None, extra_file_path=None):
    """
    Send email with PDF attachment plus an additional file attachment.
    This is used for sending to sender_email with the decoded base64 file.
    """
    pdf_filename = os.path.basename(pdf_path)
    document_name = extract_document_name(pdf_filename)

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = reciever_email

    if cc_emails:
        if isinstance(cc_emails, list):
            msg['Cc'] = ', '.join(cc_emails)
        else:
            msg['Cc'] = cc_emails

    # Set the plain text fallback (optional)
    msg.set_content("This email contains HTML content. Please view in an HTML-compatible email client.")

    # Add HTML content
    msg.add_alternative(html_content, subtype='html')

    # Attach main PDF
    with open(pdf_path, 'rb') as f:
        file_data = f.read()
    msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=pdf_filename)

    # Attach extra file if provided
    if extra_file_path and os.path.exists(extra_file_path):
        try:
            extra_filename = os.path.basename(extra_file_path)
            with open(extra_file_path, 'rb') as f:
                extra_file_data = f.read()
            
            # Determine MIME type based on file extension
            file_ext = extra_filename.split('.')[-1].lower()
            if file_ext == 'pdf':
                maintype, subtype = 'application', 'pdf'
            elif file_ext in ['jpg', 'jpeg']:
                maintype, subtype = 'image', 'jpeg'
            elif file_ext == 'png':
                maintype, subtype = 'image', 'png'
            elif file_ext in ['doc', 'docx']:
                maintype, subtype = 'application', 'msword'
            else:
                maintype, subtype = 'application', 'octet-stream'
            
            msg.add_attachment(extra_file_data, maintype=maintype, subtype=subtype, filename=extra_filename)
        except Exception as e:
            print(f"Error attaching extra file: {str(e)}")

    # Send email
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()
        smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
        smtp.send_message(msg)


# FastAPI app
app = FastAPI(title="Employee Service Letter Generator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
    

class approve_letters(BaseModel):
    employee_name: str
    designation: str
    receiver_email: str
    sender_email: str
    cc_emails: list
    request_id: str
    request_type: str
    department: str
    approval_type: str
    transaction_status: str
    book_language: str
    transaction_creator: str
    sender: str
    receiver: str
    transaction_date: str
    transaction_type: str
    confidentiality: str
    subject: str
    file_name: str
    mime_type: str  # Format: "application/pdf", "image/jpeg", etc.
    file_data: str 
    notes_on_request: str # Base64 encoded file content
    # l2: str
    # l3: str

@app.post("/approve_letters")
async def generate_emp_service_letter(details: approve_letters):
    employee_name= details.employee_name
    designation= details.designation
    receiver_email =details.receiver_email
    sender_email = details.sender_email
    cc_emails = details.cc_emails
    request_id = details.request_id
    request_type = details.request_type
    department = details.department
    approval_type = details.approval_type
    transaction_status = details.transaction_status
    book_language = details.book_language
    transaction_creator = details.transaction_creator
    sender = details.sender
    receiver = details.receiver
    transaction_date = details.transaction_date
    transaction_type = details.transaction_type
    confidentiality = details.confidentiality
    subject = details.subject
    file_name = details.file_name
    mime_type = details.mime_type
    file_data = details.file_data
    notes_on_request= details.notes_on_request
    # l2 = details.l2
    # l3 = details.l3
    today = datetime.today().strftime("%m-%d-%Y")
    
    # Generate PDF filename and email subject based on transaction_type
    if transaction_type == "INNER BOOK":
        pdf_filename = f"Inner Book.pdf"
        email_subject = f"Inner Book - Request ID - {request_id} – Approved"
    elif transaction_type == "CERTIFICATE LETTER":
        pdf_filename = f"Certificate.pdf"
        email_subject = f"Certificate - Request ID - {request_id} – Approved"
    elif transaction_type == "OUTER BOOK":
        pdf_filename = f"Outer Book.pdf"
        email_subject = f"Outer Book - Request ID - {request_id} – Approved"
    elif transaction_type == "MEMO":
        pdf_filename = f"Memo.pdf"
        email_subject = f"Memo - Request ID - {request_id} – Approved"
    else:
        pdf_filename = f"Document.pdf"
        email_subject = f"Document - Request ID - {request_id} – Approved"

    print(f"""
Employee Details:
-----------------
Employee Name       : {details.employee_name}
Designation         : {details.designation}
Receiver Email      : {details.receiver_email}
CC Emails           : {details.cc_emails}
Request ID          : {details.request_id}
Request Type        : {details.request_type}
Department          : {details.department}
Approval Type       : {details.approval_type}
Transaction Status  : {details.transaction_status}
Book Language       : {details.book_language}
Transaction Creator : {details.transaction_creator}
Sender              : {details.sender}
Receiver            : {details.receiver}
Transaction Date    : {details.transaction_date}
Transaction Type    : {details.transaction_type}
Confidentiality     : {details.confidentiality}
subject             : {details.subject}
File Name           : {details.file_name}
MIME Type          : {details.mime_type}
File Data Size     : {len(details.file_data)} chars
notes_on_request   : {details.notes_on_request}
""")



    
    try:
        # Prepare email template data
        email_data = {
            "request_id": request_id,
            "sender": sender,
            "sender_email": sender_email,
            "department": department,
            "designation": designation,
            "request_type": request_type,
            "today": today
        }
        
        # Load email content from template
        html_mail_content = get_email_content(email_data)
        
        # Process notes_on_request to remove paragraph tags
        processed_notes = remove_paragraph_tags(notes_on_request)
        
        custom_data = {
            "approval_type": approval_type,
            "transaction_status": transaction_status,
            "book_language": book_language,
            "transaction_creator": transaction_creator,
            "sender": sender,
            "receiver": receiver,
            "transaction_date": transaction_date,
            "transaction_type": transaction_type,
            "confidentiality": confidentiality,
            "subject": subject,
            "l1": processed_notes,
            "l2": "",
            "l3": ""
        }

        html_content = get_html_content(custom_data)
    
        if html_content:
            pdf_path = html_to_pdf(html_content, pdf_filename)
            if pdf_path:
                print(f"Conversion completed! PDF saved as: {pdf_path}")
            else:
                print("PDF conversion failed!")
        else:
            print("Failed to load and process HTML template!")

        # Create file from base64 data
        extra_file_path = create_file_from_base64(file_data, mime_type, file_name)
        
        # Send email to receiver (current flow - no change)
        send_email_with_attachment(pdf_path, html_mail_content, receiver_email, request_id, email_subject, cc_emails)
        
        # Send email to sender with additional file attachment only if file was created successfully
        if extra_file_path and os.path.exists(extra_file_path):
            send_email_with_extra_attachment(pdf_path, html_mail_content, sender_email, request_id, email_subject, cc_emails, extra_file_path)
            print(f"Sent email to sender ({sender_email}) with extra attachment: {extra_file_path}")
        else:
            print(f"Failed to create extra file from base64 data. Sending regular email to sender ({sender_email})")
            send_email_with_attachment(pdf_path, html_mail_content, sender_email, request_id, email_subject, cc_emails)

        # Cleanup files
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            print(f"{pdf_path} has been deleted.")
        else:
            print("PDF file does not exist.")
            
        if extra_file_path and os.path.exists(extra_file_path):
            os.remove(extra_file_path)
            print(f"{extra_file_path} has been deleted.")
        else:
            print("Extra file does not exist or was not created.")
        return JSONResponse({"status": "success", "pdf_path": pdf_path})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)