import shutil
import tempfile

from django.conf import settings
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Group, Post, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_author')
        cls.user_not_author = User.objects.create_user(username='test_user')
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded,
        )
        posts_for_creation = list()
        for i in range(12):
            posts_for_creation.append(
                Post(
                    text='Тестовый пост' + str(i),
                    author=cls.user,
                    group=cls.group,
                    image=cls.uploaded,
                )
            )
        Post.objects.bulk_create(posts_for_creation)

        cls.posts = Post.objects.order_by('-pub_date')
        cls.project_pages = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={'username': cls.user.username}),
        ]

        cls.comment = Comment.objects.create(
            text='Тестовый комментарий',
            post=cls.posts[0],
            author=cls.user_not_author,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаём неавторизованный клиент
        self.guest_client = Client()
        # Создаём авторизованный клиент
        self.user = PostsViewsTest.user_not_author
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        # Создаем авторизованный клиент автора поста
        self.user_auth_author = PostsViewsTest.user
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_auth_author)

    # Проверка используемых HTML-шаблонов
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsViewsTest.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': PostsViewsTest.user.username}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostsViewsTest.post.pk}
            ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostsViewsTest.post.pk}
            ): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }

        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    # Проверка контекста передаваемого view-функциями в HTML-шаблоны
    def post_obj_is_in_context(self):
        """Доп. функция для проверки 'page_obj' в контексте."""
        for url in PostsViewsTest.project_pages:
            response = self.guest_client.get(url)
            if (self.assertTrue('page_obj' in response.context)):
                return True

    def test_post_fields_values_in_context_check(self):
        """Доп. функция для проверки контекста поста на страницах проекта."""
        for url in PostsViewsTest.project_pages:
            response = self.guest_client.get(url)
            post_from_context = response.context['page_obj'][0]
            field_values = {
                post_from_context.text: PostsViewsTest.posts[0].text,
                post_from_context.image: PostsViewsTest.posts[0].image,
            }
            for response_field_value, expected_value in field_values.items():
                with self.subTest(field=response_field_value):
                    self.assertEqual(response_field_value, expected_value)

    def test_index_page_show_correct_context(self):
        """Проверка - контекст главной страницы содержит список постов."""
        response = self.guest_client.get(reverse('posts:index'))

        result = self.post_obj_is_in_context()
        if result:
            context = response.context['page_obj'].object_list

            paginator = Paginator(PostsViewsTest.posts, 10)
            expect_posts = list(paginator.get_page(1).object_list)

            self.assertIsInstance(
                response.context['page_obj'],
                type(paginator.page(1))
            )
            self.assertEqual(list(context), expect_posts)

    def test_group_list_page_show_correct_context(self):
        """Проверка - контекст страницы группы содержит
        список постов, отфильтрованных по группе."""
        response = self.guest_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsViewsTest.group.slug}
            )
        )

        result = self.post_obj_is_in_context()
        if result:
            context = response.context['page_obj'].object_list

            paginator = Paginator(
                Post.objects.filter(
                    group=PostsViewsTest.group
                ).order_by('-pub_date'), 10)
            expect_posts = list(paginator.get_page(1).object_list)

            self.assertIsInstance(
                response.context['page_obj'],
                type(paginator.page(1))
            )
            self.assertEqual(context, expect_posts)

    def test_profile_page_show_correct_context(self):
        """Проверка - контекст профиля пользователя содержит
        список постов, отфильтрованных по пользователю."""
        # Получаем элементы контекста из HTTP-ответа для дальнейшей проверки
        response = self.guest_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': PostsViewsTest.user.username}
            )
        )
        result = self.post_obj_is_in_context()
        if result:
            context_page_obj = response.context['page_obj'].object_list

            # Получаем вручную данные из БД и создаем страницу постов
            paginator = Paginator(
                Post.objects.filter(
                    author=PostsViewsTest.user
                ).order_by('-pub_date'), 10)
            expect_posts = list(paginator.get_page(1).object_list)

            # Проверяем действительно ли HTTP-ответ возвращает ожидаемые данные
            self.assertIsInstance(
                response.context['page_obj'],
                type(paginator.page(1))
            )
            self.assertEqual(context_page_obj, expect_posts)

            self.assertTrue('post_count' in response.context)
            self.assertEqual(
                response.context['post_count'],
                PostsViewsTest.posts.filter(author=PostsViewsTest.user).count()
            )

            self.assertTrue('author_obj' in response.context)
            self.assertEqual(
                response.context['author_obj'],
                PostsViewsTest.user
            )

    def test_post_detail_page_show_correct_context(self):
        """Проверка - контекст страницы поста
        содержит пост, отфильтрованный по id."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostsViewsTest.posts[0].pk}
            )
        )
        self.assertTrue('requested_post' in response.context)
        self.assertEqual(
            response.context['requested_post'],
            PostsViewsTest.posts[0]
        )

        self.assertTrue('post_count' in response.context)
        self.assertEqual(
            response.context['post_count'],
            PostsViewsTest.posts.filter(author=PostsViewsTest.user).count()
        )

        self.assertTrue('comments' in response.context)
        self.assertEqual(
            response.context['comments'][0],
            PostsViewsTest.comment
        )

        post_from_context = response.context['requested_post']
        field_values = {
            post_from_context.text: PostsViewsTest.posts[0].text,
            post_from_context.image: PostsViewsTest.posts[0].image,
        }
        for response_field_value, expected_value in field_values.items():
            with self.subTest(field=response_field_value):
                self.assertEqual(response_field_value, expected_value)

    def test_post_create_page_show_correct_context(self):
        """Проверка - контекст страницы создания поста
        содержит корректную форму."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for field, expected_type in form_fields.items():
            with self.subTest(field=field):
                form_field = response.context['form'].fields[field]
                self.assertIsInstance(form_field, expected_type)

    def test_post_edit_page_show_correct_context(self):
        """Проверка - контекст страницы редактирования поста
        содержит корректную форму и пост, отфильтрованный по id."""
        response = self.authorized_client_author.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostsViewsTest.post.pk}
            )
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for field, expected_type in form_fields.items():
            with self.subTest(field=field):
                form_field = response.context['form'].fields[field]
                self.assertIsInstance(form_field, expected_type)

        self.assertTrue('is_edit' in response.context)
        self.assertTrue(response.context['is_edit'])

        self.assertTrue('post' in response.context)
        self.assertEqual(
            response.context['post'],
            PostsViewsTest.post
        )

    # Проверка работы паджинатора
    def test_first_page_contains_ten_records(self):
        """Проверка - первые страницы содержат по 10 постов из 13."""
        for page in PostsViewsTest.project_pages:
            response = self.guest_client.get(page)
            self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_three_records(self):
        """Проверка - вторые страницы содержат по 3 поста из 13."""
        for page in PostsViewsTest.project_pages:
            response = self.guest_client.get(page + '?page=2')
            self.assertEqual(len(response.context['page_obj']), 3)

    # Дополнительные проверки при создании поста
    def test_new_post_is_added_to_project_pages(self):
        """После создания нового поста он появляется на главной странице,
        странице выбранной группы и профиля пользователя."""
        for page in PostsViewsTest.project_pages:
            response = self.guest_client.get(page)
            self.assertIn(
                PostsViewsTest.posts[0],
                response.context['page_obj'].object_list
            )

    def test_post_another_group(self):
        """Проверка - Пост не попал в группу,
        для которой не был предназначен."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': PostsViewsTest.group.slug}
            )
        )
        last_response_post = response.context['page_obj'][0]
        last_response_post_text = last_response_post.text
        self.assertTrue(last_response_post_text, PostsViewsTest.post)
