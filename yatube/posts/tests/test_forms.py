import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm, CommentForm
from ..models import Group, Post, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_author')
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
        cls.form = PostForm()
        cls.comment_form = CommentForm()

        cls.comment = Comment.objects.create(
            text='Тестовый комментарий',
            post=cls.post,
            author=cls.user,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = PostsFormTest.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в БД."""
        uploaded = SimpleUploadedFile(
            name='small_2.gif',
            content=PostsFormTest.small_gif,
            content_type='image/gif'
        )
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый пост 2',
            'group': PostsFormTest.group.pk,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:profile',
                kwargs={'username': PostsFormTest.user.username}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                author=PostsFormTest.user,
                text='Тестовый пост 2',
                group=PostsFormTest.group,
                image='posts/small_2.gif'
            ).exists()
        )

    def test_edit_post(self):
        """Проверка формы редактирования поста."""
        form_data = {
            'text': PostsFormTest.post.text,
            'group': PostsFormTest.group.pk,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostsFormTest.post.pk}),
            data=form_data,
            follow=True,
        )
        self.assertTrue(
            Post.objects.filter(
                author=PostsFormTest.user,
                text=PostsFormTest.post.text,
                group=PostsFormTest.group,
                image='posts/small.gif',
            ).exists()
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostsFormTest.post.pk}
            )
        )

    def test_add_comment(self):
        """Проверка формы создания комментария."""
        form_data = {
            'text': 'Тестовый комментарий',
        }

        comment_count = PostsFormTest.post.comments.count()
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostsFormTest.post.pk}
            ),
            data=form_data,
            follow=True
        )

        comment_count_add = self.post.comments.count()

        self.assertEqual(comment_count_add, comment_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                post=PostsFormTest.post,
                text='Тестовый комментарий',
                author=PostsFormTest.user,
            ).exists()
        )
        self.assertEqual(
            len(response.context['comments']),
            comment_count_add
        )
        self.assertEqual(
            response.context['comments'][comment_count_add - 1].text,
            'Тестовый комментарий'
        )
