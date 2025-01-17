from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render
from django.urls import reverse

from bookmarks import queries
from bookmarks.models import Bookmark, BookmarkForm, BookmarkFilters, build_tag_string
from bookmarks.services.bookmarks import create_bookmark, update_bookmark, archive_bookmark, archive_bookmarks, \
    unarchive_bookmark, unarchive_bookmarks, delete_bookmarks, tag_bookmarks, untag_bookmarks
from bookmarks.utils import get_safe_return_url
from bookmarks.views.partials import contexts

_default_page_size = 30


@login_required
def index(request):
    bookmark_list = contexts.ActiveBookmarkListContext(request)
    tag_cloud = contexts.ActiveTagCloudContext(request)
    return render(request, 'bookmarks/index.html', {
        'bookmark_list': bookmark_list,
        'tag_cloud': tag_cloud,
    })


@login_required
def archived(request):
    bookmark_list = contexts.ArchivedBookmarkListContext(request)
    tag_cloud = contexts.ArchivedTagCloudContext(request)
    return render(request, 'bookmarks/archive.html', {
        'bookmark_list': bookmark_list,
        'tag_cloud': tag_cloud,
    })


def shared(request):
    filters = BookmarkFilters(request)
    bookmark_list = contexts.SharedBookmarkListContext(request)
    tag_cloud = contexts.SharedTagCloudContext(request)
    public_only = not request.user.is_authenticated
    users = queries.query_shared_bookmark_users(request.user_profile, filters.query, public_only)
    return render(request, 'bookmarks/shared.html', {
        'bookmark_list': bookmark_list,
        'tag_cloud': tag_cloud,
        'users': users
    })


def convert_tag_string(tag_string: str):
    # Tag strings coming from inputs are space-separated, however services.bookmarks functions expect comma-separated
    # strings
    return tag_string.replace(' ', ',')


@login_required
def new(request):
    initial_url = request.GET.get('url')
    initial_title = request.GET.get('title')
    initial_description = request.GET.get('description')
    initial_auto_close = 'auto_close' in request.GET

    if request.method == 'POST':
        form = BookmarkForm(request.POST)
        auto_close = form.data['auto_close']
        if form.is_valid():
            current_user = request.user
            tag_string = convert_tag_string(form.data['tag_string'])
            create_bookmark(form.save(commit=False), tag_string, current_user)
            if auto_close:
                return HttpResponseRedirect(reverse('bookmarks:close'))
            else:
                return HttpResponseRedirect(reverse('bookmarks:index'))
    else:
        form = BookmarkForm()
        if initial_url:
            form.initial['url'] = initial_url
        if initial_title:
            form.initial['title'] = initial_title
        if initial_description:
            form.initial['description'] = initial_description
        if initial_auto_close:
            form.initial['auto_close'] = 'true'

    context = {
        'form': form,
        'auto_close': initial_auto_close,
        'return_url': reverse('bookmarks:index')
    }

    return render(request, 'bookmarks/new.html', context)


@login_required
def edit(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404('Bookmark does not exist')
    return_url = get_safe_return_url(request.GET.get('return_url'), reverse('bookmarks:index'))

    if request.method == 'POST':
        form = BookmarkForm(request.POST, instance=bookmark)
        if form.is_valid():
            tag_string = convert_tag_string(form.data['tag_string'])
            update_bookmark(form.save(commit=False), tag_string, request.user)
            return HttpResponseRedirect(return_url)
    else:
        form = BookmarkForm(instance=bookmark)

    form.initial['tag_string'] = build_tag_string(bookmark.tag_names, ' ')

    context = {
        'form': form,
        'bookmark_id': bookmark_id,
        'return_url': return_url
    }

    return render(request, 'bookmarks/edit.html', context)


def remove(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404('Bookmark does not exist')

    bookmark.delete()


def archive(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404('Bookmark does not exist')

    archive_bookmark(bookmark)


def unarchive(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404('Bookmark does not exist')

    unarchive_bookmark(bookmark)


def mark_as_read(request, bookmark_id: int):
    try:
        bookmark = Bookmark.objects.get(pk=bookmark_id, owner=request.user)
    except Bookmark.DoesNotExist:
        raise Http404('Bookmark does not exist')

    bookmark.unread = False
    bookmark.save()


@login_required
def action(request):
    # Determine action
    if 'archive' in request.POST:
        archive(request, request.POST['archive'])
    if 'unarchive' in request.POST:
        unarchive(request, request.POST['unarchive'])
    if 'remove' in request.POST:
        remove(request, request.POST['remove'])
    if 'mark_as_read' in request.POST:
        mark_as_read(request, request.POST['mark_as_read'])
    if 'bulk_archive' in request.POST:
        bookmark_ids = request.POST.getlist('bookmark_id')
        archive_bookmarks(bookmark_ids, request.user)
    if 'bulk_unarchive' in request.POST:
        bookmark_ids = request.POST.getlist('bookmark_id')
        unarchive_bookmarks(bookmark_ids, request.user)
    if 'bulk_delete' in request.POST:
        bookmark_ids = request.POST.getlist('bookmark_id')
        delete_bookmarks(bookmark_ids, request.user)
    if 'bulk_tag' in request.POST:
        bookmark_ids = request.POST.getlist('bookmark_id')
        tag_string = convert_tag_string(request.POST['bulk_tag_string'])
        tag_bookmarks(bookmark_ids, tag_string, request.user)
    if 'bulk_untag' in request.POST:
        bookmark_ids = request.POST.getlist('bookmark_id')
        tag_string = convert_tag_string(request.POST['bulk_tag_string'])
        untag_bookmarks(bookmark_ids, tag_string, request.user)

    return_url = get_safe_return_url(request.GET.get('return_url'), reverse('bookmarks:index'))
    return HttpResponseRedirect(return_url)


@login_required
def close(request):
    return render(request, 'bookmarks/close.html')
