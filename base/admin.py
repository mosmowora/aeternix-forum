from django.contrib import admin

# Register your models here.

from .models import FromClass, Room, Topic, Message, User
from online_users.models import OnlineUserActivity

class UserAdmin(admin.ModelAdmin):
    readonly_fields = ('id', 'last_login', 'date_joined')
    
class ClassAdmin(admin.ModelAdmin):
    actions = None
    ordering = ('set_class',)


admin.site.register(User, UserAdmin)
admin.site.register(Room)
admin.site.register(Topic)
admin.site.register(Message)
admin.site.register(FromClass, ClassAdmin)
