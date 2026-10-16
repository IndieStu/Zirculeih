from django.conf import settings


def environment(request):
    return {"review_instance": settings.REVIEW_MODE, "review_build": settings.REVIEW_BUILD}
