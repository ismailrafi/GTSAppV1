from django.urls import path
from . import views

urlpatterns = [
    # Survey records
    path('survey/', views.survey_list, name='survey-list'),
    path('survey/<int:pk>/', views.survey_detail, name='survey-detail'),
    path('survey/sync/', views.sync_surveys, name='survey-sync'),

    # GEE analysis endpoints
    path('gee/indices/', views.gee_indices, name='gee-indices'),
    path('gee/unsupervised/', views.gee_unsupervised, name='gee-unsupervised'),
    path('gee/supervised/', views.gee_supervised, name='gee-supervised'),
]
