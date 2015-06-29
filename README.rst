learn_drf_nested_resources
==========================

Introduction
------------

This project was created to provide a complete example that illustrates how to implement nested resources on a `Django REST framework <http://www.django-rest-framework.org/>`_ API using `drf-nested-routers <https://github.com/alanjds/drf-nested-routers>`_. In order to make the project as real as possible, the authentication is handled using `Django OAuth Toolkit <https://github.com/evonove/django-oauth-toolkit>`_.

The application
---------------

The application exposes an API to manage blogposts and comments. No provision has been made to display either blogposts nor comments. The model is quite simple as well

::

    class UUIDIdMixin(models.Model):
        class Meta:
            abstract = True

        id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)


    class AuthorMixin(models.Model):
        class Meta:
            abstract = True

        author = models.ForeignKey(
            settings.AUTH_USER_MODEL, editable=False, verbose_name=_('author'),
            related_name='%(app_label)s_%(class)s_author'
        )


    class Blogpost(UUIDIdMixin, TimeStampedModel, TitleSlugDescriptionModel, AuthorMixin):
        content = models.TextField(_('content'), blank=True, null=True)
        allow_comments = models.BooleanField(_('allow comments'), default=True)


    class Comment(UUIDIdMixin, TimeStampedModel, AuthorMixin):
        blogpost = models.ForeignKey(
            Blogpost, editable=False, verbose_name=_('blogpost'), related_name='comments'
        )
        content = models.TextField(_('content'), max_length=255, blank=False, null=False)

I made use of `django-extension <https://github.com/django-extensions/django-extensions>`_'s TimeStampedModel and TitleSlugDescriptionModel to provide the basic features of the model and only added a few things here and there to make it interesting.

The API
-------

The API is where things get interesting. The access to the blogposts is exposed through a DRF ``ModelViewSet``, which provides the usual actions:

    * **list:** ``GET /api/blogposts/`` List all blogposts.
    * **create:** ``POST /api/blogposts/`` Create a new blogpost.
    * **retrieve:** ``GET /api/blogposts/(?P<pk>[^/.]+)/`` Show the details of a specific blogpost.
    * **update:** ``PUT /api/blogposts/(?P<pk>[^/.]+)/`` Update all fields of a specific blogpost.
    * **partial** update: ``PATCH /api/blogposts/(?P<pk>[^/.]+)/`` Update a field of a specific blogpost.
    * **destroy:** ``DELETE /api/blogposts/(?P<pk>[^/.]+)/`` Delete a specific blogpost.

The whole point of the project is to show you how to implement nested resources, so comments are exposed under blogposts:

    * **list:** ``GET /api/blogposts/(?P<pk>[^/.]+)/comments`` List all the comments on a specific blogpost.
    * **create:** ``POST /api/blogposts/(?P<pk>[^/.]+)/comments`` Create a new comment on a specific blogpost.

The rest of the comment actions are exposed through a top-level ``/comments`` endpoint. The reason for this is that I (and others believe) that resources should be accessible through a single URI.

    * **list:** ``GET /api/comments/`` List all blogposts.
    * **retrieve:** ``GET /api/comments/(?P<pk>[^/.]+)/`` Show the details of a specific comment.
    * **update:** ``PUT /api/comments/(?P<pk>[^/.]+)/`` Update all fields of a specific comment.
    * **partial** update: ``PATCH /api/comments/(?P<pk>[^/.]+)/`` Update a field of a specific comment.
    * **destroy:** ``DELETE /api/comments/(?P<pk>[^/.]+)/`` Delete a specific comment.

This also has the advantage of being quite easy to implement, as it leverages DRF's auto-magic functionality. Everything is handled by three simple viewsets:

::

    class BlogpostViewSet(ModelViewSet):
        serializer_class = BlogpostSerializer
        queryset = Blogpost.objects.all()
        permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

        def perform_create(self, serializer):
            serializer.save(author=self.request.user)


    class CommentViewSet(
        RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, ListModelMixin, GenericViewSet
    ):
        queryset = Comment.objects.all()
        serializer_class = CommentSerializer
        permission_classes = (IsAuthenticatedOrReadOnly, CommentDeleteOrUpdatePermission)


    class NestedCommentViewSet(CreateModelMixin, ListModelMixin, GenericViewSet):
        queryset = Comment.objects.all()
        serializer_class = CommentSerializer
        permission_classes = (IsAuthenticatedOrReadOnly,)

        def create(self, request, *args, blogpost_pk=None, **kwargs):
            # Check if the referenced blogpost exists
            blogpost = get_object_or_404(Blogpost.objects.filter(pk=blogpost_pk))

            # Check if comments are allowed
            if not blogpost.allow_comments:
                raise PermissionDenied

            # Proceed as usual

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            serializer.save(
                author=self.request.user,
                blogpost=blogpost
            )

            headers = self.get_success_headers(serializer.data)

            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        def list(self, request, *args, blogpost_pk=None, **kwargs):
            # Check if the referenced blogpost exists
            blogpost = get_object_or_404(Blogpost.objects.filter(pk=blogpost_pk))

            queryset = self.filter_queryset(
                self.get_queryset().filter(blogpost=blogpost)
            )

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)

            return Response(serializer.data)

The URLs are then wired using a couple of routers:

::

    router = DefaultRouter()
    router.register(r'users', UserViewSet)
    router.register(r'blogposts', BlogpostViewSet)
    router.register(r'comments', CommentViewSet)

    blogposts_router = NestedSimpleRouter(router, r'blogposts', lookup='blogpost')
    blogposts_router.register(r'comments', NestedCommentViewSet)

    urlpatterns = [
        url(r'^admin/', include(admin.site.urls)),
        url(r'^api/', include(router.urls)),
        url(r'^api/', include(blogposts_router.urls)),
        url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    ]

Authentication
--------------

I used OAuth2 for authentication and authorization, and created an application to allow access to the API. The application was defined as "Public" with grant type "Resource owner password-base", so all we need to do to access the API is request an access token:

::

    $ curl --header "Content-Type: application/x-www-form-urlencoded" --data "username=admin&password=admin&grant_type=password&client_id=g9lMt5ySrJw8P5TQSIidykuhkG6SCKxLpvsAg2zZ" --request POST http://localhost:8000/o/token/
    {"scope": "read write", "expires_in": 36000, "token_type": "Bearer", "access_token": "nJckFj8TEg8aL9Cw5VYh0bCtQOScjr", "refresh_token": "vhbNBb4SPeL6Sgh6fJEg7TuFWqYonK"}

Afterwards we can use the given access token in the Authorization header of subsequent requests:

::

    $ curl --header "Authentication: Bearer nJckFj8TEg8aL9Cw5VYh0bCtQOScjr" --header "Accept: application/json; indent=4"  --request GET http://localhost:8000/api/blogposts/
    [
        {
            "url": "http://localhost:8000/api/blogposts/41baef11-34a3-4a56-ab2d-5f404e5135c5/",
            "title": "Blogpost title",
            "slug": "blogpost-title",
            "description": "Blogpost description (changed)",
            "content": "Blogpost content",
            "allow_comments": true,
            "author": "http://localhost:8000/api/users/1/",
            "created": "2015-06-27T23:09:42.785075Z",
            "modified": "2015-06-29T01:25:28.922868Z"
        },
        {
            "url": "http://localhost:8000/api/blogposts/82676f21-75ba-4710-a0d6-6c0b80b2d080/",
            "title": "Another blogpost",
            "slug": "another-blogpost",
            "description": "Another blogpost description",
            "content": "Another blogpost content",
            "allow_comments": false,
            "author": "http://localhost:8000/api/users/1/",
            "created": "2015-06-29T01:17:46.052855Z",
            "modified": "2015-06-29T01:27:59.722019Z"
        }
    ]

Feedback
--------

As usual, I welcome comments, suggestions and pull requests.