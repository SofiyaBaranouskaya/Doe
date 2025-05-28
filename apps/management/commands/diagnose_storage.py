from django.core.management.base import BaseCommand
from django.core.files.storage import default_storage
import os
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Diagnose storage configuration issues'

    def handle(self, *args, **options):
        self.stdout.write("===== Storage Configuration Diagnosis =====")
        self.stdout.write("Checking critical environment variables...")
        self.check_env_vars()

        self.stdout.write("\nTesting storage connection...")
        self.test_storage_connection()

        self.stdout.write("\nTesting bucket access...")
        self.test_bucket_access()

        self.stdout.write("\n===== Diagnosis Complete =====")

    def check_env_vars(self):
        """Проверка критических переменных окружения"""
        env_vars = [
            'DEFAULT_FILE_STORAGE',
            'AWS_ACCESS_KEY_ID',
            'AWS_SECRET_ACCESS_KEY',
            'AWS_STORAGE_BUCKET_NAME',
            'AWS_S3_ENDPOINT_URL',
            'AWS_DEFAULT_ACL'
        ]

        for var in env_vars:
            value = os.getenv(var)
            status = "✓ SET" if value else "✗ MISSING"
            self.stdout.write(f"  {var}: {status}")
            if value and ('KEY' in var or 'SECRET' in var):
                self.stdout.write(f"    Value: {value[:4]}...{value[-4:]}")

    def test_storage_connection(self):
        """Тестирование подключения к хранилищу"""
        try:
            # Определяем тип хранилища через рефлексию
            storage_class = default_storage.__class__.__name__
            self.stdout.write(f"  Storage type: {storage_class}")

            # Попробуем получить атрибуты S3, если они есть
            if hasattr(default_storage, 'bucket_name'):
                self.stdout.write(f"  Bucket: {default_storage.bucket_name}")
            if hasattr(default_storage, 'endpoint_url'):
                self.stdout.write(f"  Endpoint: {default_storage.endpoint_url}")

            self.stdout.write("  ✓ Storage initialized successfully")
            return True
        except Exception as e:
            self.stdout.write(f"  ✗ Storage initialization failed: {str(e)}")
            logger.exception("Storage connection error")
            return False

    def test_bucket_access(self):
        """Тест записи/чтения в бакет"""
        test_file = 'diagnostic_test.txt'
        test_content = b'This is a storage test file'
        success = True

        try:
            # Запись файла
            self.stdout.write("  Writing test file...")
            default_storage.save(test_file, test_content)
            self.stdout.write("  ✓ Test file written")
        except Exception as e:
            self.stdout.write(f"  ✗ Write failed: {str(e)}")
            logger.exception("File write error")
            success = False

        try:
            # Чтение файла
            self.stdout.write("  Reading test file...")
            if default_storage.exists(test_file):
                with default_storage.open(test_file) as f:
                    content = f.read()
                    if content == test_content:
                        self.stdout.write("  ✓ Content matches")
                    else:
                        self.stdout.write(f"  ✗ Content mismatch: {len(content)} bytes")
                        success = False
            else:
                self.stdout.write("  ✗ Test file not found")
                success = False
        except Exception as e:
            self.stdout.write(f"  ✗ Read failed: {str(e)}")
            logger.exception("File read error")
            success = False

        try:
            # Удаление файла
            if default_storage.exists(test_file):
                self.stdout.write("  Deleting test file...")
                default_storage.delete(test_file)
                self.stdout.write("  ✓ Cleanup complete")
        except Exception as e:
            self.stdout.write(f"  ✗ Delete failed: {str(e)}")
            logger.exception("File delete error")
            success = False

        return success