from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.core.management import call_command
from django.db import OperationalError
from profiles.models import Profile, Photo
from django.utils import timezone
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
import random
import io
import os


class Command(BaseCommand):
    help = 'Initialize database with admin user and comprehensive test data'

    def handle(self, *args, **options):
        try:
            # Сначала применяем миграции
            self.stdout.write('Applying migrations...')
            call_command('migrate', verbosity=0, interactive=False)
            
            with transaction.atomic():
                # Создаем суперпользователя
                self.create_admin_user()
                
                # Создаем тестовых пользователей и профили
                self.create_comprehensive_test_users()
                
                # Создаем тестовые фотографии
                self.create_test_photos()
                
                self.stdout.write(
                    self.style.SUCCESS('Database initialized successfully!')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error initializing database: {str(e)}')
            )
            # Попробуем еще раз без транзакции
            try:
                call_command('migrate', verbosity=0, interactive=False)
                self.create_admin_user()
                self.create_comprehensive_test_users()
                self.create_test_photos()
                self.stdout.write(
                    self.style.SUCCESS('Database initialized successfully on retry!')
                )
            except Exception as retry_error:
                self.stdout.write(
                    self.style.ERROR(f'Failed to initialize database: {str(retry_error)}')
                )

    def create_admin_user(self):
        """Создать администратора"""
        try:
            if not User.objects.filter(username='admin').exists():
                admin_user = User.objects.create_superuser(
                    username='admin',
                    email='admin@admin.com',
                    password='admin123'
                )
                self.stdout.write(
                    self.style.SUCCESS('Created admin user: admin/admin123')
                )
            else:
                self.stdout.write('Admin user already exists')
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not create admin user: {str(e)}')
            )

    def create_comprehensive_test_users(self):
        """Создать реалистичных тестовых пользователей"""
        
        # Расширенные данные для мужских профилей
        male_profiles = [
            {
                'username': 'mikhail25',
                'first_name': 'Михаил',
                'nickname': 'Миша_Москва',
                'age': 25,
                'height': 180,
                'weight': 75,
                'city': 'moscow',
                'education': 'higher',
                'employment': 'employed',
                'orientation': 'traditional',
                'marital_status': 'single',
                'goal': 'Ищу серьезные отношения для создания семьи. Важна взаимная поддержка и понимание.',
                'smoking': 'no',
                'alcohol': 'rarely',
                'sport': 'regularly',
                'health_rating': 9,
                'conception_method': 'agreement',
                'father_contact': 'regular',
                'payment_approach': 'shared_expenses',
                'desired_age_min': 20,
                'desired_age_max': 30,
                'desired_height_min': 160,
                'desired_height_max': 175,
            },
            {
                'username': 'alexander30',
                'first_name': 'Александр',
                'nickname': 'Саша_СПб',
                'age': 30,
                'height': 175,
                'weight': 80,
                'city': 'spb',
                'education': 'higher',
                'employment': 'employed',
                'orientation': 'traditional',
                'marital_status': 'divorced',
                'goal': 'Хочу найти партнершу для рождения детей. Готов к долгосрочным отношениям.',
                'smoking': 'occasionally',
                'alcohol': 'socially',
                'sport': 'sometimes',
                'health_rating': 8,
                'conception_method': 'natural',
                'father_contact': 'important',
                'payment_approach': 'full_support',
                'desired_age_min': 25,
                'desired_age_max': 35,
                'desired_height_min': 165,
                'desired_height_max': 180,
                'has_children': True,
            },
            {
                'username': 'dmitry35',
                'first_name': 'Дмитрий',
                'nickname': 'Дима_НСК',
                'age': 35,
                'height': 185,
                'weight': 85,
                'city': 'novosibirsk',
                'education': 'specialized',
                'employment': 'entrepreneur',
                'orientation': 'traditional',
                'marital_status': 'single',
                'goal': 'Ищу женщину для создания большой и счастливой семьи. Ценю честность и открытость.',
                'smoking': 'no',
                'alcohol': 'no',
                'sport': 'regularly',
                'health_rating': 10,
                'conception_method': 'agreement',
                'father_contact': 'very_important',
                'payment_approach': 'full_support',
                'desired_age_min': 22,
                'desired_age_max': 32,
                'desired_height_min': 160,
                'desired_height_max': 175,
            },
            {
                'username': 'andrey28',
                'first_name': 'Андрей',
                'nickname': 'Андрей_Екб',
                'age': 28,
                'height': 178,
                'weight': 78,
                'city': 'ekaterinburg',
                'education': 'higher',
                'employment': 'employed',
                'orientation': 'traditional',
                'marital_status': 'single',
                'goal': 'Мечтаю о семье с детьми. Готов взять на себя ответственность за будущее семьи.',
                'smoking': 'no',
                'alcohol': 'rarely',
                'sport': 'sometimes',
                'health_rating': 8,
                'conception_method': 'natural',
                'father_contact': 'regular',
                'payment_approach': 'shared_expenses',
                'desired_age_min': 23,
                'desired_age_max': 33,
                'desired_height_min': 160,
                'desired_height_max': 170,
            },
            {
                'username': 'sergey32',
                'first_name': 'Сергей',
                'nickname': 'Серёжа_Казань',
                'age': 32,
                'height': 182,
                'weight': 82,
                'city': 'kazan',
                'education': 'secondary',
                'employment': 'employed',
                'orientation': 'traditional',
                'marital_status': 'single',
                'goal': 'Хочу стать отцом и создать крепкую семью. Ценю традиционные ценности.',
                'smoking': 'occasionally',
                'alcohol': 'socially',
                'sport': 'regularly',
                'health_rating': 9,
                'conception_method': 'agreement',
                'father_contact': 'important',
                'payment_approach': 'full_support',
                'desired_age_min': 24,
                'desired_age_max': 35,
                'desired_height_min': 165,
                'desired_height_max': 175,
            },
        ]
        
        # Расширенные данные для женских профилей
        female_profiles = [
            {
                'username': 'elena23',
                'first_name': 'Елена',
                'nickname': 'Лена_Москва',
                'age': 23,
                'height': 165,
                'weight': 55,
                'city': 'moscow',
                'education': 'higher',
                'employment': 'student',
                'orientation': 'traditional',
                'marital_status': 'single',
                'goal': 'Мечтаю о материнстве и крепкой семье. Ищу надежного партнера для совместного будущего.',
                'smoking': 'no',
                'alcohol': 'no',
                'sport': 'regularly',
                'health_rating': 10,
                'conception_method': 'natural',
                'father_contact': 'very_important',
                'payment_approach': 'shared_expenses',
                'desired_age_min': 25,
                'desired_age_max': 35,
                'desired_height_min': 175,
                'desired_height_max': 190,
            },
            {
                'username': 'anna27',
                'first_name': 'Анна',
                'nickname': 'Аня_СПб',
                'age': 27,
                'height': 170,
                'weight': 60,
                'city': 'spb',
                'education': 'higher',
                'employment': 'employed',
                'orientation': 'traditional',
                'marital_status': 'single',
                'goal': 'Готова к серьезным отношениям и созданию семьи. Важна эмоциональная связь.',
                'smoking': 'no',
                'alcohol': 'rarely',
                'sport': 'sometimes',
                'health_rating': 9,
                'conception_method': 'natural',
                'father_contact': 'important',
                'payment_approach': 'full_support',
                'desired_age_min': 28,
                'desired_age_max': 40,
                'desired_height_min': 175,
                'desired_height_max': 185,
            },
            {
                'username': 'maria31',
                'first_name': 'Мария',
                'nickname': 'Маша_НСК',
                'age': 31,
                'height': 168,
                'weight': 58,
                'city': 'novosibirsk',
                'education': 'specialized',
                'employment': 'employed',
                'orientation': 'traditional',
                'marital_status': 'divorced',
                'goal': 'Хочу второй шанс на счастье в материнстве. Ищу понимающего мужчину.',
                'smoking': 'no',
                'alcohol': 'socially',
                'sport': 'regularly',
                'health_rating': 8,
                'conception_method': 'agreement',
                'father_contact': 'regular',
                'payment_approach': 'shared_expenses',
                'desired_age_min': 30,
                'desired_age_max': 42,
                'desired_height_min': 175,
                'desired_height_max': 190,
                'has_children': True,
            },
            {
                'username': 'olga26',
                'first_name': 'Ольга',
                'nickname': 'Оля_Екб',
                'age': 26,
                'height': 172,
                'weight': 62,
                'city': 'ekaterinburg',
                'education': 'higher',
                'employment': 'student',
                'orientation': 'traditional',
                'marital_status': 'single',
                'goal': 'Стремлюсь к материнству и семейному счастью. Ценю честность и верность.',
                'smoking': 'no',
                'alcohol': 'rarely',
                'sport': 'sometimes',
                'health_rating': 9,
                'conception_method': 'natural',
                'father_contact': 'very_important',
                'payment_approach': 'shared_expenses',
                'desired_age_min': 26,
                'desired_age_max': 36,
                'desired_height_min': 178,
                'desired_height_max': 185,
            },
            {
                'username': 'irina29',
                'first_name': 'Ирина',
                'nickname': 'Ира_Казань',
                'age': 29,
                'height': 166,
                'weight': 57,
                'city': 'kazan',
                'education': 'higher',
                'employment': 'employed',
                'orientation': 'traditional',
                'marital_status': 'single',
                'goal': 'Мечтаю стать мамой и найти спутника жизни. Важна взаимная поддержка.',
                'smoking': 'no',
                'alcohol': 'rarely',
                'sport': 'regularly',
                'health_rating': 10,
                'conception_method': 'natural',
                'father_contact': 'important',
                'payment_approach': 'shared_expenses',
                'desired_age_min': 27,
                'desired_age_max': 38,
                'desired_height_min': 175,
                'desired_height_max': 185,
            },
        ]
        
        created_count = 0
        
        # Создаем мужские профили
        for profile_data in male_profiles:
            try:
                if not User.objects.filter(username=profile_data['username']).exists():
                    user = User.objects.create_user(
                        username=profile_data['username'],
                        first_name=profile_data['first_name'],
                        email=f"{profile_data['username']}@test.com",
                        password='test123'
                    )
                    
                    Profile.objects.create(
                        user=user,
                        nickname=profile_data['nickname'],
                        age=profile_data['age'],
                        height=profile_data['height'],
                        weight=profile_data['weight'],
                        blood_group=random.choice(['I+', 'II+', 'III+', 'IV+', 'I-', 'II-']),
                        gender='male',
                        city=profile_data['city'],
                        orientation=profile_data['orientation'],
                        marital_status=profile_data['marital_status'],
                        goal=profile_data['goal'],
                        education=profile_data['education'],
                        employment=profile_data['employment'],
                        smoking=profile_data['smoking'],
                        alcohol=profile_data['alcohol'],
                        sport=profile_data['sport'],
                        health_rating=profile_data['health_rating'],
                        has_diseases=False,
                        conception_method=profile_data['conception_method'],
                        father_contact=profile_data['father_contact'],
                        payment_approach=profile_data['payment_approach'],
                        looking_for='straight_women',
                        desired_age_min=profile_data['desired_age_min'],
                        desired_age_max=profile_data['desired_age_max'],
                        desired_height_min=profile_data.get('desired_height_min'),
                        desired_height_max=profile_data.get('desired_height_max'),
                        desired_appearance='european_light',
                        has_children=profile_data.get('has_children', False),
                        photo_required=True,
                        last_online=timezone.now() - timezone.timedelta(hours=random.randint(1, 48)),
                        is_active=True
                    )
                    created_count += 1
                    self.stdout.write(f'Created male profile: {profile_data["nickname"]}')
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Could not create male profile {profile_data["nickname"]}: {str(e)}')
                )
        
        # Создаем женские профили
        for profile_data in female_profiles:
            try:
                if not User.objects.filter(username=profile_data['username']).exists():
                    user = User.objects.create_user(
                        username=profile_data['username'],
                        first_name=profile_data['first_name'],
                        email=f"{profile_data['username']}@test.com",
                        password='test123'
                    )
                    
                    Profile.objects.create(
                        user=user,
                        nickname=profile_data['nickname'],
                        age=profile_data['age'],
                        height=profile_data['height'],
                        weight=profile_data['weight'],
                        blood_group=random.choice(['I+', 'II+', 'III+', 'IV+', 'I-', 'II-']),
                        gender='female',
                        city=profile_data['city'],
                        orientation=profile_data['orientation'],
                        marital_status=profile_data['marital_status'],
                        goal=profile_data['goal'],
                        education=profile_data['education'],
                        employment=profile_data['employment'],
                        smoking=profile_data['smoking'],
                        alcohol=profile_data['alcohol'],
                        sport=profile_data['sport'],
                        health_rating=profile_data['health_rating'],
                        has_diseases=False,
                        conception_method=profile_data['conception_method'],
                        father_contact=profile_data['father_contact'],
                        payment_approach=profile_data['payment_approach'],
                        looking_for='straight_men',
                        desired_age_min=profile_data['desired_age_min'],
                        desired_age_max=profile_data['desired_age_max'],
                        desired_height_min=profile_data.get('desired_height_min'),
                        desired_height_max=profile_data.get('desired_height_max'),
                        desired_appearance='european_light',
                        has_children=profile_data.get('has_children', False),
                        photo_required=True,
                        last_online=timezone.now() - timezone.timedelta(hours=random.randint(1, 48)),
                        is_active=True
                    )
                    created_count += 1
                    self.stdout.write(f'Created female profile: {profile_data["nickname"]}')
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Could not create female profile {profile_data["nickname"]}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created {created_count} comprehensive test profiles total')
        )

    def create_placeholder_image(self, text, color='#667eea', size=(300, 400)):
        """Создать placeholder изображение с текстом"""
        try:
            # Создаем изображение
            image = Image.new('RGB', size, color=color)
            draw = ImageDraw.Draw(image)
            
            # Пытаемся загрузить шрифт (если не найден, используем стандартный)
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            # Получаем размеры текста
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Вычисляем позицию для центрирования
            x = (size[0] - text_width) // 2
            y = (size[1] - text_height) // 2
            
            # Рисуем текст
            draw.text((x, y), text, fill='white', font=font)
            
            # Сохраняем в BytesIO
            img_io = io.BytesIO()
            image.save(img_io, format='JPEG', quality=85)
            img_io.seek(0)
            
            return img_io
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not create placeholder image: {str(e)}')
            )
            return None

    def create_test_photos(self):
        """Создать тестовые фотографии для профилей"""
        try:
            profiles = Profile.objects.all()
            created_photos = 0
            
            for profile in profiles:
                try:
                    # Проверяем, есть ли уже фотографии
                    if Photo.objects.filter(profile=profile).exists():
                        continue
                    
                    # Создаем 1-3 фотографии для каждого профиля
                    num_photos = random.randint(1, 3)
                    
                    for i in range(num_photos):
                        # Создаем placeholder изображение
                        img_io = self.create_placeholder_image(
                            f'{profile.nickname}\nФото {i+1}',
                            color=random.choice(['#667eea', '#764ba2', '#17a2b8', '#28a745', '#ffc107'])
                        )
                        
                        if img_io:
                            # Создаем запись фотографии
                            photo = Photo.objects.create(
                                profile=profile,
                                is_primary=(i == 0),
                                is_verified=True,
                                uploaded_at=timezone.now() - timezone.timedelta(days=random.randint(1, 30))
                            )
                            
                            # Сохраняем файл
                            filename = f'profile_{profile.id}_photo_{i+1}.jpg'
                            photo.image.save(
                                filename,
                                ContentFile(img_io.getvalue()),
                                save=True
                            )
                            
                            created_photos += 1
                            
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'Could not create photos for {profile.nickname}: {str(e)}')
                    )
                    continue
            
            self.stdout.write(
                self.style.SUCCESS(f'Created {created_photos} test photos')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not create test photos: {str(e)}')
            ) 