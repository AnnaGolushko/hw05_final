from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='StasBasov')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_group',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user
        )

    def test_models_have_correct_object_names(self):
        """Проверка, что в поле __str__ объектов моделей приложения posts
        записано корректное значение."""
        post = PostModelTest.post
        group = PostModelTest.group
        test_models_names = {
            post.text[:15]: post,
            group.title: group,
        }
        for expected_object_name, model in test_models_names.items():
            with self.subTest(field=expected_object_name):
                self.assertEqual(str(model), expected_object_name)
