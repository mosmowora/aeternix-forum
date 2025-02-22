from datetime import timedelta
import datetime
from django.core.files import File
import threading
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.db.models.query import QuerySet
from django.contrib.auth import authenticate, login, logout
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.urls import reverse
from .models import (
    EmailPasswordVerification, FromClass, Room, Topic, Message, User
)
from .forms import (
    ChangePasswordForm, NewClassForm,
    ReplyForm, RoomForm, UpdateClassForm, UserCreationForm, UserForm
)
from online_users.models import OnlineUserActivity
# Create your views here.

ENCRYPTION_MAGIC = 12
ALL_CLASSES = FromClass.objects.filter(custom=False)


class EmailThread(threading.Thread):

    def __init__(self, subject: str, html_content: str, recipients: tuple[str]):
        self.subject = subject
        self.recipients = recipients
        self.html_content = html_content
        threading.Thread.__init__(self)

    def run(self):
        msg = EmailMultiAlternatives(
            self.subject, self.html_content, "tomas.nosal04@gmail.com", self.recipients)
        msg.attach_alternative(self.html_content, "text/html")
        msg.send(fail_silently=False)


def loginPage(request: HttpRequest):
    """
    Login page form
    """
    page = 'login'
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        email = request.POST.get('email').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(email=email)
        except Exception:
            messages.error(request, 'Užívateľ neexistuje')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Zlý email alebo heslo')

    return render(request, 'base/login_register.html', {'page': page})


def logoutUser(request):
    logout(request)
    return redirect('home')


def registerPage(request: HttpRequest):
    """
    Register page form
    """
    form = UserCreationForm()

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        is_email_valid = form['email'].data.endswith("@spse-po.sk")
        if not is_email_valid:
            messages.error(
                request, "Zadaná emailová adresa nepatrí do školskej domény")
            return render(request, 'base/login_register.html', {'form': form})

        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.replace(" ", "_").lower()
            user.save()
            user.from_class.add(form.cleaned_data['from_class'])
            login(request, user)
            return redirect('home')
        else:
            errors = [error.errors for error in form if len(error.errors) > 0]
            messages.error(request, *errors)

    return render(request, 'base/login_register.html', {'form': form})


def home(request: HttpRequest):
    """
    Home page
    """
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    request.session.set_expiry(timedelta(hours=6))
    request.session.clear_expired()
    user = AnonymousUser()
    rooms = None
    next_class = None
    topics = Topic.objects.all()
    room_messages = Message.objects.all()

    if not isinstance(request.user, AnonymousUser):
        user = User.objects.get(pk=request.user.id)
        if request.user.is_staff:
            rooms = Room.objects.filter(
                (Q(topic__name__iexact=q) if q != '' else Q(topic__name__icontains=q)) |
                (Q(name__icontains=q))
            ).distinct()
        else:
            rooms = Room.objects.filter(
                (Q(topic__name__iexact=q) if q != '' else Q(topic__name__icontains=q)) |
                (Q(name__icontains=q))
            ).filter(
                Q(limited_for__in=request.user.from_class.all()) |
                Q(host=request.user) |
                Q(public=True)
            ).distinct()

            room_messages = sorted(room_messages.filter(
                Q(room__limited_for__in=request.user.from_class.all())
            ), key=lambda x: x.created, reverse=True)

        try:
            next_class = FromClass.objects.get(pk=user.from_class.filter(
                Q(set_class__in=ALL_CLASSES)).first().pk + 6)
        except (FromClass.DoesNotExist, AttributeError):
            next_class = None

    else:
        rooms = Room.objects.filter(public=True)
        for message in room_messages:
            if not message.room.public:
                message.user.username = '????'
                message.body = '????'
                message.room.name = 'neznáme'

    activities = OnlineUserActivity.get_user_activities(
        time_delta=timedelta(seconds=30))

    active_users = User.objects.filter(
        id__in=map(lambda u: u.user_id, activities)
    )
    room_count = rooms.count()

    context = {'rooms': rooms, 'topics': tuple(filter(lambda x: x.room_set.all().count() != 0, topics)), 'show_topics': tuple(filter(lambda y: y.room_set.all().count() != 0, sorted(topics, key=lambda x: x.room_set.all().count(), reverse=True)))[:3],
               'room_count': room_count, 'room_messages': room_messages[:3], 'active_users': active_users, 'next_class': next_class}

    if not user.is_anonymous and (9 >= datetime.date.today().month >= 7) and not user.updated_profile and not user.is_staff:
        context['needs_update'] = True
        for user in User.objects.filter(is_staff=False):
            user.updated_profile = False
            user.save()

    return render(request, 'base/home.html', context)


@login_required(login_url='login', redirect_field_name=None)
def updateGroups(request: HttpRequest):
    return render(
        request,
        "base/update-groups.html",
        {
            'user_groups': request.user.registered_groups.all()
        }
    )


@login_required(login_url='login', redirect_field_name=None)
def updateUserClass(request: HttpRequest):
    form = UpdateClassForm(request.POST)
    user = request.user
    new_class = None
    if request.method == 'POST':
        user = User.objects.get(pk=request.user.pk)
        try:
            new_class = FromClass.objects.get(
                pk=int(request.POST.get('set_class')))
        except TypeError:
            new_class = None

        if new_class not in user.from_class.all():
            old_class = user.from_class.filter(custom=False).first()
            user.from_class.add(new_class)
            user.from_class.set(user.from_class.exclude(pk=old_class.pk))
            return redirect('needs-update')
        else:
            messages.error(request, "Už patríš do tejto skupiny")

    return render(request, 'base/update-class.html', {'form': form, 'from_class': user.from_class.first().set_class, 'user_rooms': user.room_set.all(), 'done_class': True})


@login_required(login_url='login', redirect_field_name=None)
def newClass(request: HttpRequest):
    """
    Form for creating a new class or group
    """
    try:
        user = User.objects.get(id=request.user.id)
        form = NewClassForm(instance=user)
        form.fields['users'].queryset = User.objects.values_list(
            "email", flat=True).filter(~Q(email__exact=request.user.email))

    except Exception:
        user = None
        form = NewClassForm()

    if user and user.registered_groups.count() + 1 > 5:
        messages.info(
            request, "Dosiahol si maximálny počet vytvorených skupín")
        return redirect('home')

    back_button = request.META.get("HTTP_REFERER").split(
        "/") if request.META.get("HTTP_REFERER") is not None else 'new-class'

    if request.method == 'POST' and user.registered_groups.count() + 1 <= 5:
        clazz = request.POST.get("set_class")
        picked_users = User.objects.filter(
            email__in=request.POST.getlist("users"))
        if clazz not in FromClass.objects.values_list("set_class", flat=True):
            clazz = FromClass.objects.create(set_class=clazz, custom=True)
            user.registered_groups.add(clazz)
            user.save()
            for user in picked_users:
                if clazz not in user.from_class.all():
                    user.from_class.add(clazz)
                    print(f"Added {clazz} to user: {user}")
            request.user.from_class.add(clazz)

            messages.success(request, "Úspešne vytvorená skupina")
            return redirect("home")
        else:
            messages.error(request, "Táto skupina už existuje!")

    return render(request, 'base/new_class_entry.html', {'form': form, "back": "register" in back_button, 'classes': tuple(FromClass.objects.all())})


@login_required(login_url='login', redirect_field_name=None)
def updateGroup(request: HttpRequest, pk):
    """
    Form for updating an existing group
    """
    user = request.user
    group = FromClass.objects.get(pk=pk)
    users_in_group = User.objects.filter(
        from_class=group).values_list("email", flat=True)
    form = NewClassForm(instance=user,
                        initial={
                            'set_class': group.set_class,
                            'users': [usr for usr in users_in_group]
                        },
                        )
    print(f"{form['users'].initial=}")
    back_button = request.META.get("HTTP_REFERER").split(
        "/") if request.META.get("HTTP_REFERER") is not None else 'new-class'

    if request.method == 'POST':
        picked_users = tuple(map(lambda x: User.objects.get(
            email=x), request.POST.getlist("users")))
        clazz = FromClass.objects.get(pk=pk)
        clazz.set_class = request.POST.get("set_class")
        clazz.custom = True
        clazz.save()

        old_users = User.objects.filter(from_class=clazz)
        # Add new users
        for user_in_class in picked_users:
            if clazz not in user_in_class.from_class.all():
                user_in_class.from_class.add(clazz)
                print(f"Added {clazz} to user_in_class: {user_in_class}")

        # Delete old users
        # print(tuple(filter(lambda u: u not in picked_users, old_users)))
        for old_user in tuple(filter(lambda u: u not in picked_users, old_users)):
            old_user.from_class.set(old_user.from_class.exclude(id=clazz.id))

        if clazz not in request.user.from_class.all():
            print("Added author of the group")
            request.user.from_class.add(clazz)

        messages.success(request, "Úspešne aktualizovaná skupina")
        return redirect("user-profile", pk=request.user.pk)
    return render(request, "base/new_class_entry.html", {'form': form, "back": "register" in back_button})


@login_required(login_url='login', redirect_field_name=None)
def deleteGroup(request: HttpRequest, pk):
    if request.method == "POST":
        for user in User.objects.all():
            if user.from_class.contains(FromClass.objects.get(pk=pk)):
                user.from_class.set(user.from_class.exclude(pk=pk))
                user.save()

        return redirect('home')

    return render(request, "base/delete.html", {'group': FromClass.objects.get(pk=pk)})


@login_required(login_url='login', redirect_field_name=None)
def pinRoom(request: HttpRequest, pk):
    """
    Logic for pinning or unpinning a room
    """

    pinned_room: Room = Room.objects.get(id=pk)
    pinned_room.pinned = not pinned_room.pinned
    pinned_room.save()
    return HttpResponseRedirect(reverse('home'))


@login_required(login_url='login', redirect_field_name=None)
def subscribeRoom(request: HttpRequest, pk):
    room = Room.objects.get(id=pk)
    user = User.objects.get(id=request.user.id)
    if user in room.subscribing.all():
        room.subscribing.remove(user)
    else:
        room.subscribing.add(user)

    return redirect('room', pk=room.id)


# @login_required(login_url='login', redirect_field_name=None)
def room(request: HttpRequest, pk):
    """
    Page for showing everything about the room, handling room messages, message upvotes, participants, etc.
    """
    try:
        room = Room.objects.get(id=pk)
        room_messages: QuerySet[Message] = room.message_set.all()
        room_messages = sorted(
            room_messages, key=lambda mess: mess.likes.count(), reverse=True)

        participants = room.participants.all()

        upvoted_messages: dict[Message, bool] = {}

        back: str = request.META.get('HTTP_REFERER')
        back = any(x in ('room', 'error', 'delete-message', 'upvote-message', 'update-room')
                   for x in back.split("/")) if back is not None else None

        for message in room_messages:
            upvoted = False
            if message.likes.filter(id=request.user.id).exists():
                upvoted = True

            upvoted_messages[message] = upvoted

        active_users = User.objects.filter(
            id__in=list(map(lambda u: u.user_id, OnlineUserActivity.get_user_activities(
                time_delta=timedelta(seconds=30))))
        )
        context = {'room': room, 'room_messages': room_messages, 'amount_of_messages': len(room_messages),
                   'participants': participants, 'upvoted_messages': upvoted_messages, 'active_users': active_users, 'back': back, 'is_anonymous': request.user.id is None}

        if room.file and room.file.name.split(".")[-1] in ('docx', 'pdf', 'xls', 'xlsx', 'ppt', 'pptx', 'potm'):
            context['file_type'] = "file"
        elif room.file and room.file.name.split(".")[-1] in ('xbm', 'tif', 'jfif', 'ico', 'gif', 'svg', 'jpg', 'jpeg', 'png', 'webp', 'bmp', 'pjp', 'apng', 'pjpeg', 'avif'):
            context['file_type'] = "image"

        if request.method == 'POST':
            content = request.POST.get('body')
            parent = None
            reply_form = ReplyForm(data=request.POST)

            if reply_form.is_valid():
                content = reply_form.cleaned_data['body']
                try:
                    parent = reply_form.cleaned_data['parent']
                except Exception:
                    parent = None

            if content == '':
                return redirect('room', pk=room.id)

            try:
                parent = Message.objects.get(id=reply_form['parent'].value())
            except Exception as e:
                parent = None

            try:
                message = Message(
                    user=request.user,
                    room=room,
                    body=content,
                    parent=parent
                )
            except Exception as e:
                print(e)
                messages.error(request, "Problém s pripojením")
                EmailThread("SPŠE Forum server error",
                                f"Error nastal pri meneni hesla uzivatela {request.user.name}\nError type: {e.args}", ("tomas.nosal04@gmail.com",)).start()
                return redirect('room', pk=room.id)

            if request.user not in room.participants.all():
                room.participants.add(request.user)

            htmly = get_template('base/email_template.html')
            EmailThread("SPŠE Forum nová správa", htmly.render(
                {'student': request.user, 'body': content, 'room': room}), tuple(
                map(lambda user: user.email, room.subscribing.all()))).start()
            message.save()
            return redirect('room', pk=room.id)
    except Exception as e:
        print(e)
        EmailThread("SPŠE Forum server error",
                                f"Error nastal pri meneni hesla uzivatela {request.user.name}\nError type: {e.args}", ("tomas.nosal04@gmail.com",)).start()
        return fallback(request, "Nemožno zobraziť túto diskusiu.")

    return render(request, 'base/room.html', context)


def upvoteMessage(request: HttpRequest, pk):
    """
    Logic for upvoting or downvoting a message
    """
    message = Message.objects.get(id=request.POST.get('message_id'))

    if message.likes.filter(id=request.user.id).exists():
        message.likes.remove(request.user)
    else:
        message.likes.add(request.user)

    message.save()
    return HttpResponseRedirect(reverse('room', args=[message.room_id]))


def userProfile(request: HttpRequest, pk):
    """
    User's profile page
    """
    user = None
    try:
        user = User.objects.get(id=pk)
        rooms = user.room_set.all()
        room_messages = user.message_set.all()
        active_users = User.objects.filter(
            id__in=list(map(lambda u: u.user_id, OnlineUserActivity.get_user_activities(
                time_delta=timedelta(seconds=30))))
        )
        topics = Topic.objects.all()
        topics = tuple(filter(lambda y: y.room_set.all().count() != 0, sorted(
            topics, key=lambda x: x.room_set.all().count(), reverse=True)))
        context = {
            'user': user, 'rooms': rooms, 'from_class': user.from_class.all()[0],
            'room_messages': room_messages, 'topics': topics,
            'show_topics': sorted(topics[:4], key=lambda x: x.room_set.all().count(), reverse=True), 'active_users': active_users
        }
        return render(request, 'base/profile.html', context)
    except Exception as e:
        print(e)
        if user is None:
            return fallback(request, message="Nenašiel som užívateľa")
        else:
            # This shouldn't happen
            return fallback(request, message="Tu nemáš čo hľadať")


def mailResponse(request: HttpRequest, pk):
    """
    E-mail confirmation handler\n
    get's the user based on his id and after decrypting the password from the url sets his new password.\n
    Handles password confirmation token expiry. Token expires after 1H.

    Params
    -----

    pk `str` - user's id\n
    password `str` - encrypted password taken from the url for decryption
    """

    user = User.objects.get(id=pk)
    pass_verification = EmailPasswordVerification.objects.get(
        user__id=user.id)
    password = "".join(
        map(lambda s: chr(ord(s) + ENCRYPTION_MAGIC), pass_verification.password))
    expires = pass_verification.token_created + datetime.timedelta(hours=2)

    expires = expires.replace(tzinfo=datetime.datetime.now(
        datetime.timezone.utc).astimezone().tzinfo)
    now = datetime.datetime.now(tz=datetime.datetime.now(
        datetime.timezone.utc).astimezone().tzinfo)

    # Debugging purposes
    print(f"{expires=}")
    print(f"{now=}")

    if now > expires:
        return fallback(request, message="Token pre zmenu hesla vypršal.")

    user.set_password(password)
    user.save()
    login(request, user)
    messages.success(request, 'Úspešne zmenené heslo')
    return redirect('home')


def changePassword(request: HttpRequest):
    """
    If the user wants to change his password, handle it with this logic
    """
    user = None
    form = None
    try:
        user = User.objects.get(id=request.user.id)
        form = ChangePasswordForm(instance=user)
    except Exception:
        user = AnonymousUser()
        form = ChangePasswordForm(email=True)

    if request.method == 'POST':
        if request.POST.get('password1') == request.POST.get('password2'):
            if isinstance(user, AnonymousUser):
                try:
                    student = User.objects.get(email=request.POST.get("email"))
                except Exception:
                    messages.error(request, "Užívateľ neexistuje")
                    return redirect('change-password')
                # password = f'http://localhost:8000/email-response/{student.pk}/{quote(quote(encrypt(request.POST.get("password1")), encoding="utf-8"), safe=":/")}'
                password = f'http://forum.spse-po.sk/email-response/{student.pk}/'
                htmly = get_template('base/email_template.html')
                try:
                    EmailThread("SPŠE Forum zabudnuté heslo",
                                htmly.render(
                                    {'student': student, 'password': password}), (request.POST.get("email"),)).start()
                except Exception as e:
                    EmailThread("SPŠE Forum server error",
                                f"Error nastal pri meneni hesla uzivatela {request.user.name}\nError type: {e.args}", ("tomas.nosal04@gmail.com",)).start()
                    messages.error(request, "Nastala chyba pri poslaní emailu")

                messages.info(request, "Bol ti zaslaný potvrdzovací email")
                print("Bol ti zaslaný potvrdzovací email")
                try:
                    got_user = EmailPasswordVerification.objects.get(
                        user=student)  # This is neccessary !!!
                    got_user.token_created = datetime.datetime.now() + datetime.timedelta(hours=1)
                    got_user.password = "".join(
                        map(lambda s: chr(ord(s) - ENCRYPTION_MAGIC), request.POST.get("password1")))
                    got_user.save()
                except Exception:
                    EmailPasswordVerification.objects.create(
                        user=student,
                        token_created=datetime.datetime.now() + datetime.timedelta(hours=1),
                        password="".join(
                            map(lambda s: chr(ord(s) - ENCRYPTION_MAGIC), request.POST.get("password1")))
                    )
                return redirect('home')

            else:
                if user.check_password(request.POST.get('password1')):
                    messages.error(
                        request, "Nemôžeš mať rovnaké heslo ako predtým")

                else:
                    user.set_password(request.POST.get('password1'))
                    user.save()
                    login(request, user)
                    messages.success(request, 'Úspešne si si zmenil heslo')
                    return redirect('user-profile', pk=user.id)
        else:
            messages.error(request, "Heslá nie sú rovnaké")

    return render(request, 'base/change_password.html', {'form': form})


def fallback(request: HttpRequest, message: str = None):
    """
    Error handler site (404 page)

    Params:
    ------
    message - `str`: optional message to display on the 404 page
    """
    return render(request, 'base/error-site.html', {'message': message})


@login_required(login_url='login', redirect_field_name=None)
def createRoom(request: HttpRequest):
    """
    Site for room creation, basically the form backend
    """
    try:
        if request.user.room_set.all().count() >= 10:
            messages.info(
                request, 'Dosiahol si maximálny počet vytvorených diskusií')
            return redirect('home')

        form = RoomForm()
        form.fields['limit_for'].queryset = FromClass.objects.exclude(
            ~Q(id__in=request.user.from_class.all()) & Q(custom=True))
        topics = Topic.objects.all()
        context = {'form': form, 'topics': topics}

        if request.method == 'POST':
            if request.FILES.get('file') and request.FILES.get('file').name.split(".")[-1] not in ('docx', 'pdf', 'xls', 'xlsx', 'ppt', 'pptx', 'potm', 'xbm', 'tif', 'jfif', 'ico', 'gif', 'svg', 'jpg', 'jpeg', 'png', 'webp', 'bmp', 'pjp', 'apng', 'pjpeg', 'avif'):
                messages.error(request, "Nepodporovaný typ súboru")
                return redirect('create-room')

            form = RoomForm(request.POST or None, request.FILES or None)
            topic_name = request.POST.get('topic')
            topic, _ = Topic.objects.get_or_create(name=topic_name)
            class_list = request.POST.getlist("limit_for")
            if request.META.get("HTTP_REFERER") is not None:
                context['back'] = any(
                    x == 'create-room' for x in request.META['HTTP_REFERER'].split("/"))

            room = Room(
                host=request.user,
                topic=topic,
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                pinned=True if request.POST.get('pinned') and request.POST.get(
                    'pinned') == "on" else False,
                public=True if request.POST.get('public') == "on" else False,
                file=request.FILES.get('file')
            )
            selected_classes = set(int(x) for x in class_list)
            if len(selected_classes) == 0 and not room.public:
                context['message'] = 'Musíš zaškrtnúť pre koho sa ukáže'
                return redirect('update-room', pk=room.pk)

            room.save()
            room.limited_for.set(selected_classes)
            return redirect('home')
    except Exception as e:
        if e[1] == "Data too long for column 'file' at row 1":
            messages.info(request, "Názov súboru je pridlhý")
            return redirect('create-room')
        print(e)
        return fallback(request, "Niečo sa stalo pri vytváraní diskusie.")

    return render(request, 'base/room_form.html', context)


@login_required(login_url='login', redirect_field_name=None)
def updateRoom(request: HttpRequest, pk):
    """
    Site for room updates, basically the form backend
    """
    try:
        room = Room.objects.get(id=pk)
        form = RoomForm(instance=room)
        topics = Topic.objects.all()
        
        form['limit_for'].initial = room.limited_for.get_queryset()
        context = {'form': form, 'topics': topics, 'room': room}

        if request.user != room.host and not request.user.is_staff:
            return fallback(request)

        if request.method == 'POST':
            if request.META.get("HTTP_REFERER") is not None:
                context['back'] = any(
                    x == 'update-room' for x in request.META['HTTP_REFERER'].split("/"))
                if not request.user.is_anonymous and (9 >= datetime.date.today().month >= 7) and not request.user.updated_profile:
                    context['needs_update_back'] = True

            if request.FILES.get('file') and request.FILES.get('file').name.split(".")[-1] not in ('docx', 'pdf', 'xls', 'xlsx', 'ppt', 'pptx', 'potm', 'xbm', 'tif', 'jfif', 'ico', 'gif', 'svg', 'jpg', 'jpeg', 'png', 'webp', 'bmp', 'pjp', 'apng', 'pjpeg', 'avif'):
                messages.error(request, "Nepodporovaný typ súboru")
                return redirect('update-room', pk=room.pk)
            
            class_list = request.POST.getlist("limit_for")
            topic_name = request.POST.get('topic')
            topic, _ = Topic.objects.get_or_create(name=topic_name)
            room.name = request.POST.get('name')
            room.topic = topic
            room.description = request.POST.get('description')
            room.pinned = True if request.POST.get(
                'pinned') and request.POST.get('pinned') == "on" else False
            room.public = True if request.POST.get('public') == "on" else False
            # If there is new file -> change it, otherwise ignore setting new one
            if request.FILES.get('file'):
                room.file = request.FILES.get('file')
            room.limited_for.set(FromClass.objects.all())
            selected_classes = set(int(x) for x in class_list)

            form = RoomForm(request.POST, request.FILES, instance=room)
            if len(selected_classes) == 0 and not room.public:
                context['message'] = 'Musíš zaškrtnúť pre koho sa ukáže'
                return redirect('update-room', pk=room.pk)
            
            if form.is_valid():
                room = form.save()
                
            elif form.errors:
                lst = form.errors.as_data()
                EmailThread("SPŠE Forum server error",
                    f"Error nastal pri meneni udajov diskusie {room.name}\nError type: {lst}", ("tomas.nosal04@gmail.com",)).start()
                print(lst)
                return redirect('update-room', pk=room.pk)

            if context.get('needs_update_back') is not None:
                return redirect('needs-update')
            return redirect('room', pk=room.pk)

    except Exception as e:
        EmailThread("SPŠE Forum server error",
                    f"Error nastal pri meneni udajov diskusie {room.name}\nError type: {e.args}", ("tomas.nosal04@gmail.com",)).start()
        print(
            f"Error nastal pri meneni udajov diskusie {room.name}\nError type: {e.args}")
        return fallback(request, "Nebolo možné zmeniť údaje diskusie")

    return render(request, 'base/room_form.html', context)


@login_required(login_url='login', redirect_field_name=None)
def deleteRoom(request: HttpRequest, pk):
    """
    Site for room deletion
    """
    room = Room.objects.get(id=pk)
    context = {'obj': room, 'back': any(
        x == 'delete-room' for x in request.META['HTTP_REFERER'].split("/"))}
    if request.user != room.host and not request.user.is_staff:
        return fallback(request)

    if request.method == 'POST':
        if not request.user.is_anonymous and (9 >= datetime.date.today().month >= 7) and not request.user.updated_profile:
            context['needs_update_back'] = True
        room.delete()
        if context.get("needs_update_back") is not None:
            return redirect('needs-update')
        return redirect('home')
    return render(request, 'base/delete.html', context)


@login_required(login_url='login')
def deleteMessage(request, pk):
    """
    Site for room's message deletion
    """
    message = None
    try:
        message = Message.objects.get(id=pk)
    except Exception:
        messages.error(request, 'Správa neexistuje')
        return redirect('home')

    if request.user != message.user:
        return fallback(request, "Takto odstránenie správy nefunguje.")

    if request.method == 'POST':
        message.delete()
        # redirect user back to the room
        return redirect('room', pk=message.room.id)

    return render(request, 'base/delete.html', {'obj': message})


@login_required(login_url='login', redirect_field_name=None)
def needsUpdate(request: HttpRequest):
    user = request.user

    if request.method == "POST":
        user.updated_profile = True
        user.save()
        return redirect('home')

    return render(request, "base/needs_update.html", {'from_class': user.from_class.first().set_class, 'user_rooms': user.room_set.all()})


@login_required(login_url='login', redirect_field_name=None)
def updateUser(request: HttpRequest):
    """
    Site for updating the user's info
    """
    user = request.user
    form = UserForm(instance=user)

    try:
        if request.method == 'POST':
            form = UserForm(request.POST, request.FILES, instance=user)
            if form.is_valid():
                form.save()
                return redirect('user-profile', pk=user.id)
            elif form.errors:
                lst = tuple(*form.errors.as_data().values())
                for error in lst:
                    if "100 characters" in error.messages[0]:
                        messages.error(
                            request, "Uisti sa, že názov súboru má najviac 100 znakov")
                        continue
                    elif error.code == 'invalid_image':
                        messages.error(
                            request, "Uisti sa, že súbor je obrázok")
                        continue

                    messages.error(request, *error)

    except Exception as e:
        EmailThread("SPŠE Forum server error",
                    f"Error nastal pri meneni udajov uzivatela {request.user.name}\nError type: {e.args}", ("tomas.nosal04@gmail.com",)).start()
        return fallback(request, "Niečo neočakávané sa stalo.")

    return render(request, 'base/update-user.html', {'form': form})


@login_required(login_url='login', redirect_field_name=None)
def deleteUser(request: HttpRequest):
    """
    Site for deleting everything about the user
    """
    try:
        if request.method == 'POST':
            posted_messages = Message.objects.filter(
                user__email__exact=request.user.email)
            posted_messages.delete()
            rooms = list(filter(lambda r: request.user in r.all(), [
                r.participants for r in Room.objects.all()]))
            subscribed_to = list(filter(lambda r: request.user in r.all(), [
                r.subscribing for r in Room.objects.all()
            ]))
            for participants in rooms:
                participants.get(email__exact=request.user.email).delete()

            for subscriber in subscribed_to:
                if subscriber.filter(email__exact=request.user.email).exists():
                    subscriber.get(email__exact=request.user.email).delete()

            hosted_rooms = Room.objects.filter(
                host__name__exact=request.user.name)
            hosted_rooms.delete()
            if request.user.id is not None:
                User.objects.get(pk=request.user.pk).delete()
            messages.success(request, "Odstránil si si účet")
            return redirect('home')
    except Exception as e:
        EmailThread("SPŠE Forum server error",
                    f"Error nastal pri zmazani uzivatela {request.user.name}\nError type: {e.args}", ("tomas.nosal04@gmail.com",)).start()
        return fallback(request, "Niečo sa stalo pri odstraňovaní tvojho účtu.")

    return render(request, 'base/delete-user.html')


def topicsPage(request: HttpRequest):
    """
    Site for showing topics and students/teachers
    """
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    render_value = ""
    type_of = "topic"

    try:
        if request.method == "GET":
            if request.GET.get("search_for_students") is None:
                render_value = request.GET.get("search_for_topics")
                type_of = 'topic'
            else:
                render_value = request.GET.get("search_for_students")
                type_of = 'user'

        alphabet = {c: i for i, c in enumerate(
            'AÁÄBCČDĎDZDŽEÉFGHCHIÍJKLĹĽMNŇOÓÔPQRŔSŠTŤUÚVWXYÝZŽ')}
        # Topics
        topics = sorted(Topic.objects.filter(
            Q(name__icontains=q)), key=lambda x: x.room_set.all().count(), reverse=True) \
            if type_of == "topic" \
            \
            else sorted(User.objects.filter(Q(name__icontains=q) | Q(from_class__set_class__icontains=q)),  # Students
                        key=lambda user: [alphabet.get(c, ord(c)) for c in user.name.split()[0]])
    except Exception as e:
        EmailThread("SPŠE Forum server error",
                    f"Error nastal pri ukazani tem/studentov {request.user.name}\nError type: {e.args}", ("tomas.nosal04@gmail.com",)).start()
        return fallback(request)

    return render(request, 'base/topics.html', {'topics': tuple(filter(lambda x: x.room_set.all().count() != 0, topics)) if type_of != 'user' else set(topics), 'render_value': render_value, "type_of": type_of})


def activityPage(request):
    """
    Activity page with room messages
    """
    room_messages = Message.objects.all()[:3]
    return render(request, 'base/activity.html', {'room_messages': room_messages})
