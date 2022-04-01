from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post, Follow

User = get_user_model()


class PostsFollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_author')
        cls.user_not_author = User.objects.create_user(
            username='test_user'
        )
        cls.user_not_author_2 = User.objects.create_user(
            username='test_user_2'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
            group=cls.group,
        )
        posts_for_creation = list()
        for i in range(5):
            posts_for_creation.append(
                Post(
                    text='Тестовый пост' + str(i),
                    author=cls.author,
                    group=cls.group,
                )
            )
        Post.objects.bulk_create(posts_for_creation)
        cls.posts = Post.objects.order_by('-pub_date')

    def setUp(self):
        # Создаём неавторизованный клиент
        self.guest_client = Client()
        # Создаём авторизованный клиент 1
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsFollowTest.user_not_author)

    def create_follow_for_tests(self):
        """Создание подписки на автора."""
        Follow.objects.create(
            user=PostsFollowTest.user_not_author,
            author=PostsFollowTest.author
        )

    def test_create_follow(self):
        """Проверка подписки"""
        follow_count = Follow.objects.count()
        response = self.authorized_client.post(
            reverse(
                'posts:profile_follow',
                args=[PostsFollowTest.author]
            ),
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile',
                args=[PostsFollowTest.author]
            )
        )
        self.assertEqual(Follow.objects.count(), follow_count + 1)
        self.assertTrue(
            Follow.objects.filter(
                user=PostsFollowTest.user_not_author,
                author=PostsFollowTest.author
            ).exists()
        )

    def test_unfollow(self):
        """Проверка отписки"""
        self.create_follow_for_tests()
        follow_count = Follow.objects.count()
        response = self.authorized_client.post(
            reverse(
                'posts:profile_unfollow',
                args=[PostsFollowTest.author]
            ),
        )
        self.assertRedirects(
            response, reverse(
                'posts:profile',
                args=[PostsFollowTest.author]
            )
        )
        self.assertEqual(Follow.objects.count(), follow_count - 1)

    def test_show_author_posts_if_user_is_follower(self):
        """Проверка новая запись появляется в ленте тех,
        кто на него подписан."""
        self.create_follow_for_tests()
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertTrue('page_obj' in response.context)
        context = response.context['page_obj'].object_list
        self.assertEqual(list(PostsFollowTest.posts), context)

    def test_not_show_author_posts_if_user_not_follower(self):
        """Проверка новая запись не появляется в ленте тех,
        кто на него не подписан."""
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertTrue('page_obj' in response.context)
        context = response.context['page_obj'].object_list
        self.assertNotEqual(list(PostsFollowTest.posts), context)
