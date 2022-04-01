from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_author')
        cls.user_not_author = User.objects.create_user(username='auth_user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
        )
        cls.urls = [
            f'/profile/{cls.user.username}/',
            f'/group/{cls.group.slug}/',
            '/',
            f'/posts/{cls.post.pk}/',
        ]
        cls.urls_auth_required = [
            '/create/',
            '/follow/',
            f'/posts/{PostsURLTests.post.pk}/edit/',
        ]
        cls.urls_auth_required_redirects_check = [
            '/create/',
            '/follow/',
            f'/posts/{PostsURLTests.post.pk}/edit/',
            f'/profile/{cls.user.username}/follow/',
            f'/profile/{cls.user.username}/unfollow/',
            f'/posts/{cls.post.pk}/comment/',
        ]

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.user_auth = PostsURLTests.user_not_author
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_auth)
        # Создаем авторизованный клиент автора поста
        self.user_auth_author = PostsURLTests.user
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_auth_author)

    # Проверка вызова соответствующих HTML-шаблонов
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{PostsURLTests.group.slug}/': 'posts/group_list.html',
            f'/profile/{PostsURLTests.user.username}/': 'posts/profile.html',
            f'/posts/{PostsURLTests.post.pk}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{PostsURLTests.post.pk}/edit/': 'posts/create_post.html',
            '/follow/': 'posts/follow.html',
        }

        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client_author.get(url)
                self.assertTemplateUsed(response, template)

    # Проверка общедоступных страницы для гостей
    def test_posts_app_urls_for_guest_users(self):
        """Проверка доступности страниц неавторизованным пользователям"""
        for url in PostsURLTests.urls:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверки доступности общедоступных страниц для авторизованных лиц
    def test_posts_app_urls_for_auth_users(self):
        """Проверка доступности общедоступных страниц
        авторизованным пользователям"""
        for url in PostsURLTests.urls:
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_auth_required_for_auth_users(self):
        """Проверка доступности auth_required страниц
        авторизованным пользователям"""
        for url in PostsURLTests.urls_auth_required:
            with self.subTest(url=url):
                response = self.authorized_client_author.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверка несуществующей страницы
    def test_unexisting_page_for_users(self):
        """Проверка ответа от несуществующей страницы пользователям."""
        http_clients = [
            'guest_client',
            'authorized_client',
        ]
        for client in http_clients:
            with self.subTest(client=client):
                response = self.client.get('/unexisting_page/')
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    # Проверка редиректов для неавторизованного пользователя
    def test_url_redirects_guest_to_login(self):
        """Страницы, требующие аутентификации, перенаправят
        гостя на страницу авторизации."""
        for url in PostsURLTests.urls_auth_required_redirects_check:
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(response, f'/auth/login/?next={url}')

    # Проверка редиректов для авторизованного пользователя
    def test_edit_url_redirect_auth_not_author_on_posts_login(self):
        """Страница редактирования перенаправит
        не автора поста на страницу поста."""
        response = self.authorized_client.get(
            f'/posts/{PostsURLTests.post.pk}/edit/',
            follow=True
        )
        self.assertRedirects(response, f'/posts/{PostsURLTests.post.pk}/')

    def test_comment_url_redirect_auth_user_on_post_detail(self):
        """Страница комментирования перенаправит
        пользователя на страницу поста."""
        response = self.authorized_client.get(
            f'/posts/{PostsURLTests.post.pk}/comment/',
            follow=True
        )
        self.assertRedirects(response, f'/posts/{PostsURLTests.post.pk}/')
