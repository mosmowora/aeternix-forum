from django.urls import path, re_path
from . import views
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path('login/', views.loginPage, name="login"),
    path('logout/', views.logoutUser, name="logout"),
    path('register/', views.registerPage, name="register"),
    re_path(r'^jsi18n/$', JavaScriptCatalog.as_view(), name='jsi18n'),

    path('', views.home, name="home"),
    path('room/<str:pk>/', views.room, name="room"),
    path('profile/<str:pk>/', views.userProfile, name="user-profile"),
    path('change-password/', views.changePassword, name="change-password"),

    path('pinned/<str:pk>/', views.pinRoom, name="pinit"),
    path('create-room/', views.createRoom, name="create-room"),
    path('update-room/<str:pk>/', views.updateRoom, name="update-room"),
    path('delete-room/<str:pk>/', views.deleteRoom, name="delete-room"),
    path('subscribe-room/<str:pk>/', views.subscribeRoom, name="subscribe-room"),

    path('delete-message/<str:pk>/', views.deleteMessage, name="delete-message"),
    path('upvote-message/<str:pk>/', views.upvoteMessage, name="upvote-message"),

    path('update-user/', views.updateUser, name="update-user"),
    path('needs-update/', views.needsUpdate, name="needs-update"),
    path('delete-user/', views.deleteUser, name="delete-user"),

    path('topics/', views.topicsPage, name="topics"),
    path('activity/', views.activityPage, name="activity"),
    
    path('error/', views.fallback, name="fallback"),
    path('new-class/', views.newClass, name="new-class"),
    path('update-groups/', views.updateGroups, name="update-groups"),
    path('update-group/<str:pk>', views.updateGroup, name="update-group"),
    path('delete-group/<str:pk>', views.deleteGroup, name="delete-group"),

    path('update-class/', views.updateUserClass, name="update-class"),
    
    path('email-response/<str:pk>/', views.mailResponse, name="mail-response"),
]
