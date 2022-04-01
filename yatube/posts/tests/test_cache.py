from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostsCacheTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='test_author')

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
        posts_for_creation = list()
        for i in range(12):
            posts_for_creation.append(
                Post(
                    text='Тестовый пост',
                    author=cls.user,
                    group=cls.group,
                )
            )
        Post.objects.bulk_create(posts_for_creation)

        cls.posts = Post.objects.order_by('-pub_date')

    def setUp(self):
        # Создаём неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованный клиент автора поста
        self.user_auth_author = PostsCacheTest.user
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_auth_author)

    def get_content(self):
        response = self.authorized_client_author.get(
            reverse('posts:index')
        )
        return response.content

    def test_cache_index(self):
        """Проверка кеширования страницы index."""
        post_exist = self.get_content()
        self.posts[0].delete()
        post_deleted = self.get_content()
        self.assertEqual(post_exist, post_deleted)
        cache.clear()
        post_cleared = self.get_content()
        self.assertNotEqual(post_exist, post_cleared)
