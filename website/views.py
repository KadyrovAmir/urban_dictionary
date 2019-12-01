import time

from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
try:
    from django.utils import simplejson as json
except ImportError:
    import json

from website.forms import EditUserForm, EditProfileForm
from website.models import Definition, Term, CustomUser, Example, UploadData, Rating

# Create your views here.
from django.views import View
from django.views.generic import ListView, DetailView

from website.models import Term, STATUSES


def main_page(request):
    return render(request, 'website/main_page.html',
                  {'definitions': Definition.get_top_for_week})


@login_required
@transaction.atomic
def activate_user(request):
    request.user.custom_user.status = STATUSES[0][0]
    request.user.save()
    return redirect('website:update_profile')


@login_required
@transaction.atomic
def update_profile(request):
    if request.method == 'POST':
        user_form = EditUserForm(request.POST, instance=request.user)
        profile_form = EditProfileForm(request.POST, instance=request.user.custom_user)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return redirect('website:main_page')
    else:
        user_form = EditUserForm(instance=request.user)
        profile_form = EditProfileForm(instance=request.user.custom_user)
    return render(request, 'edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


@login_required
def page_create_definition(request):
    if request.method == 'POST':
        # TODO проверка на уникальность
        term = Term(name=request.POST["name"])
        term.save()
        definition = Definition(term=term, description=request.POST["description"],
                                source=request.POST["source"],
                                author=CustomUser.objects.get(user=request.user))
        definition.save()
        examples = request.POST.getlist("examples")
        primary = int(request.POST.get("primary"))
        print(primary)
        for i, ex in enumerate(examples):
            example = Example(example=ex, primary=True if primary == i else False, definition=definition)
            example.save()
        for f, h in zip(request.FILES.getlist("upload_data"), request.POST.getlist("header")):
            print(f)
            link_file = "%s/%s/%s.%s" % (
            definition.author.id, definition.id, int(time.time() * 1000), f.name.split(".")[1])
            print(link_file)
            fs = FileSystemStorage()
            filename = fs.save(link_file, f)
            u = UploadData(header_for_file=h, definition=definition, image=filename)
            u.save()
        return redirect("website:definition", definition.id)
    return render(request, "website/definition/create_definition.html", {})


def definition(request, id):
    return render(request, "website/definition/definition.html", {"def": Definition.objects.get(id=id)})


class TermView(View):

    def get(self, request, pk):
        term = Term.objects.get(pk=pk)
        return render(request, 'website/term_page.html',
                      {'term': term,})


@require_POST
def like(request):
    if request.method == 'POST':
        user = request.user.custom_user
        definition_id = request.POST.get('def_id', None)
        defin = get_object_or_404(Definition, pk=definition_id)

        if defin.estimates.filter(user=user, estimate=1).exists():
            # user has already liked this definition
            # remove like/user
            defin.estimates.get(user=user).delete()
        elif defin.estimates.filter(user=user, estimate=0).exists():
            defin.estimates.get(user=user).delete()
            Rating(definition=defin, user=user, estimate=1).save()
        else:
            # add a new like for a company
            Rating(definition=defin, user=user, estimate=1).save()

        ctx = {'likes_count': defin.get_likes(), 'dislikes_count': defin.get_dislikes()}
        # use mimetype instead of content_type if django < 5
        return HttpResponse(json.dumps(ctx), content_type='application/json')


def dislike(request):
    if request.method == 'POST':
        user = request.user.custom_user
        definition_id = request.POST.get('def_id', None)
        defin = get_object_or_404(Definition, pk=definition_id)

        if defin.estimates.filter(user=user, estimate=0).exists():
            # user has already liked this definition
            # remove like/user
            defin.estimates.get(user=user).delete()
        elif defin.estimates.filter(user=user, estimate=1).exists():
            defin.estimates.get(user=user).delete()
            Rating(definition=defin, user=user, estimate=0).save()
        else:
            # add a new like for a company
            Rating(definition=defin, user=user, estimate=0).save()

        ctx = {'dislikes_count': defin.get_dislikes(), 'likes_count': defin.get_likes()}
        # use mimetype instead of content_type if django < 5
        return HttpResponse(json.dumps(ctx), content_type='application/json')