from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
from website.models import Definition


def definition(request):
    query = ' '.join(request.GET['word'].split('%20'))
    object_list = Definition.objects.filter(
        Q(description__icontains=query) | Q(term__name__icontains=query)
    )
    result = []
    for d in object_list:
        result.append(d.description + '%20')
    if not result:
        return HttpResponse('Слово не найдено%20')
    return HttpResponse(result)
