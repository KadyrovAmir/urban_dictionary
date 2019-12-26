from datetime import datetime
import random
import time
import os.path

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, redirect, get_object_or_404, render_to_response
from django.views.decorators.http import require_POST
from django_registration.forms import User
from django.core.mail import send_mail
from django.views import View
from django.template import RequestContext

from website.enums import STATUSES_FOR_REQUESTS, ACTION_TYPES, USER, DEF, RFP, RUPS, SUP
from urban_dictionary.settings import EMAIL_HOST_USER

try:
    from django.utils import simplejson as json
except ImportError:
    import json

from website.forms import *
from website.models import Definition, CustomUser, Example, UploadData, Rating, RequestForPublication, Favorites, \
    Notification, RequestUpdateStatus, Blocking, Term, STATUSES, ROLE_CHOICES


def main_page(request):
    return render(request, 'website/main_page.html',
                  {'definitions': Definition.get_top_for_week, 'popular_for_week': True})
    # {'definitions': Definition.objects.all})


def custom_handler404(request, exception, template_name="page_not_found.html"):
    response = render_to_response("website/base/page_not_found.html")
    response.status_code = 404
    print(request.user)
    return response


@login_required
@transaction.atomic
def activate_user(request):
    request.user.custom_user.status = STATUSES[0][0]
    request.user.save()
    return redirect('website:update_profile')


def ask_support(request):
    if not request.user.is_anonymous:
        if request.user.custom_user.is_admin():
            if request.method == 'POST':
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
            return render(request, 'website/support_list.html',
                          {'questions': Support.objects.filter(answer__isnull=True).order_by("-date_creation")})
    if request.method == 'POST':
        question = Support(question=request.POST["question"], name=request.POST["name"], email=request.POST["email"],
                           date_creation=datetime.now())
        if not request.user.is_anonymous:
            question.user = request.user.custom_user
        question.save()
        for admin in CustomUser.objects.filter(role=3):
            Notification(date_creation=datetime.now(), user=admin,
                         action_type=ACTION_TYPES[14][0],
                         models_id="%s%s" % (SUP, question.id)).save()
        return render(request, 'website/support_done.html', {'email': question.email})
    return render(request, 'website/support.html', {})


@login_required
def answer_support(request, pk):
    if request.user.custom_user.is_admin():
        question = get_object_or_404(Support, pk=pk)
        if request.method == 'POST':
            question.answer = request.POST['answer']
            question.save()

            BASE = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(BASE, "support_mail.txt"), 'r', encoding="utf-8") as support_mail:
                email_text = support_mail.read() \
                    .replace("question_Q8Vx q]vYfs$*7c,<tyfP|SCdr+wl+m2N{.uY.[a9&mR1zmHL}8[Xz V&36X||0t",
                             question.question) \
                    .replace("answer_q+W{ceC)}*<la~K9C{)>CLfUNY6[?c|u=JVT[)`L8*R|=qw,C?x &A:Bvv^tQD^D", question.answer)
                send_mail('Ответ на вопрос на сайте {}'.format(request.META['HTTP_HOST']),
                          email_text,
                          EMAIL_HOST_USER,
                          [question.email],
                          fail_silently=False)
            if not question.user is None:
                Notification(date_creation=datetime.now(), user=question.user,
                             action_type=ACTION_TYPES[11][0],
                             models_id="%s%s" % (SUP, question.id)).save()
            return redirect('website:support')
        return render(request, 'website/support_answer.html', {
            'question': question
        })
    else:
        redirect('website:main_page')


@login_required
@require_POST
def change_password(request):
    password_form = PasswordChangeForm(user=request.user, data=request.POST)
    if password_form.is_valid():
        password_form.save()
        update_session_auth_hash(request, password_form.user)
        return redirect('website:profile', pk=request.user.id)
    else:
        request.session['change_password_msg'] = password_form.errors
        return redirect('website:update_profile')


@login_required
@transaction.atomic
def update_profile(request):
    password_form = PasswordChangeForm(user=request.user)
    if request.method == 'POST':
        user_form = EditUserForm(request.POST, instance=request.user)
        profile_form = EditProfileForm(request.POST, instance=request.user.custom_user)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            user = profile_form.save(commit=False)
            user.photo = request.FILES.get('photo', user.photo)
            user.save()
            return redirect('website:profile', pk=user.id)
    else:
        user_form = EditUserForm(instance=request.user)
        profile_form = EditProfileForm(instance=request.user.custom_user)
        password_form._errors = request.session.pop('change_password_msg', None)
    return render(request, 'website/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'role': ROLE_CHOICES[request.user.custom_user.role - 1][1]
    })


class UserDetailView(View):

    def get(self, request, pk):
        profile = get_object_or_404(User, pk=pk)
        if profile.custom_user.is_block():
            if request.user.is_anonymous:
                raise Http404()
            if not request.user.custom_user.is_admin():
                raise Http404()
        user_definitions = Definition.objects.filter(author_id__exact=pk)
        user_rating = str(sum(map(lambda x: x.get_likes() - x.get_dislikes(), user_definitions)))
        definition_number = Definition.objects.filter(author_id__exact=pk).count()
        return render(request, 'website/profile.html',
                      {'profile': profile,
                       'role': ROLE_CHOICES[profile.custom_user.role - 1][1],
                       'rating': user_rating,
                       'definition_number': definition_number})


@login_required
def create_definition(request):
    current_user = CustomUser.objects.get(user=request.user)
    if request.method == 'POST':
        term = Term.objects.filter(name=request.POST["name"]).first()
        if term is None:
            term = Term(name=request.POST["name"])
            term.save()
        definition = Definition(term=term, description=request.POST["description"],
                                source=request.POST["source"],
                                author=current_user)
        definition.save()
        if current_user.is_moderator() or current_user.is_admin():
            definition.date = datetime.now()
            definition.save()
        else:
            cur_date = datetime.now()
            rfp = RequestForPublication(definition=definition, date_creation=cur_date)
            rfp.save()
            for admin in CustomUser.objects.filter(role=3):
                Notification(date_creation=cur_date, user=admin, action_type=ACTION_TYPES[12][0],
                             models_id="%s%s %s%s" % (USER, current_user.id, RFP, rfp.id)).save()

        examples = request.POST.getlist("examples")
        primary = int(request.POST.get("primary"))
        for i, ex in enumerate(examples):
            example = Example(example=ex, primary=True if primary == i else False, definition=definition)
            example.save()
        for f, h in zip(request.FILES.getlist("upload_data"), request.POST.getlist("header")):
            link_file = "%s/%s/%s.%s" % (
                definition.author.id, definition.id, int(time.time() * 1000), f.name.split(".")[1])
            fs = FileSystemStorage()
            filename = fs.save(link_file, f)
            u = UploadData(header_for_file=h, definition=definition, image=filename)
            u.save()
        return redirect("website:definition", definition.id)
    return render(request, "website/definition/create_definition.html", {})


@login_required
def edit_definition(request, pk):
    print("!!!")
    definition = Definition.objects.get(id=pk)
    current_user = request.user.custom_user
    if definition.author != current_user:
        raise Http404()
    rfp = RequestForPublication.objects.get(definition=definition)
    if request.method == "POST":

        term = Term.objects.filter(name=request.POST["name"]).first()
        if term is None:
            term = Term(name=request.POST["name"])
            term.save()
        definition.term = term
        definition.description = request.POST["description"]
        definition.source = request.POST["source"]
        definition.date = None
        definition.save()
        if current_user.is_moderator() or current_user.is_admin():
            definition.date = datetime.now()
            definition.save()
        else:
            rfp.date_creation = datetime.now()
            rfp.status = STATUSES_FOR_REQUESTS[0][0]
            rfp.save()

        old_examples = list(definition.examples.all())
        examples = request.POST.getlist("examples")
        primary = int(request.POST.get("primary"))
        for i, ex in enumerate(examples):
            cur_examples = Example.objects.filter(example=ex, definition=definition)
            if len(cur_examples) > 0:
                example = cur_examples[0]
            else:
                example = Example(example=ex, definition=definition)
            if example in old_examples:
                old_examples.remove(example)
            if primary == i:
                example.primary = True
            else:
                example.primary = False
            example.save()

        for ex in old_examples:
            ex.delete()

        print(request.POST)
        for f, h in zip(request.FILES.getlist("upload_data"), request.POST.getlist("header")):
            link_file = "%s/%s/%s.%s" % (
                definition.author.id, definition.id, int(time.time() * 1000), f.name.split(".")[1])
            fs = FileSystemStorage()
            filename = fs.save(link_file, f)
            u = UploadData(header_for_file=h, definition=definition, image=filename)
            u.save()
        return redirect("website:personal_definitions")
    return render(request, "website/definition/edit_definition.html", {"definition": definition, "rfp": rfp})


@login_required
def request_for_definition(request, pk):
    current_user = CustomUser.objects.get(user=request.user)
    rfp = get_object_or_404(RequestForPublication, pk=pk)
    if not current_user.is_admin() or not rfp.is_new():
        raise Http404()
    if request.method == 'POST':
        answer = request.POST["answer"]
        if answer == "approve":
            rfp.status = STATUSES_FOR_REQUESTS[2][0]
            rfp.definition.date = datetime.now()
            rfp.definition.save()
            Notification(date_creation=datetime.now(), user=rfp.definition.author,
                         action_type=ACTION_TYPES[6][0],
                         models_id="%s%s" % (DEF, rfp.definition.id)).save()
        else:
            if answer == "reject":
                rfp.status = STATUSES_FOR_REQUESTS[1][0]
                Notification(date_creation=datetime.now(), user=rfp.definition.author,
                             action_type=ACTION_TYPES[4][0],
                             models_id="%s%s" % (DEF, rfp.definition.id)).save()
            else:
                rfp.status = STATUSES_FOR_REQUESTS[3][0]
                Notification(date_creation=datetime.now(), user=rfp.definition.author,
                             action_type=ACTION_TYPES[5][0],
                             models_id="%s%s" % (DEF, rfp.definition.id)).save()
            rfp.reason = request.POST["reason"]
        rfp.save()
        return redirect('website:requests_pub')

    return render(request, "website/admin/admin_definition_check.html", {"rfp": rfp})


def definition(request, pk):
    try:
        definition = Definition.objects.get(id=pk)
        return render(request, "website/definition/definition.html", {"definition": definition})
    except:
        raise Http404()


def user_definitions(request, pk):
    target_user = get_object_or_404(CustomUser, pk=pk)
    if target_user != request.user.custom_user:
        return render(request, "website/definition/personal_definitions.html",
                      {"definitions": Definition.objects.filter(author__exact=target_user),
                       'target_user': target_user})
    else:
        return redirect('website:personal_definitions')


@login_required
def personal_definitions(request):
    current_user = request.user.custom_user
    return render(request, "website/definition/personal_definitions.html",
                  {"definitions": Definition.objects.filter(author=current_user),
                   'target_user': current_user})


class TermView(View):

    def get(self, request, pk):
        term = Term.objects.get(pk=pk)
        return render(request, 'website/term_page.html',
                      {'term': term})


@require_POST
@login_required
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
            if defin.author.id != user.id:
                Notification(date_creation=datetime.now(), action_type=ACTION_TYPES[1][0], user=defin.author,
                             models_id="%s%s %s%s" % (USER, user.id, DEF, defin.id)).save()
        else:
            # add a new like for a company
            Rating(definition=defin, user=user, estimate=1).save()
            if defin.author.id != user.id:
                Notification(date_creation=datetime.now(), action_type=ACTION_TYPES[1][0], user=defin.author,
                             models_id="%s%s %s%s" % (USER, user.id, DEF, defin.id)).save()

        ctx = {'likes_count': defin.get_likes(), 'dislikes_count': defin.get_dislikes()}
        # use mimetype instead of content_type if django < 5
        return HttpResponse(json.dumps(ctx), content_type='application/json')


@login_required
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
            if defin.author.id != user.id:
                Notification(date_creation=datetime.now(), user=defin.author,
                             models_id="%s%s %s%s" % (USER, user.id, DEF, defin.id)).save()
            Rating(definition=defin, user=user, estimate=0).save()
        else:
            # add a new like for a company
            Rating(definition=defin, user=user, estimate=0).save()
            if defin.author.id != user.id:
                Notification(date_creation=datetime.now(), user=defin.author,
                             models_id="%s%s %s%s" % (USER, user.id, DEF, defin.id)).save()

        ctx = {'dislikes_count': defin.get_dislikes(), 'likes_count': defin.get_likes()}
        # use mimetype instead of content_type if django < 5
        return HttpResponse(json.dumps(ctx), content_type='application/json')


@login_required
def favourite(request):
    if request.method == 'POST':
        user = request.user.custom_user
        definition_id = request.POST.get('def_id', None)
        defin = get_object_or_404(Definition, pk=definition_id)

        if defin.favorites.filter(user=user).exists():
            defin.favorites.get(user=user).delete()
            colour = 'black'
        else:
            Favorites(definition=defin, user=user).save()
            if defin.author.id != user.id:
                Notification(date_creation=datetime.now(), user=defin.author, action_type=ACTION_TYPES[10][0],
                             models_id="%s%s %s%s" % (USER, user.id, DEF, defin.id)).save()
            colour = 'red'

        ctx = {'colour': colour}
        return HttpResponse(json.dumps(ctx), content_type='application/json')


@login_required
def favourites(request):
    favs = Favorites.objects.filter(user=request.user.custom_user)
    result = [fav.definition for fav in favs]
    return render(request, 'website/main_page.html',
                  # {'definitions': Definition.get_top_for_week})
                  {'definitions': result, 'favorites_page': True})


def random_definition(request):
    definitons = [d for d in Definition.objects.all() if d.is_publish()]
    definition = random.choice(definitons)
    return redirect("website:definition", definition.id)


def search(request):
    query = request.GET.get('q')
    object_list = Definition.objects.filter(
        Q(description__icontains=query) | Q(term__name__icontains=query)
    )
    object_list = [d for d in object_list if d.is_publish()]
    if object_list:
        return render(request, 'website/main_page.html',
                      {'definitions': object_list, 'search_page': True})
    else:
        raise Http404()


@login_required
def requests_pub(request):
    user = request.user.custom_user
    if user.is_admin():
        return render(request, 'website/admin/requests_for_publication.html',
                      {'rfps': RequestForPublication.objects.order_by(
                          "-date_creation").filter(status=STATUSES_FOR_REQUESTS[0][0])})
    raise Http404()


@login_required
def notifications(request):
    user = request.user.custom_user
    notifs = user.notifications.all().order_by("-date_creation")
    for n in notifs:
        n.new = False
        n.save()
    return render(request, "website/notifications.html", {"notifications": notifs})


@login_required
def create_request_for_update_status(request):
    user = request.user.custom_user
    rup = RequestUpdateStatus(date_creation=datetime.now(), user=user)
    rup.save()
    for admin in CustomUser.objects.filter(role=3):
        Notification(date_creation=datetime.now(), user=admin, action_type=ACTION_TYPES[13][0],
                     models_id="%s%s" % (RUPS, rup.id)).save()
    return redirect('website:profile', pk=user.id)


@login_required
def update_status(request, pk, answer):
    if request.user.custom_user.is_admin():
        rup = RequestUpdateStatus.objects.get(pk=pk)
        if answer == "accept":
            rup.status = 3
            rup.save()
            user = rup.user
            user.role = 2
            user.save()
        else:
            rup.status = 2
            rup.save()
        Notification(date_creation=datetime.now(), user=rup.user, action_type=ACTION_TYPES[3][0],
                     models_id="%s%s" % (RUPS, rup.id)).save()
        return redirect("website:requests_for_update_status")
    raise Http404()


@login_required
def requests_for_update_status(request):
    if request.user.custom_user.is_admin():
        return render(request, "website/admin/requests_for_update_status.html",
                      {"rups": RequestUpdateStatus.objects.filter(status=1)})
    raise Http404()


@login_required
@transaction.atomic
def block(request, pk):
    if request.user.custom_user.is_admin():
        blocked_user = User.objects.get(pk=pk)
        blocking = Blocking(user=blocked_user.custom_user, reason=request.POST["reason"], date_creation=datetime.now(),
                            expiration_date=request.POST["date"])
        blocking.save()
        blocked_user.is_active = False
        blocked_user.save()
        update_session_auth_hash(request, blocked_user)

        BASE = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(BASE, "block_mail.txt"), 'r', encoding="utf-8") as support_mail:
            email_text = support_mail.read() \
                .replace("user_a93a04d13d4efbf11caf76339de7b435", blocked_user.username) \
                .replace("reason_bfffaf3d25520b20dabb1dd7ab2f615f", blocking.reason) \
                .replace("date_494deb546d18a9e9dd16f28ea9e41bfd", blocking.expiration_date)
            send_mail('Блокировка на платформе {}'.format(request.META['HTTP_HOST']),
                      email_text,
                      EMAIL_HOST_USER,
                      [blocked_user.email],
                      fail_silently=False)

        return redirect('website:profile', pk=blocked_user.id)
    raise Http404()


@login_required
@transaction.atomic
def unblock(request, pk):
    if request.user.custom_user.is_admin():
        unblocked_user = User.objects.get(pk=pk)
        blocking = unblocked_user.custom_user.blocking.all().filter(active=True)[0]
        blocking.active = False
        blocking.save()
        unblocked_user.is_active = True
        unblocked_user.save()

        BASE = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(BASE, "unblock_mail.txt"), 'r', encoding="utf-8") as support_mail:
            email_text = support_mail.read() \
                .replace("user_a93a04d13d4efbf11caf76339de7b435", unblocked_user.username)
            send_mail('Разблокировка на платформе {}'.format(request.META['HTTP_HOST']),
                      email_text,
                      EMAIL_HOST_USER,
                      [unblocked_user.email],
                      fail_silently=False)

        return redirect('website:profile', pk=unblocked_user.id)
    raise Http404()


@login_required
def drop_file(request):
    print("check")
    file = UploadData.objects.get(pk=request.POST.get('file_id', None))
    if file.definition.author == request.user.custom_user:
        file.delete()
        return HttpResponse(json.dumps({}), content_type='application/json')
    raise Http404()
