import os
import subprocess
import tempfile
import logging
from django.http import HttpResponse
from django.utils.crypto import get_random_string

logger = logging.getLogger(__name__)

def html_to_pdf_response(html_content=None, filename="document.pdf", url=None):
    """
    Convert HTML content or a URL to a PDF response using Chrome headless.
    """
    chrome = os.environ.get("CHROME_PATH")
    if not chrome:
        # Fallback to default paths on Windows and WSL
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
            "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
            "/usr/bin/google-chrome",
            "/usr/bin/chrome",
        ]
        for p in paths:
            if os.path.exists(p):
                chrome = p
                break
    
    if not chrome:
        return HttpResponse("Chrome not found. Please set CHROME_PATH environment variable.", content_type="text/plain")

    pdf_output_dir = os.environ.get("PDF_OUTPUT_DIR")
    # Use system temp dir if not configured
    if not pdf_output_dir:
        pdf_output_dir = tempfile.gettempdir()

    random_string = get_random_string(6)
    temp_html_name = f"temp_{random_string}.html"
    temp_pdf_name = f"temp_{random_string}.pdf"
    
    # We write the HTML to a temp file
    temp_html_path = os.path.join(pdf_output_dir, temp_html_name)
    temp_pdf_path = os.path.join(pdf_output_dir, temp_pdf_name)

    try:
        if url:
            source = url
        else:
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # If we are using Windows Chrome from WSL, we might need a better way to pass the file path.
            # But the most robust way is to use a URL.
            source = f"file:///{temp_html_path.replace('\\', '/')}"
            if chrome.startswith("/mnt/c"):
                 # Convert /mnt/c/path to C:/path for Windows Chrome
                 win_path = temp_html_path.replace("/mnt/c/", "C:/")
                 source = f"file:///{win_path}"

        args = [
            chrome,
            "--headless",
            "--disable-gpu",
            "--print-to-pdf-no-header",
            "--print-to-pdf-no-footer",
            f"--print-to-pdf={temp_pdf_path}",
            source,
        ]
        
        logger.info(f"Running command: {' '.join(args)}")
        subprocess.check_call(args, timeout=30)
        
        if not os.path.exists(temp_pdf_path):
            return HttpResponse("Failed to generate PDF file.", content_type="text/plain")

        with open(temp_pdf_path, "rb") as f:
            pdf_data = f.read()
            
        response = HttpResponse(pdf_data, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
            
    except Exception as e:
        logger.exception("Error while generating PDF")
        return HttpResponse(f"Error while generating PDF: {str(e)}", content_type="text/plain")
    finally:
        # Cleanup
        try:
            if os.path.exists(temp_html_path):
                os.remove(temp_html_path)
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
        except Exception:
            pass
