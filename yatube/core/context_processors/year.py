from django.utils import timezone


def year(request):
    current_datetime = timezone.now()
    return {
        'year': current_datetime.year,
    }
