from typing import Any
from django import forms
from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from .models import FromClass, Message, Room, Topic, User
from django.contrib.admin.widgets import FilteredSelectMultiple

class UserCreationForm(UserCreationForm):
    from_class = forms.ModelChoiceField(
        queryset=FromClass.objects.exclude(
            set_class__in=("Administrátori", "Učitelia")),
        widget=forms.Select
    )

    class Meta:
        model = User
        fields = ['name', 'username', 'email',
                  'from_class', 'password1', 'password2']


TOPIC_FIELDS_NAME = ['name']
TOPIC_FIELDS_LABEL = ["Téma"]
topic_label_list = dict(zip(TOPIC_FIELDS_NAME, TOPIC_FIELDS_LABEL))


class TopicForm(ModelForm):
    class Meta:
        model = Topic
        fields = '__all__'
        labels = topic_label_list


MESSAGE_FIELDS_NAME = ['user', 'room', 'body', 'likes', 'parent']
MESSAGE_FIELDS_LABEL = ['Napísal', "Názov diskusie",
                        "Správa", "Palce hore", "Odpovedal na"]
message_label_list = dict(zip(MESSAGE_FIELDS_NAME, MESSAGE_FIELDS_LABEL))


class MessageForm(ModelForm):
    class Meta:
        model = Message
        fields = '__all__'
        labels = message_label_list


ROOM_FIELDS_NAME = ['host', 'topic', 'name',
                    'description', 'participants', 'pinned', 'limited_for']
ROOM_FIELDS_LABEL = ['Autor', "Téma", "Názov",
                     "Popis", "Zúčastnení", 'Pinnuté', 'Ukáže sa pre']
room_label_list = dict(zip(ROOM_FIELDS_NAME, ROOM_FIELDS_LABEL))


class RoomAdminForm(ModelForm):
    class Meta:
        model = Room
        fields = '__all__'
        labels = room_label_list


USER_FIELDS_NAME = ['name', 'email', 'bio',
                    'from_class', 'date_joined', 'last_login']
USER_FIELDS_LABEL = ['Meno', "E-mail", "O mne",
                     "Trieda", 'Pridal sa', 'Naposledy na portáli']
user_label_list = dict(zip(USER_FIELDS_NAME, USER_FIELDS_LABEL))


class UserAdminForm(ModelForm):
    class Meta:
        model = User
        fields = '__all__'
        labels = user_label_list


class ReplyForm(ModelForm):

    class Meta:
        model = Message
        fields = ['body', 'parent']

        labels = {
            'body': (''),
        }

        widgets = {
            'body': forms.TextInput(),
        }


class NewClassForm(ModelForm):

    name = forms.CharField(
        label='Tvoje Meno',
        widget=forms.TextInput(),
        max_length=255,
        required=True
    )
    email = forms.CharField(
        label='Tvoj Email',
        widget=forms.TextInput(),
        max_length=255,
        required=True
    )
    set_class = forms.CharField(
        max_length=30, label='Názov skupiny', required=True, widget=forms.TextInput())
    
    users = forms.ModelMultipleChoiceField(User.objects.values_list("email", flat=True), widget=FilteredSelectMultiple("User", False, attrs={'rows':'2'}))
    
    class Meta:
        model = User
        fields = ['name', 'email']


class RoomForm(ModelForm):
    selection = forms.CheckboxSelectMultiple()

    limit_for = forms.ModelMultipleChoiceField(
        queryset=FromClass.objects.all(),
        widget=selection
    )

    file = forms.FileField(
        allow_empty_file=False,
        required=False,
        widget=forms.FileInput()
    )

    class Meta:
        model = Room
        fields = ['topic', 'name', 'description', 'pinned', 'limit_for']


class UserForm(ModelForm):
    class Meta:
        model = User
        fields = ['avatar', 'name', 'username', 'email', 'bio']


class ChangePasswordForm(UserCreationForm, ModelForm):

    email = None

    def __init__(self, email: bool = False, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if email:
            self.email = forms.EmailField()

    class Meta:
        model = User
        fields = ['email', 'password1', 'password2']


FROMCLASS_FIELDS_NAME = ['set_class']
FROMCLASS_FIELDS_LABEL = ['Trieda']
fromclass_label_list = dict(zip(FROMCLASS_FIELDS_NAME, FROMCLASS_FIELDS_LABEL))


class FromClassAdminForm(ModelForm):
    class Meta:
        model = FromClass
        fields = '__all__'
        labels = fromclass_label_list
