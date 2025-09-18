from fastapi import UploadFile
from datetime import datetime
from docx import Document
from typing import Dict, List
from urllib.parse import urlparse
import boto3
from botocore.exceptions import ClientError
import os
import tempfile
import mimetypes
from PyPDF2 import PdfReader
import pandas as pd
import csv
from pydantic import BaseModel
from ..core.config import settings
from app.exceptions.http_exceptions import APIException
import bleach
import time



class FileContent(BaseModel):
    filename: str
    content: str
    s3_url: str


class S3Handler:
    def __init__(self, bucket_name: str):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = bucket_name

    async def upload_file(self, file_path: str, original_filename: str) -> str:
        """Upload file to S3 and return the URL"""
        try:
            # Generate a unique file path in S3
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            s3_key = f"uploads/{timestamp}_{original_filename}"

            # Upload the file
            content_type = mimetypes.guess_type(original_filename)[0]
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': content_type}
            )

            # Build S3 URL using settings.AWS_ENDPOINT
            if settings.AWS_ENDPOINT:
                # If AWS_ENDPOINT is configured, use it to build URL
                s3_url = f"{settings.AWS_ENDPOINT}/{s3_key}"
            else:
                # If AWS_ENDPOINT is not configured, use standard format to build URL
                # Check if it's China region
                if settings.AWS_REGION and settings.AWS_REGION.startswith('cn-'):
                    s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com.cn/{s3_key}"
                else:
                    s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            
            return s3_url
        except ClientError as e:
            raise APIException(
                status_code=500,
                message=f"Failed to upload file to S3: {str(e)}"
            )


async def process_multiple_files(
    files: List[UploadFile],
    allowed_file_types: List[str],
    s3_handler: S3Handler
) -> List[FileContent]:
    """Process multiple uploaded files with S3 storage"""
    processed_files = []
    max_file_size = 100 * 1024 * 1024  # 25 MB

    for file in files:
        # Check file size
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)

        if file_size > max_file_size:
            raise APIException(
                status_code=400,
                message=f"File {file.filename} is too large. Maximum allowed is {max_file_size / (1024 * 1024)} MB"
            )

        # Get file extension
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in allowed_file_types:
            raise APIException(
                status_code=400,
                message=f"Unsupported file type {file.filename}. Supported types: {', '.join(allowed_file_types)}"
            )

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        try:
            # Upload to S3 first
            s3_url = await s3_handler.upload_file(temp_file_path, file.filename)

            # Process file content based on type
            if file_ext in ['png', 'jpg', 'jpeg']:
                # For images, we just pass the S3 URL to the AI
                content = f"Image URL: {s3_url}"
            elif file_ext in ALLOWED_AUDIO_TYPES:
                content = process_audio_file(temp_file_path)
            elif file_ext == 'docx':
                content = extract_docx_text(temp_file_path)
            elif file_ext == 'pdf':
                content = extract_pdf_text(temp_file_path)
            elif file_ext == 'csv':
                content = process_csv_file(temp_file_path)
            else:
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

            processed_files.append(FileContent(
                filename=file.filename,
                content=content,
                s3_url=s3_url
            ))

        except Exception as e:
            raise APIException(
                status_code=400,
                message=f"Failed to process file {file.filename}: {str(e)}"
            )
        finally:
            os.unlink(temp_file_path)

    return processed_files


def extract_docx_text(file_path):
    """
    从 DOCX 文件中提取文本内容
    """
    doc = Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)


def extract_pdf_text(file_path: str) -> str:
    """
    从 PDF 文件中提取文本内容
    """
    try:
        reader = PdfReader(file_path)
        text_content = []

        # Iterate through each page and extract text
        for page in reader.pages:
            text_content.append(page.extract_text())

        return "\n".join(text_content)
    except Exception as e:
        raise APIException(
            status_code=400,
            message=f"PDF 文件解析失败: {str(e)}"
        )


def process_csv_file(file_path: str) -> str:
    """
    处理 CSV 文件并返回格式化的文本内容
    """
    try:
        # Try using pandas to read (can handle more complex CSV)
        try:
            df = pd.read_csv(file_path)
            # Get basic statistics
            summary = f"CSV 文件概要:\n"
            summary += f"总行数: {len(df)}\n"
            summary += f"总列数: {len(df.columns)}\n"
            summary += f"列名: {', '.join(df.columns)}\n\n"

            # Add first few rows as preview
            preview_rows = min(5, len(df))
            summary += f"前 {preview_rows} 行数据预览:\n"
            summary += df.head(preview_rows).to_string()

            return summary

        except Exception:
            # If pandas reading fails, use csv module as fallback
            with open(file_path, 'r', encoding='utf-8') as f:
                csv_reader = csv.reader(f)
                headers = next(csv_reader)  # Get headers
                rows = list(csv_reader)[:5]  # Get first 5 rows of data

                content = f"CSV 文件内容:\n"
                content += f"表头: {', '.join(headers)}\n\n"
                content += "数据预览:\n"
                for row in rows:
                    content += f"{', '.join(row)}\n"

                return content

    except Exception as e:
        raise APIException(
            status_code=400,
            message=f"CSV 文件解析失败: {str(e)}"
        )


def process_audio_file(file_path: str) -> str:
    """
    处理音频文件并返回转录文本
    """
    import whisper
    import os

    try:
        # Ensure file path is absolute and properly encoded
        absolute_path = os.path.abspath(os.path.normpath(file_path))

        # Convert file path to raw string
        safe_path = str(absolute_path)

        # Load Whisper model
        model = whisper.load_model("base")

        # Transcribe audio
        result = model.transcribe(safe_path)

        return result["text"]

    except Exception as e:
        raise APIException(
            status_code=400,
            message=f"Audio transcription failed: {str(e)}"
        )


def validate_remote_url(url: str) -> bool:
    """验证远程URL是否有效"""
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc])
    except Exception as e:
        raise APIException(
            status_code=400,
            message=f"Verification of remote URL failed: {str(e)}"
        )


def get_temporary_credentials() -> Dict:
    """
    获取AWS S3的临时访问凭证

    Returns:
        Dict: 包含临时凭证的字典，包括access key, secret key和session token
    """
    # If it's China region, need to specify endpoint_url specifically
    region = settings.AWS_REGION
    endpoint_url = None
    if region.startswith('cn-'):
        endpoint_url = f"https://sts.{region}.amazonaws.com.cn"
    sts_client = boto3.client(
        'sts',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=region,
        endpoint_url=endpoint_url
    )

    try:
        response = sts_client.get_session_token(
            DurationSeconds=3600  # Credential valid for 1 hour
        )

        return {
            'key': response['Credentials']['AccessKeyId'],
            'secret': response['Credentials']['SecretAccessKey'],
            'token': response['Credentials']['SessionToken']
        }

    except Exception as e:
        raise APIException(
            status_code=500,
            message=f"Failed to get temporary credentials: {str(e)}"
        )


# HTML sanitization function
def sanitize_html(html_content):
    allowed_tags = ['p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'em', 'u', 
                   'ul', 'ol', 'li', 'span', 'a', 'img', 'blockquote', 'code', 'pre',
                   'table', 'thead', 'tbody', 'tr', 'th', 'td', 'div']
    allowed_attrs = {
        '*': ['class', 'style'],
        'a': ['href', 'rel', 'target'],
        'img': ['src', 'alt', 'width', 'height'],
        'table': ['border', 'cellpadding', 'cellspacing'],
        'th': ['colspan', 'rowspan'],
        'td': ['colspan', 'rowspan'],
    }
    cleaned_html = bleach.clean(html_content, 
                               tags=allowed_tags, 
                               attributes=allowed_attrs, 
                               strip=True)
    return cleaned_html


# HTTP proxy configuration tool
def configure_http_proxy():
    """
    配置HTTP代理，仅在测试环境中启用
    
    Returns:
        httpx.Client: 配置了代理的httpx客户端，如果不需要代理则返回默认客户端
    """
    import os
    import httpx
    from ..core.config import settings
    
    # Enable proxy only in test environment
    if settings.ENV == "development" and settings.USE_HTTP_PROXY:
        # Set environment variables
        os.environ["HTTP_PROXY"] = settings.HTTP_PROXY
        os.environ["HTTPS_PROXY"] = settings.HTTPS_PROXY
        
        # Create httpx client configured with proxy
        # Note: proxy URL format in httpx should be complete URL
        proxy_url = settings.HTTP_PROXY
        proxy_client = httpx.Client(proxy=proxy_url)
        return proxy_client
    else:
        # In non-development environment or when proxy is not enabled, explicitly remove proxy environment variables
        if "HTTP_PROXY" in os.environ:
            del os.environ["HTTP_PROXY"]
        if "HTTPS_PROXY" in os.environ:
            del os.environ["HTTPS_PROXY"]
        if "http_proxy" in os.environ:
            del os.environ["http_proxy"]
        if "https_proxy" in os.environ:
            del os.environ["https_proxy"]
    
    # Return an httpx client explicitly configured without proxy
    return httpx.Client(timeout=60.0)  


def convert_to_timestamp(date_value):
    if date_value is None:
        return None
    
    try:
        # Try to parse the date string - adjust the format as needed
        # This example assumes date format like "2025-03-11" or "2025/03/11"
        if isinstance(date_value, str):
            # Try multiple common date formats
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"]:
                try:
                    date_obj = datetime.strptime(date_value, fmt)
                    # Convert to integer timestamp (seconds since epoch)
                    return int(time.mktime(date_obj.timetuple()))
                except ValueError:
                    continue
        
        # If it's already a datetime object
        elif isinstance(date_value, datetime):
            return int(time.mktime(date_value.timetuple()))
        
        # If the conversion failed
        return None
    except:
        return None


def get_timezone_by_city(city_name, country_code=None):
    from timezonefinder import TimezoneFinder
    from geopy.geocoders import Nominatim
    """
    通过城市名称获取时区字符串
    
    参数:
        city_name (str): 城市名称
        country_code (str, optional): 国家代码，如 'CN', 'US' 等
    
    返回:
        str: 时区字符串，如 'Asia/Shanghai'
    """
    try:
        # Initialize geocoder
        geolocator = Nominatim(user_agent="timezone_app")
        
        # Build query string
        query = city_name
        if country_code:
            query = f"{city_name}, {country_code}"
            
        # Get geographical location of the city
        location = geolocator.geocode(query)
        
        if location is None:
            return None
            
        # Use TimezoneFinder to find timezone
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lng=location.longitude, lat=location.latitude)
        
        return timezone_str
        
    except Exception as e:
        print(f"获取时区时出错: {e}")
        return None