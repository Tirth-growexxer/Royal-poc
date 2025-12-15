# Royal Group -Document Management API

A FastAPI-based microservice for automated generation, distribution, and storage of documents (service letters, certificates, memos, and books) for the Royal Group Management System.

## Overview

This API service automates the workflow for generating official documents, converting them to PDF format, sending them via email, and storing them in Oracle Cloud Infrastructure (OCI) Object Storage. The system supports role-based access where managers and employees can request and retrieve documents through a frontend application.

## Features

- **Automated PDF Generation**: Converts HTML templates to PDF documents using dynamic data
- **Email Distribution**: Sends professional HTML emails with PDF attachments to recipients
- **Cloud Storage Integration**: Uploads and retrieves documents from OCI Object Storage
- **Multi-Transaction Support**: Handles various document types:
  - Inner Book (كتاب داخلي)
  - Outer Book
  - Certificate Letters
  - Memos/Notes
- **Secure Credential Management**: Integrates with OCI Vault for secure secret retrieval
- **Image Processing**: Converts image URLs to base64 for PDF embedding
- **Base64 File Handling**: Processes and attaches additional files (PDFs, images, documents)

## Technology Stack

- **Framework**: FastAPI (Python 3.x)
- **PDF Generation**: pdfkit (wkhtmltopdf)
- **Cloud Services**: Oracle Cloud Infrastructure (OCI) SDK
  - Object Storage
  - Vault (for secrets management)
- **Email**: SMTP (smtplib)
- **Data Validation**: Pydantic
- **Template Engine**: Python string formatting

## Project Structure

```
Royal-poc/
├── main.py                 # Main FastAPI application and endpoints
├── secret_manager.py       # OCI Vault integration for secrets
├── template_pdf.html       # PDF document template
├── template.txt           # PDF template (alternative format)
├── email_template.txt      # Email HTML template
├── sign.jpg               # Digital signature image
├── requirements.txt       # Python dependencies
├── config.json            # Configuration file (not in repo)
└── README.md              # This file
```

## Prerequisites

1. **Python 3.8+**
2. **wkhtmltopdf** (required for pdfkit)
   ```bash
   # Ubuntu/Debian
   sudo apt-get install wkhtmltopdf
   
   # macOS
   brew install wkhtmltopdf
   
   # Windows
   # Download from: https://wkhtmltopdf.org/downloads.html
   ```
3. **Oracle Cloud Infrastructure Account** with:
   - Object Storage bucket configured
   - Vault with secrets for email credentials
   - OCI API credentials (user OCID, tenancy OCID, fingerprint, private key)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Royal-poc
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the application**
   
   Create a `config.json` file in the project root:
   ```json
   {
     "smtp_server": "smtp.gmail.com",
     "sender_email": "noreply@royalgroup.com",
     "smtp_port": 587,
     "smtp_username": "<OCI_Vault_Secret_OCID_for_username>",
     "smtp_password": "<OCI_Vault_Secret_OCID_for_password>",
     "oci_user_ocid": "<OCI_User_OCID>",
     "oci_fingerprint": "<OCI_API_Key_Fingerprint>",
     "oci_tenancy_ocid": "<OCI_Tenancy_OCID>",
     "oci_region": "us-ashburn-1",
     "oci_bucket_name": "<OCI_Bucket_Name>",
     "oci_folder_name": "royal_group",
     "oci_namespace": "<OCI_Namespace>",
     "oci_private_key_path": "/path/to/oci/private/key.pem"
   }
   ```

5. **Set up OCI credentials**
   
   Option 1: Use OCI config file (recommended for local development)
   ```bash
   # Place OCI config at ~/.oci/config
   ```
   
   Option 2: Configure in `config.json` (as shown above)

## Running the Application

1. **Start the FastAPI server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the API**
   - API Base URL: `http://localhost:8000`
   - Interactive API Docs: `http://localhost:8000/docs`
   - Alternative Docs: `http://localhost:8000/redoc`

## API Endpoints

### 1. Generate and Send Document
**POST** `/approve_letters`

Generates a PDF document, sends emails to recipients, and uploads to OCI storage.

**Request Body:**
```json
{
  "employee_name": "John Doe",
  "designation": "Software Engineer",
  "receiver_email": "receiver@example.com",
  "sender_email": "sender@example.com",
  "cc_emails": ["cc1@example.com", "cc2@example.com"],
  "request_id": "12345",
  "request_type": "Service Letter",
  "department": "IT",
  "approval_type": "Approved",
  "transaction_status": "Completed",
  "book_language": "English",
  "transaction_creator": "Manager Name",
  "transaction_creator_email": "manager@example.com",
  "sender": "John Doe",
  "receiver": "HR Department",
  "transaction_date": "2024-01-15",
  "transaction_type": "INNER BOOK",
  "confidentiality": "Internal",
  "subject": "Service Letter Request",
  "file_name": "additional_document",
  "mime_type": "application/pdf",
  "file_data": "<base64_encoded_file_content>",
  "notes_on_request": "<HTML_content_with_notes>"
}
```

**Response:**
```json
{
  "status": "success",
  "pdf_path": "12345_Inner Book.pdf",
  "oci_object_name": "royal_group/12345_INNER_BOOK.pdf"
}
```

**Transaction Types:**
- `INNER BOOK` → Generates "Inner Book" document
- `OUTER BOOK` → Generates "Outer Book" document
- `CERTIFICATE LETTER` → Generates "Certificate" document
- `MEMO` or `NOTE` → Generates "Memo" document

### 2. Retrieve PDF by Request ID
**POST** `/get_pdf_by_id`

Retrieves a PDF document from OCI storage by request ID.

**Request Body:**
```json
{
  "id": "12345"
}
```

**Response:**
- Returns PDF file if found
- Returns 404 error if not found

## Workflow

1. **Frontend Request**: Manager or employee submits a document request through the frontend
2. **PDF Generation**: API generates PDF from HTML template with dynamic data
3. **Email Distribution**: 
   - Sends email to transaction creator (manager) with PDF attachment
   - Sends email to sender (employee) with PDF and any additional files
4. **Cloud Storage**: PDF is uploaded to OCI Object Storage for archival
5. **Retrieval**: Documents can be retrieved later using the request ID

## Security Features

- **OCI Vault Integration**: Email credentials stored securely in OCI Vault
- **Instance Principals**: Uses OCI Instance Principals for authentication (when running on OCI)
- **CORS Configuration**: Configurable CORS middleware for frontend integration
- **Input Validation**: Pydantic models for request validation

## Template System

### PDF Template (`template_pdf.html` / `template.txt`)
- Supports bilingual content (English/Arabic)
- Dynamic fields: transaction details, approval info, notes, signature
- Embedded signature image support
- Customizable styling

### Email Template (`email_template.txt`)
- Professional HTML email design
- Includes request details and approval status
- Responsive layout

## Error Handling

The API includes comprehensive error handling:
- PDF generation failures
- Email sending errors
- OCI upload/download failures
- Template loading errors
- Invalid input validation

All errors return appropriate HTTP status codes with descriptive error messages.

## Development Notes

- The application uses `secret_manager_local.py` for local development (you may need to create this file or modify imports)
- Temporary PDF files are created during processing and should be cleaned up
- OCI client initialization gracefully handles missing configurations
- Image URLs in HTML content are automatically converted to base64 for PDF embedding

## Environment Variables

While the application primarily uses `config.json`, you can also use environment variables for sensitive data:
- `OCI_PRIVATE_KEY_PATH`: Path to OCI private key file
- `SMTP_USERNAME`: SMTP username (if not using OCI Vault)
- `SMTP_PASSWORD`: SMTP password (if not using OCI Vault)

## Troubleshooting

### PDF Generation Fails
- Ensure `wkhtmltopdf` is installed and accessible in PATH
- Check file permissions for output directory
- Verify HTML template syntax

### Email Sending Fails
- Verify SMTP credentials in OCI Vault
- Check SMTP server settings and port
- Ensure firewall allows SMTP connections

### OCI Upload Fails
- Verify OCI credentials and permissions
- Check bucket name and namespace
- Ensure proper IAM policies for Object Storage

### Template Loading Fails
- Verify template files exist in project directory
- Check file encoding (should be UTF-8)
- Ensure all template placeholders are provided in request

## Contributing

1. Follow the existing code style
2. Add appropriate error handling
3. Update documentation for new features
4. Test all endpoints before submitting

## License

[Specify your license here]

## Contact

For questions or issues, please contact the development team.

