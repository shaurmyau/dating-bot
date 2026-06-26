import pytest
import boto3
from moto import mock_aws
from bot.services.s3_service import S3Service

@mock_aws
def test_upload_and_get_url(monkeypatch):
    # Отключаем прокси (если они заданы в системе)
    monkeypatch.delenv('HTTP_PROXY', raising=False)
    monkeypatch.delenv('HTTPS_PROXY', raising=False)
    monkeypatch.delenv('SOCKS_PROXY', raising=False)
    monkeypatch.delenv('NO_PROXY', raising=False)

    # Создаём клиент без endpoint_url (moto перехватывает)
    client = boto3.client('s3', region_name='us-east-1')
    client.create_bucket(Bucket='dating-photos')

    # Создаём S3Service и подменяем его клиент на мок-клиент
    s3_service = S3Service()           # создаст клиент с реальным endpoint, но мы его заменим
    s3_service.client = client
    s3_service.bucket = 'dating-photos'

    data = b"test image data"
    key = s3_service.upload_photo(data, "jpg")
    assert key.startswith("photos/")
    assert key.endswith(".jpg")

    url = s3_service.get_photo_url(key)
    assert s3_service.bucket in url