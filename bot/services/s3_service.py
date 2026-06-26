import boto3
from botocore.client import Config
from config import config
import uuid
from io import BytesIO

class S3Service:
    def __init__(self):
        self.client = boto3.client(
            's3',
            endpoint_url=config.S3_ENDPOINT,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
            config=Config(signature_version='s3v4'),
            region_name=config.S3_REGION,
            use_ssl=config.S3_USE_SSL
        )
        self.bucket = config.S3_BUCKET

    def upload_photo(self, file_data: bytes, extension: str = 'jpg') -> str:
        """Загружает байты файла в S3 и возвращает ключ (путь)"""
        key = f"photos/{uuid.uuid4()}.{extension}"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=BytesIO(file_data),
            ContentType=f'image/{extension}'
        )
        return key

    def get_photo_url(self, key: str) -> str:
        """Возвращает публичный URL (или подписанный, если bucket приватный)"""
        if config.S3_ENDPOINT.startswith('http'):
            # MinIO или публичный доступ
            return f"{config.S3_ENDPOINT}/{self.bucket}/{key}"
        else:
            # AWS S3 – генерируем подписанный URL на 1 час
            return self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=3600
            )